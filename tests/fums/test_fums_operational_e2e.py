# tests/fums/test_fums_operational_e2e.py
"""FUMS Operational End-to-End Orchestration Test Suite.

Simulates and verifies complete operational lifecycles:
1. Routine patch: Detection -> Green -> Proposal -> Prod Deployment.
2. Major Release: Detection -> Red -> Gatekeeper Certification -> Release offer.
3. Upstream Failure: Major update -> Quarantine -> AI Diagnosis -> Admin Alert.
4. Interactive Sandbox & UAT: Request Mode B -> Quota -> Nightly Sleep -> Sign-off.
5. Production Failure: Container health failure -> Atomic Rollback -> P1 Escalation.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from managers.customer_sandbox_manager import CustomerSandboxManager
from managers.fleet_update_manager import FleetUpdateManager
from managers.gatekeeper_manager import GatekeeperManager


@pytest.fixture
def operational_env():
    """Provides isolated managers and mock infrastructure for end-to-end testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "fums_e2e.db"
        mock_pve = MagicMock()
        mock_pve.get.return_value = {
            "data": [{"name": "eth0", "inet": "192.168.1.199/24"}]
        }
        mock_notifier = MagicMock()
        mock_notifier.send_signal.return_value = True
        mock_notifier.format_client_proposal.return_value = "Mock Proposal"

        mock_diagnoser = MagicMock()
        mock_diagnoser.diagnose_single_failure.return_value = {
            "recommended_action": "Fix PostgreSQL foreign key constraints",
            "failure_category": "DATABASE_MIGRATION",
        }

        gk_mgr = GatekeeperManager(
            proxmox_client=mock_pve,
            notifier=mock_notifier,
            ai_diagnoser=mock_diagnoser,
        )

        sb_mgr = CustomerSandboxManager(
            proxmox_client=mock_pve,
            notifier=mock_notifier,
            db_path=db_path,
            max_sandboxes=3,
        )

        fums_mgr = FleetUpdateManager(
            notifier=mock_notifier,
            gatekeeper_manager=gk_mgr,
            sandbox_manager=sb_mgr,
            db_path=db_path,
        )

        yield {
            "fums": fums_mgr,
            "gatekeeper": gk_mgr,
            "sandbox": sb_mgr,
            "notifier": mock_notifier,
            "diagnoser": mock_diagnoser,
            "pve": mock_pve,
        }


def test_e2e_routine_patch_workflow(operational_env):
    """Keten 1: Routine patch zonder breaking changes (Green risk)."""
    fums = operational_env["fums"]
    notifier = operational_env["notifier"]

    changelog = "Fix minor CSS alignment and typography"
    analysis = fums.analyze_release(
        component_id="vaultwarden",
        old_version="1.31.0",
        new_version="1.31.1",
        raw_changelog=changelog,
    )

    assert analysis["risk_evaluation"]["risk_level"] == "GREEN"
    assert analysis["risk_evaluation"]["requires_gatekeeper"] is False

    # Propose update to client via Signal
    sent = fums.notify_client_proposal(analysis, "+31612345678", channel="signal")
    assert sent is True
    notifier.send_signal.assert_called_once()

    # Customer responds with immediate rollout (Choice 1)
    response_action = fums.handle_client_response(
        analysis=analysis,
        client_response_text="UPDATE 1",
        client_id="ClientAlpha",
    )
    assert response_action["action"] == "production_update_immediate"
    assert response_action["safety_level"] == "high_safety"

    # Execution parameters built
    args = fums.build_ansible_update_args(
        component_id="vaultwarden",
        target_host="192.168.1.50",
        new_tag="1.31.1",
    )
    assert args["extravars"]["component_id"] == "vaultwarden"

    # Simulation of successful deployment
    res = fums.handle_execution_result("vaultwarden", "192.168.1.50", success=True)
    assert res["status"] == "success"
    notifier.escalate_p1_admin.assert_not_called()


