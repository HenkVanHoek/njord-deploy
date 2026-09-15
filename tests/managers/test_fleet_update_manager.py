# tests/managers/test_fleet_update_manager.py
"""Unit tests for FleetUpdateManager."""

from unittest.mock import MagicMock

from managers.fleet_update_manager import FleetUpdateManager


def test_analyze_release_major():
    mgr = FleetUpdateManager()
    changelog = (
        "# Release 30.0.0\n"
        "BREAKING CHANGE: Deprecated PHP 8.1 support\n"
        "DATABASE: Automatic migration executed on first start\n"
    )
    res = mgr.analyze_release(
        component_id="nextcloud",
        old_version="29.0.5",
        new_version="30.0.0",
        raw_changelog=changelog,
    )
    assert res["component_id"] == "nextcloud"
    assert res["risk_evaluation"]["risk_level"] == "RED"
    assert res["risk_evaluation"]["is_major"] is True
    assert "approval_token" in res
    assert "BREAKING CHANGE" in res["filtered_changelog"]


def test_notify_client_proposal():
    mock_notifier = MagicMock()
    mock_notifier.format_client_proposal.return_value = "Proposal Text"
    mock_notifier.send_signal.return_value = True

    mgr = FleetUpdateManager(notifier=mock_notifier)
    analysis = {
        "component_id": "nextcloud",
        "old_version": "29.0.5",
        "new_version": "30.0.0",
        "risk_evaluation": {"risk_level": "RED"},
        "approval_token": "tok123",
    }
    ok = mgr.notify_client_proposal(analysis, "+31612345678", channel="signal")
    assert ok is True
    mock_notifier.send_signal.assert_called_once_with("Proposal Text", "+31612345678")


def test_build_ansible_update_args():
    mgr = FleetUpdateManager()
    args = mgr.build_ansible_update_args(
        component_id="nextcloud",
        target_host="192.168.1.100",
        new_tag="30.0.0",
        old_tag="29.0.5",
        service_port=8080,
    )
    assert "update_playbook.yml" in args["playbook"]
    assert args["inventory"] == "192.168.1.100,"
    assert args["extravars"]["component_id"] == "nextcloud"
    assert args["extravars"]["new_tag"] == "30.0.0"
    assert args["extravars"]["service_port"] == "8080"


def test_handle_execution_result_failure_triggers_p1():
    mock_notifier = MagicMock()
    mgr = FleetUpdateManager(notifier=mock_notifier)

    err = "Task failed: FUMS_ROLLBACK_EXECUTED: Health check failed on nextcloud."
    res = mgr.handle_execution_result(
        component_id="nextcloud",
        target_host="192.168.1.100",
        success=False,
        error_output=err,
    )
    assert res["status"] == "failed"
    assert res["rollback_executed"] is True
    mock_notifier.escalate_p1_admin.assert_called_once_with(
        component_name="nextcloud",
        target_host="192.168.1.100",
        error_reason=err,
        rollback_performed=True,
    )


def test_verify_gatekeeper_certified():
    mock_gk = MagicMock()
    mock_gk.run_gatekeeper_verification.return_value = {
        "certified": True,
        "quarantined": False,
    }
    mgr = FleetUpdateManager(gatekeeper_manager=mock_gk)

    analysis = {
        "component_id": "nextcloud",
        "old_version": "29.0.5",
        "new_version": "30.0.0",
        "risk_evaluation": {
            "risk_level": "RED",
            "requires_gatekeeper": True,
        },
    }

    res = mgr.verify_gatekeeper(analysis)
    assert res["status"] == "gatekeeper_certified"
    assert res["risk_evaluation"]["gatekeeper_certified"] is True
    mock_gk.run_gatekeeper_verification.assert_called_once()


def test_verify_gatekeeper_quarantined():
    mock_gk = MagicMock()
    mock_gk.run_gatekeeper_verification.return_value = {
        "certified": False,
        "quarantined": True,
        "error": "DB Schema mismatch",
    }
    mgr = FleetUpdateManager(gatekeeper_manager=mock_gk)

    analysis = {
        "component_id": "nextcloud",
        "old_version": "29.0.5",
        "new_version": "30.0.0",
        "risk_evaluation": {
            "risk_level": "RED",
            "requires_gatekeeper": True,
        },
    }

    res = mgr.verify_gatekeeper(analysis)
    assert res["status"] == "quarantined"
    assert res["risk_evaluation"]["gatekeeper_certified"] is False
    assert res["quarantine_error"] == "DB Schema mismatch"


def test_handle_client_response_training_sandbox():
    mock_sandbox = MagicMock()
    mock_sandbox.request_sandbox.return_value = {
        "success": True,
        "access_url": "https://clientx.training.njorddeploy.com",
    }
    mgr = FleetUpdateManager(sandbox_manager=mock_sandbox)
    analysis = {"component_id": "nextcloud", "new_version": "30.0.0"}

    res = mgr.handle_client_response(
        analysis=analysis,
        client_response_text="UPDATE 4",
        client_id="ClientX",
    )
    assert res["action"] == "training_sandbox_requested"
    assert res["sandbox"]["success"] is True
    mock_sandbox.request_sandbox.assert_called_once_with(
        client_id="ClientX",
        component_id="nextcloud",
        target_version="30.0.0",
    )


def test_handle_client_response_production_scheduled_night():
    mgr = FleetUpdateManager()
    analysis = {"component_id": "nextcloud", "new_version": "30.0.0"}

    res = mgr.handle_client_response(
        analysis=analysis,
        client_response_text="UPDATE 2 A",
        client_id="ClientX",
    )
    assert res["action"] == "production_update_scheduled_night"
    assert res["schedule"] == "02:00"
    assert res["safety_level"] == "high_safety"


def test_handle_client_response_production_immediate_fast():
    mgr = FleetUpdateManager()
    analysis = {"component_id": "nextcloud", "new_version": "30.0.0"}

    res = mgr.handle_client_response(
        analysis=analysis,
        client_response_text="UPDATE 1 B",
        client_id="ClientX",
    )
    assert res["action"] == "production_update_immediate"
    assert res["safety_level"] == "fast_rolling"
