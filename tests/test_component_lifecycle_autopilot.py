# tests/test_component_lifecycle_autopilot.py
"""Unit tests for NjordDeploy Component Lifecycle Autopilot."""

import json
from unittest.mock import MagicMock, patch

from scripts.component_lifecycle_autopilot import (
    dispatch_escalation_alert,
    dispatch_success_report,
    get_candidates,
    main,
    mark_candidate_needs_review,
    run_proeftuin_test,
    send_signal_alert,
)


def test_get_candidates_filtering_and_sorting():
    """Verifies candidate detection, security prioritization, and pinning."""
    mock_metadata = {
        "components": {
            "caddy": {
                "group": "reverse_proxy",
                "pinned": False,
                "staging": {"status": "candidate", "version": "2.11.8"},
            },
            "mealie": {
                "group": "Lifestyle & Automation",
                "pinned": False,
                "staging": {"status": "candidate", "version": "3.30.0"},
            },
            "pi-hole": {
                "group": "dns_blocker",
                "pinned": True,  # Pinned: must be excluded!
                "staging": {"status": "candidate", "version": "2026.10.0"},
            },
            "idle-app": {
                "group": "Tools",
                "staging": {"status": "idle", "version": "1.0.0"},
            },
        }
    }

    candidates = get_candidates(mock_metadata)
    assert len(candidates) == 2
    # Caddy is security -> must be first
    assert candidates[0][0] == "caddy"
    assert candidates[0][1] == "2.11.8"
    assert candidates[0][2] is True

    # Mealie is standard -> must be second
    assert candidates[1][0] == "mealie"
    assert candidates[1][1] == "3.30.0"
    assert candidates[1][2] is False

    # Filtered by ID
    filtered = get_candidates(mock_metadata, filter_ids=["mealie"])
    assert len(filtered) == 1
    assert filtered[0][0] == "mealie"


