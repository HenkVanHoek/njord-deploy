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


def test_customer_sandbox_edge_cases():
    """Test exceptions in clone, destroy, non-existent sandbox, and expired purge."""
    from datetime import datetime, timedelta
    from unittest.mock import patch

    import pytest

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_sandboxes_edges.db"
        mock_pve = MagicMock()

        mgr = CustomerSandboxManager(
            proxmox_client=mock_pve,
            db_path=db_file,
        )

        # 1. Non-existent sandbox operations
        assert mgr.destroy_sandbox(9999) is False
        sign_err = mgr.sign_off_uat(9999)
        assert sign_err["success"] is False
        assert "not found" in sign_err["error"]

        # 2. Provisioning exception
        mock_pve.clone_lxc.side_effect = Exception("Storage full on PVE")
        req_err = mgr.request_sandbox("ClientErr", "app", "1.0")
        assert req_err["success"] is False
        assert "Storage full on PVE" in req_err["error"]

        # 3. Connection rollback
        with pytest.raises(RuntimeError):
            with mgr._get_connection() as conn:
                conn.execute(
                    "INSERT INTO sandboxes (client_id, component_id, version, "
                    "vmid, status, created_at, expires_at) "
                    "VALUES ('fail', 'app', '1.0', 999, 'active', 'now', 'now');"
                )
                raise RuntimeError("Abort transaction")

        # 4. Destroy with PVE exception
        mock_pve.clone_lxc.side_effect = None
        mock_pve.get.return_value = {"data": [{"name": "eth0", "inet": "10.0.0.1/24"}]}
        mock_pve.destroy_lxc.side_effect = Exception("PVE destroy error")
        created = mgr.request_sandbox("ClientDest", "app", "1.0")
        assert mgr.destroy_sandbox(created["sandbox_id"]) is True

        # 5. Nightly cycle with PVE exceptions
        mock_pve.stop_lxc.side_effect = None
        mock_pve.start_lxc.side_effect = None
        c2 = mgr.request_sandbox("ClientNightErr", "app", "1.0")
        assert c2["success"] is True

        mock_pve.stop_lxc.side_effect = Exception("Stop failed")
        mock_pve.start_lxc.side_effect = Exception("Start failed")
        res_night = mgr.run_nightly_sleep_cycle(22)
        assert res_night["slept"] == 1
        res_day = mgr.run_nightly_sleep_cycle(10)
        assert res_day["woken"] == 1

        # 6. Purge expired sandboxes
        with mgr._get_connection() as conn:
            expired_time = (datetime.now() - timedelta(days=20)).isoformat()
            conn.execute(
                "UPDATE sandboxes SET expires_at = ? WHERE id = ?;",
                (expired_time, c2["sandbox_id"]),
            )
        assert mgr.purge_expired_sandboxes() >= 1

        # 7. _wait_for_lxc_ip without proxmox_client and default db_path
        with patch(
            "src.managers.customer_sandbox_manager.get_app_data_dir",
            return_value=Path(tmpdir),
        ):
            mgr_no_pve = CustomerSandboxManager(proxmox_client=None)
            assert mgr_no_pve._wait_for_lxc_ip(101) == "127.0.0.1"

        # 8. _wait_for_lxc_ip exception handling inside while loop
        mock_pve.get.side_effect = Exception("PVE Network Timeout")
        times = [100.0, 101.0, 110.0]
        with patch("time.time", side_effect=times):
            with patch("time.sleep", return_value=None):
                assert mgr._wait_for_lxc_ip(101, timeout_seconds=5) is None
