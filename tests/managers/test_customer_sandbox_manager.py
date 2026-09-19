# tests/managers/test_customer_sandbox_manager.py
"""Unit tests for Customer Interactive Sandbox Manager (De Proeftuin - Modus B)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from managers.customer_sandbox_manager import CustomerSandboxManager


def test_sandbox_provisioning_and_quota():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_sandboxes.db"
        mock_pve = MagicMock()
        mock_pve.get.return_value = {
            "data": [{"name": "eth0", "inet": "192.168.1.189/24"}]
        }

        mgr = CustomerSandboxManager(
            proxmox_client=mock_pve,
            db_path=db_file,
            max_sandboxes=2,
        )

        # 1. Request first sandbox
        res1 = mgr.request_sandbox(
            client_id="ClientA",
            component_id="nextcloud",
            target_version="30.0.0",
            ttl_days=14,
        )
        assert res1["success"] is True
        assert res1["vmid"] == 860
        assert res1["access_url"] == "https://clienta.training.njorddeploy.com"
        assert "Mailpit" in res1["mail_catcher"]

        # 2. Request second sandbox
        res2 = mgr.request_sandbox(
            client_id="ClientB",
            component_id="immich",
            target_version="1.118.0",
            ttl_days=7,
        )
        assert res2["success"] is True
        assert res2["vmid"] == 861

        # 3. Request third sandbox -> quota exceeded
        res3 = mgr.request_sandbox(
            client_id="ClientC",
            component_id="vaultwarden",
            target_version="1.32.0",
        )
        assert res3["success"] is False
        assert res3.get("quota_exceeded") is True
        assert "Concurrency quota exceeded" in res3["error"]


def test_uat_sign_off_and_teardown():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_sandboxes.db"
        mock_pve = MagicMock()
        mock_pve.get.return_value = {
            "data": [{"name": "eth0", "inet": "192.168.1.189/24"}]
        }

        mgr = CustomerSandboxManager(
            proxmox_client=mock_pve,
            db_path=db_file,
        )

        res = mgr.request_sandbox(
            client_id="AcmeCorp",
            component_id="nextcloud",
            target_version="30.0.0",
        )
        s_id = res["sandbox_id"]
        vmid = res["vmid"]

        # Key-user completes UAT and signs off
        signoff_res = mgr.sign_off_uat(
            sandbox_id=s_id,
            key_user_notes="Tested contact sync and new files UI - all approved!",
        )
        assert signoff_res["success"] is True
        assert signoff_res["uat_signed_off"] is True
        assert signoff_res["status"] == "ready_for_production_schedule"

        # Verify Proxmox teardown
        mock_pve.stop_lxc.assert_called_with("pve", vmid)
        mock_pve.destroy_lxc.assert_called_with("pve", vmid)

        # Active list should now be empty
        active = mgr.get_active_sandboxes()
        assert len(active) == 0


def test_nightly_sleep_cycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_sandboxes.db"
        mock_pve = MagicMock()
        mock_pve.get.return_value = {
            "data": [{"name": "eth0", "inet": "192.168.1.189/24"}]
        }

        mgr = CustomerSandboxManager(
            proxmox_client=mock_pve,
            db_path=db_file,
        )

        mgr.request_sandbox("ClientNight", "nextcloud", "30.0.0")

        # Night time (e.g. 23:00)
        night_res = mgr.run_nightly_sleep_cycle(current_hour=23)
        assert night_res["slept"] == 1
        assert night_res["woken"] == 0

        # Day time (e.g. 09:00)
        day_res = mgr.run_nightly_sleep_cycle(current_hour=9)
        assert day_res["woken"] == 1
        assert day_res["slept"] == 0