def test_e2e_major_release_gatekeeper_certified(operational_env):
    """Keten 2: Major update trigger Gatekeeper Modus A -> Certificering -> Klant."""
    fums = operational_env["fums"]
    pve = operational_env["pve"]

    changelog = "BREAKING CHANGE: Complete API rewrite and schema updates"
    analysis = fums.analyze_release(
        component_id="nextcloud",
        old_version="29.0.5",
        new_version="30.0.0",
        raw_changelog=changelog,
        has_db_migration=True,
    )

    assert analysis["risk_evaluation"]["risk_level"] == "RED"
    assert analysis["risk_evaluation"]["requires_gatekeeper"] is True

    # Run Gatekeeper Modus A
    verified_analysis = fums.verify_gatekeeper(analysis)
    assert verified_analysis["status"] == "gatekeeper_certified"
    assert verified_analysis["risk_evaluation"]["gatekeeper_certified"] is True

    # Ephemeral container was spun up and destroyed
    pve.clone_lxc.assert_called_once()
    pve.destroy_lxc.assert_called_once()


def test_e2e_major_release_quarantine_flow(operational_env):
    """Keten 3: Major update faalt in Gatekeeper -> Quarantaine + AI Analyse + Alarm."""
    fums = operational_env["fums"]
    notifier = operational_env["notifier"]
    diagnoser = operational_env["diagnoser"]

    analysis = fums.analyze_release(
        component_id="immich",
        old_version="1.110.0",
        new_version="2.0.0",
        has_db_migration=True,
    )

    # Simulator of failing database migration
    def broken_migration(ip, vmid):
        return {
            "success": False,
            "error": "Prisma migration fatal error: column 'ownerId' missing",
            "logs": "Postgres error code 42703",
        }

    verified_analysis = fums.verify_gatekeeper(
        analysis,
        executor_func=broken_migration,
    )
    assert verified_analysis["status"] == "quarantined"
    assert verified_analysis["risk_evaluation"]["gatekeeper_certified"] is False

    # AI diagnosis triggered
    diagnoser.diagnose_single_failure.assert_called_once()

    # Admin was alerted of quarantine
    notifier.escalate_p1_admin.assert_called_once()
    _, kwargs = notifier.escalate_p1_admin.call_args
    assert "FUMS GATEKEEPER QUARANTAINE" in kwargs["error_reason"]


def test_e2e_customer_training_and_uat_lifecycle(operational_env):
    """Keten 4: Klant vraagt Modus B aan -> Testing -> Sign-off -> Auto-afbraak."""
    fums = operational_env["fums"]
    sandbox = operational_env["sandbox"]

    analysis = {"component_id": "nextcloud", "new_version": "30.0.0"}

    # Customer sends "UPDATE 4"
    resp = fums.handle_client_response(
        analysis=analysis,
        client_response_text="UPDATE 4",
        client_id="GemeenteAlmere",
    )
    assert resp["action"] == "training_sandbox_requested"
    sb_data = resp["sandbox"]
    assert sb_data["success"] is True
    sandbox_id = sb_data["sandbox_id"]
    assert "gemeentealmere" in sb_data["access_url"]

    # Key-user inspects dummy seed data, conducts training, and gives UAT Sign-off
    signoff = sandbox.sign_off_uat(
        sandbox_id=sandbox_id,
        key_user_notes="All 15 staff members trained. Approved for go-live.",
    )
    assert signoff["success"] is True
    assert signoff["uat_signed_off"] is True
    assert signoff["status"] == "ready_for_production_schedule"


def test_e2e_production_failure_triggers_atomic_rollback(operational_env):
    """Keten 5: Falende update in productie triggert atomaire rollback + P1 alarm."""
    fums = operational_env["fums"]
    notifier = operational_env["notifier"]

    fail_output = (
        "TASK [Verify Container Health Check Status] ... fatal\n"
        "FUMS_ROLLBACK_EXECUTED: Health check failed on nextcloud. "
        "Successfully rolled back state."
    )

    res = fums.handle_execution_result(
        component_id="nextcloud",
        target_host="192.168.1.100",
        success=False,
        error_output=fail_output,
    )

    assert res["status"] == "failed"
    assert res["rollback_executed"] is True

    notifier.escalate_p1_admin.assert_called_once_with(
        component_name="nextcloud",
        target_host="192.168.1.100",
        error_reason=fail_output,
        rollback_performed=True,
    )
