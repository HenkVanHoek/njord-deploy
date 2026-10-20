# tests/managers/test_gatekeeper_manager.py
"""Unit tests for Gatekeeper Staging Manager (De Proeftuin - Modus A)."""

from unittest.mock import MagicMock, patch

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

    # Admin must be alerted of quarantine
    mock_notifier.escalate_p1_admin.assert_called_once()
    args, kwargs = mock_notifier.escalate_p1_admin.call_args
    assert "FUMS GATEKEEPER QUARANTAINE" in kwargs["error_reason"]


def test_gatekeeper_no_pve_client_and_exceptions():
    """Test runs without Proxmox client, unexpected exceptions, and cleanup failures."""
    mock_notifier = MagicMock()
    mock_diagnoser = MagicMock()

    # 1. No proxmox client (mock mode on localhost)
    mgr_no_pve = GatekeeperManager(
        proxmox_client=None,
        notifier=mock_notifier,
        ai_diagnoser=mock_diagnoser,
    )
    res_no_pve = mgr_no_pve.run_gatekeeper_verification(
        component_id="caddy", old_version="1.0", new_version="1.1"
    )
    assert res_no_pve["certified"] is True
    assert mgr_no_pve._wait_for_container_ip(123) == "127.0.0.1"

    # 2. Synthetic migration without target IP
    assert (
        mgr_no_pve._execute_synthetic_migration(None, "caddy", "1.1")["success"]
        is False
    )

    # 3. PVE client throws unhandled exception during clone/start
    mock_pve = MagicMock()
    mock_pve.clone_lxc.side_effect = RuntimeError("Proxmox cluster offline")
    mgr_err = GatekeeperManager(
        proxmox_client=mock_pve,
        notifier=mock_notifier,
        ai_diagnoser=mock_diagnoser,
    )
    res_err = mgr_err.run_gatekeeper_verification(
        component_id="caddy", old_version="1.0", new_version="1.1"
    )
    assert res_err["quarantined"] is True
    assert "Proxmox cluster offline" in res_err["error"]

    # 4. Cleanup exception
    mock_pve_clean = MagicMock()
    mock_pve_clean.get.return_value = {
        "data": [{"name": "eth0", "inet": "192.168.1.188/24"}]
    }
    mock_pve_clean.destroy_lxc.side_effect = Exception("Storage lock")
    mgr_clean = GatekeeperManager(
        proxmox_client=mock_pve_clean,
        notifier=mock_notifier,
        ai_diagnoser=mock_diagnoser,
    )
    res_clean = mgr_clean.run_gatekeeper_verification(
        component_id="caddy", old_version="1.0", new_version="1.1"
    )
    assert res_clean["certified"] is True

    # 5. AI diagnoser exception
    mock_diagnoser.diagnose_single_failure.side_effect = Exception("AI crash")
    assert mgr_clean._diagnose_gatekeeper_failure("caddy", "err", "logs") is None

    # 6. _wait_for_container_ip timeout and exception handling (lines 191-194)
    mock_pve_timeout = MagicMock()
    mock_pve_timeout.get.side_effect = RuntimeError("Interface read timeout")
    mgr_timeout = GatekeeperManager(
        proxmox_client=mock_pve_timeout,
        notifier=mock_notifier,
        ai_diagnoser=mock_diagnoser,
    )
    with patch("time.sleep", return_value=None):
        assert mgr_timeout._wait_for_container_ip(123, timeout_seconds=0.01) is None
