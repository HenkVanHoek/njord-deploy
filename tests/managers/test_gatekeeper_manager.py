# tests/managers/test_gatekeeper_manager.py
"""Unit tests for Gatekeeper Staging Manager (De Proeftuin - Modus A)."""

from unittest.mock import MagicMock

from managers.gatekeeper_manager import GatekeeperManager


def test_gatekeeper_success_lifecycle():
    mock_pve = MagicMock()
    mock_notifier = MagicMock()
    mock_diagnoser = MagicMock()

    # Mock IP resolution
    mock_pve.get.return_value = {"data": [{"name": "eth0", "inet": "192.168.1.188/24"}]}

    mgr = GatekeeperManager(
        proxmox_client=mock_pve,
        notifier=mock_notifier,
        ai_diagnoser=mock_diagnoser,
        node="pve",
        template_vmid=9000,
        staging_vmid_start=850,
    )

    result = mgr.run_gatekeeper_verification(
        component_id="nextcloud",
        old_version="29.0.5",
        new_version="30.0.0",
        service_port=8080,
    )

    assert result["certified"] is True
    assert result["quarantined"] is False
    assert result["component_id"] == "nextcloud"

    # Verify Proxmox lifecycle: clone -> start -> stop -> destroy
    mock_pve.clone_lxc.assert_called_once()
    mock_pve.start_lxc.assert_called_once()
    mock_pve.stop_lxc.assert_called_once()
    mock_pve.destroy_lxc.assert_called_once()
    mock_notifier.escalate_p1_admin.assert_not_called()


def test_gatekeeper_failure_triggers_quarantine_and_ai_diagnosis():
    mock_pve = MagicMock()
    mock_notifier = MagicMock()
    mock_diagnoser = MagicMock()

    mock_pve.get.return_value = {"data": [{"name": "eth0", "inet": "192.168.1.188/24"}]}
    mock_diagnoser.diagnose_single_failure.return_value = {
        "recommended_action": "Check PostgreSQL 16 migration scripts.",
        "failure_category": "DATABASE_MIGRATION",
    }

    mgr = GatekeeperManager(
        proxmox_client=mock_pve,
        notifier=mock_notifier,
        ai_diagnoser=mock_diagnoser,
    )

    # Custom executor simulating a failed database migration
    def failing_executor(ip: str, vmid: int):
        return {
            "success": False,
            "error": "PostgreSQL schema upgrade error: table columns mismatch",
            "logs": "Traceback: column 'status' not found in table 'users'",
        }

    result = mgr.run_gatekeeper_verification(
        component_id="nextcloud",
        old_version="29.0.5",
        new_version="30.0.0",
        executor_func=failing_executor,
    )

    assert result["certified"] is False
    assert result["quarantined"] is True
    assert "PostgreSQL schema upgrade error" in result["error"]
    assert result["ai_diagnosis"] is not None

    # Ephemeral container must still be destroyed!
    mock_pve.destroy_lxc.assert_called_once()

    # Admin must be alerted of quarantine
    mock_notifier.escalate_p1_admin.assert_called_once()
    args, kwargs = mock_notifier.escalate_p1_admin.call_args
    assert "FUMS GATEKEEPER QUARANTAINE" in kwargs["error_reason"]