@patch("urllib.request.urlopen")
def test_send_signal_alert_success(mock_urlopen):
    """Verifies that Signal alerts are posted with valid payload."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    success = send_signal_alert("Test Alert Message")
    assert success is True
    assert mock_urlopen.called


@patch("urllib.request.urlopen")
def test_send_signal_alert_network_failure(mock_urlopen):
    """Verifies graceful handling of Signal API network failure."""
    mock_urlopen.side_effect = OSError("Connection refused")
    success = send_signal_alert("Test Alert Message")
    assert success is False


@patch("scripts.component_lifecycle_autopilot.load_metadata")
@patch("scripts.component_lifecycle_autopilot.save_metadata")
@patch("scripts.component_lifecycle_autopilot.sync_sysopswatch")
def test_mark_candidate_needs_review(mock_sync, mock_save, mock_load):
    """Verifies that failing candidate is marked as needs_review in staging."""
    fake_meta = {
        "components": {
            "immich": {
                "staging": {"status": "candidate", "version": "1.118.0"}
            }
        }
    }
    mock_load.return_value = fake_meta

    mark_candidate_needs_review(
        "immich", "1.118.0", "Container failed health check"
    )

    saved_meta = mock_save.call_args[0][0]
    staging = saved_meta["components"]["immich"]["staging"]
    assert staging["status"] == "needs_review"
    assert "Container failed health check" in staging["last_test_error"]
    assert "last_test_timestamp" in staging
    assert mock_sync.called


@patch("scripts.component_lifecycle_autopilot.send_signal_alert")
def test_dispatch_escalation_alert(mock_send_signal):
    """Verifies escalation alert formatting for human-in-the-loop guidance."""
    dispatch_escalation_alert(
        comp_id="nextcloud",
        version="30.0.1",
        error_details="Database connection timeout",
    )
    assert mock_send_signal.called
    msg = mock_send_signal.call_args[0][0]
    assert "Toestemming & Actie vereist" in msg
    assert "nextcloud" in msg
    assert "30.0.1" in msg
    assert "Database connection timeout" in msg


@patch("scripts.component_lifecycle_autopilot.send_signal_alert")
def test_dispatch_success_report(mock_send_signal):
    """Verifies green success report formatting."""
    dispatch_success_report(
        passed_comps=[("caddy", "2.11.8"), ("dockge", "1.5.1")],
        remaining_candidates=0,
    )
    assert mock_send_signal.called
    msg = mock_send_signal.call_args[0][0]
    assert "Ochtendronde Voltooid" in msg
    assert "caddy" in msg
    assert "dockge" in msg
    assert "Wachtkamer is schoon" in msg


@patch("subprocess.run")
def test_run_proeftuin_test_success(mock_subproc, tmp_path):
    """Verifies test runner invocation and success parsing."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_subproc.return_value = mock_proc

    results_file = tmp_path / "proxmox_results.json"
    results_file.write_text(
        json.dumps(
            [
                {
                    "component_id": "caddy",
                    "status": "success",
                    "http_ok": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    with patch(
        "scripts.component_lifecycle_autopilot.RESULTS_JSON_PATH",
        results_file,
    ):
        success, err = run_proeftuin_test("caddy", template_id=912)
        assert success is True
        assert err == ""


@patch("subprocess.run")
def test_run_proeftuin_test_failure(mock_subproc, tmp_path):
    """Verifies test runner failure parsing from results json."""
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "Error: Container crashed"
    mock_subproc.return_value = mock_proc

    results_file = tmp_path / "proxmox_results.json"
    results_file.write_text(
        json.dumps(
            [
                {
                    "component_id": "caddy",
                    "status": "failed",
                    "http_ok": False,
                    "error_message": "Container crashed with exit 137",
                }
            ]
        ),
        encoding="utf-8",
    )

    with patch(
        "scripts.component_lifecycle_autopilot.RESULTS_JSON_PATH",
        results_file,
    ):
        success, err = run_proeftuin_test("caddy", template_id=912)
        assert success is False
        assert "Container crashed with exit 137" in err


@patch("scripts.component_lifecycle_autopilot.run_upstream_check")
@patch("scripts.component_lifecycle_autopilot.load_metadata")
def test_main_no_candidates(mock_load, mock_scan):
    """Verifies main exits cleanly when no candidates exist."""
    mock_load.return_value = {"components": {}}
    with patch("sys.argv", ["component_lifecycle_autopilot.py", "--skip-scan"]):
        ret = main()
        assert ret == 0


@patch("scripts.component_lifecycle_autopilot.load_metadata")
@patch("scripts.component_lifecycle_autopilot.run_proeftuin_test")
@patch("scripts.component_lifecycle_autopilot.sync_and_publish_all")
@patch("scripts.component_lifecycle_autopilot.dispatch_success_report")
def test_main_happy_flow(
    mock_report, mock_sync, mock_test, mock_load
):
    """Verifies happy flow where all candidates pass and publish."""
    mock_load.return_value = {
        "components": {
            "gotify": {
                "staging": {"status": "candidate", "version": "3.1.2"}
            }
        }
    }
    mock_test.return_value = (True, "")

    with patch(
        "sys.argv",
        [
            "component_lifecycle_autopilot.py",
            "--skip-scan",
            "--components",
            "gotify",
        ],
    ):
        ret = main()
        assert ret == 0
        assert mock_test.called
        assert mock_sync.called
        assert mock_report.called


@patch("scripts.component_lifecycle_autopilot.load_metadata")
@patch("scripts.component_lifecycle_autopilot.run_proeftuin_test")
@patch("scripts.component_lifecycle_autopilot.mark_candidate_needs_review")
@patch("scripts.component_lifecycle_autopilot.dispatch_escalation_alert")
def test_main_exception_flow(
    mock_alert, mock_mark, mock_test, mock_load
):
    """Verifies exception flow where candidate fails, alerts, and stops."""
    mock_load.return_value = {
        "components": {
            "immich": {
                "staging": {"status": "candidate", "version": "1.118.0"}
            }
        }
    }
    mock_test.return_value = (False, "Database migration failure")

    with patch(
        "sys.argv",
        [
            "component_lifecycle_autopilot.py",
            "--skip-scan",
            "--components",
            "immich",
        ],
    ):
        ret = main()
        assert ret == 1
        assert mock_mark.called
        assert mock_alert.called
