# tests/configurator_app/test_configurator_routes_advanced.py

"""Advanced route coverage for configurator_app.

Covers Settings updates, Tailscale scan, Proxmox LXC/VM creation,
Container logs, Device details, System analysis, Generated files preview,
Component selection validation, and Backup API lifecycle endpoints.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from configurator_app.app import create_app


class ConfiguratorAdvancedRoutesTestCase(unittest.TestCase):
    """Deep coverage for advanced routes in Configurator App."""

    def setUp(self):
        """Initializes test client with patched managers."""
        self.patcher_manager = patch("configurator_app.app.ComponentManager")
        self.patcher_setup = patch("configurator_app.app.SetupManager")
        self.patcher_scanner = patch("configurator_app.app.NodeScanner")
        self.patcher_deploy = patch("configurator_app.app.DeploymentManager")

        self.mock_manager_class = self.patcher_manager.start()
        self.mock_setup_class = self.patcher_setup.start()
        self.mock_scanner_class = self.patcher_scanner.start()
        self.mock_deploy_class = self.patcher_deploy.start()

        self.mock_manager = self.mock_manager_class.return_value
        self.mock_setup = self.mock_setup_class.return_value
        self.mock_scanner = self.mock_scanner_class.return_value
        self.mock_deploy = self.mock_deploy_class.return_value

        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher_manager.stop()
        self.patcher_setup.stop()
        self.patcher_scanner.stop()
        self.patcher_deploy.stop()

    def test_settings_update_raw_and_form_and_invalid(self):
        """Verifies /api/settings with raw, form, and invalid modes."""
        # 1. Invalid mode
        res_invalid = self.client.post("/api/settings", json={"mode": "unknown"})
        self.assertEqual(res_invalid.status_code, 400)

        # 2. Raw mode
        with patch("builtins.open", mock_open()):
            res_raw = self.client.post(
                "/api/settings",
                json={"mode": "raw", "raw_content": "FOO=baz\nNEW_KEY=123\n"},
            )
            self.assertEqual(res_raw.status_code, 200)

        # 3. Form mode invalid settings
        res_bad_form = self.client.post(
            "/api/settings",
            json={"mode": "form", "settings": "not-a-dict"},
        )
        self.assertEqual(res_bad_form.status_code, 400)

        # 4. Form mode valid
        form_data = "FOO=old\n# Comment\nBAR=keep\n"
        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.open", mock_open(read_data=form_data)),
        ):
            res_form = self.client.post(
                "/api/settings",
                json={
                    "mode": "form",
                    "settings": {"FOO": "new_val", "ADDED": "extra"},
                },
            )
            self.assertEqual(res_form.status_code, 200)

    def test_scan_pis_tailscale_discovery(self):
        """Verifies /scan-pis with discovery_method='tailscale'."""
        with patch("configurator_app.app.get_tailscale_status") as mock_ts:
            # Active tailscale
            mock_ts.return_value = {
                "active": True,
                "peers": [{"ip": "100.64.0.1", "name": "node-1"}],
            }
            res_active = self.client.post(
                "/scan-pis", json={"discovery_method": "tailscale"}
            )
            self.assertEqual(res_active.status_code, 200)
            data_active = res_active.get_json()
            peers = data_active.get("hosts", [])
            peer, *_ = peers
            self.assertEqual(peer["name"], "node-1")

            # Inactive tailscale
            mock_ts.return_value = {"active": False, "reason": "Daemon stopped"}
            res_inactive = self.client.post(
                "/scan-pis", json={"discovery_method": "tailscale"}
            )
            self.assertEqual(res_inactive.status_code, 400)
            data_inactive = res_inactive.get_json()
            self.assertIn("Daemon stopped", data_inactive.get("error", ""))

    def test_proxmox_create_lxc_route(self):
        """Verifies /api/proxmox/create-lxc validation, pre-flight, and creation."""
        # 1. Missing credentials
        with patch.dict("os.environ", {"PROXMOX_TOKEN_ID": ""}):
            res_no_token = self.client.post("/api/proxmox/create-lxc", json={})
            self.assertEqual(res_no_token.status_code, 500)

        # Mock Proxmox credentials in environment
        env_vars = {
            "PROXMOX_TOKEN_ID": "test-token",
            "PROXMOX_TOKEN_SECRET": "secret",
            "PROXMOX_NODE": "pve",
        }

        with (
            patch.dict("os.environ", env_vars),
            patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class,
            patch("managers.ssh_manager.SSHManager") as mock_ssh_class,
        ):
            mock_client = mock_pve_class.return_value
            mock_ssh = mock_ssh_class.return_value
            mock_ssh.get_ssh_key.return_value = MagicMock(
                get_name=lambda: "ssh-ed25519",
                get_base64=lambda: "dummy_base64",
            )

            # 2. Duplicate hostname check
            mock_client.get_lxc_list.return_value = [
                {"name": "my-ct", "vmid": 105, "status": "running"}
            ]
            res_dup = self.client.post(
                "/api/proxmox/create-lxc", json={"hostname": "my-ct"}
            )
            self.assertEqual(res_dup.status_code, 409)

            # 3. Stale CTs threshold
            mock_client.get_lxc_list.return_value = [
                {"name": f"stale-{i}", "vmid": 200 + i, "status": "stopped"}
                for i in range(11)
            ]
            res_stale = self.client.post(
                "/api/proxmox/create-lxc", json={"hostname": "fresh-ct"}
            )
            self.assertEqual(res_stale.status_code, 409)

            # 4. Successful creation
            mock_client.get_lxc_list.return_value = []
            mock_client.get_next_vmid.return_value = 300
            mock_client.get.side_effect = [
                # storage list
                {"data": [{"active": True, "content": "vztmpl", "storage": "local"}]},
                # content list
                {"data": [{"volid": "local:vztmpl/debian-12-standard.tar.zst"}]},
                # task status
                {"data": {"status": "stopped", "exitstatus": "OK"}},
                # interfaces poll
                {"data": [{"name": "eth0", "inet": "192.168.1.180/24"}]},
            ]
            mock_client.create_lxc.return_value = {"data": "UPID:pve:0001"}
            mock_client.start_lxc.return_value = {"data": "UPID:pve:0002"}
            mock_client.get_target_ip.return_value = "192.168.1.180"

            mock_ssh.connect.return_value = (True, "Connected")
            mock_ssh.execute_command.return_value = (0, "Success")

            with (
                patch("time.sleep", return_value=None),
                patch.object(self.app, "extensions", {}),
            ):
                res_ok = self.client.post(
                    "/api/proxmox/create-lxc",
                    json={"hostname": "valid-ct", "cores": 2, "memory": 2048},
                )
                self.assertEqual(res_ok.status_code, 201)
                data = res_ok.get_json()
                self.assertEqual(data.get("status"), "success")
                self.assertEqual(data.get("vmid"), 300)

    def test_proxmox_create_vm_and_templates(self):
        """Verifies /api/proxmox/list-templates and /api/proxmox/create-vm."""
        # 1. Missing credentials
        with patch.dict("os.environ", {"PROXMOX_TOKEN_ID": ""}):
            res_list_no_token = self.client.post("/api/proxmox/list-templates", json={})
            self.assertEqual(res_list_no_token.status_code, 200)
            self.assertFalse(res_list_no_token.get_json().get("configured"))

            res_vm_no_token = self.client.post(
                "/api/proxmox/create-vm", json={"template_vmid": 900}
            )
            self.assertEqual(res_vm_no_token.status_code, 500)

        env_vars = {
            "PROXMOX_TOKEN_ID": "token",
            "PROXMOX_TOKEN_SECRET": "secret",
            "PROXMOX_NODE": "pve",
        }

        with (
            patch.dict("os.environ", env_vars),
            patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class,
            patch("managers.ssh_manager.SSHManager") as mock_ssh_class,
        ):
            mock_client = mock_pve_class.return_value
            mock_ssh = mock_ssh_class.return_value

            # 2. List templates success
            mock_client.get.return_value = {
                "data": [
                    {"vmid": 900, "name": "debian-tmpl", "template": 1},
                    {"vmid": 100, "name": "regular-vm", "template": 0},
                ]
            }
            res_list = self.client.post("/api/proxmox/list-templates", json={})
            self.assertEqual(res_list.status_code, 200)
            tmpls = res_list.get_json().get("templates", [])
            self.assertEqual(len(tmpls), 1)
            tmpl, *_ = tmpls
            self.assertEqual(tmpl["name"], "debian-tmpl")

            # 3. Create VM validation: missing template_vmid
            res_bad_vmid = self.client.post("/api/proxmox/create-vm", json={})
            self.assertEqual(res_bad_vmid.status_code, 400)

            # 4. Create VM validation: non-integer template_vmid
            res_invalid_vmid = self.client.post(
                "/api/proxmox/create-vm", json={"template_vmid": "abc"}
            )
            self.assertEqual(res_invalid_vmid.status_code, 400)

            # 5. Create VM success with clone fallback and resize
            mock_client.get_vm_list.return_value = []
            mock_client.get_next_vmid.return_value = 500
            # clone_vm fails first with linked clone not supported, then succeeds
            mock_client.clone_vm.side_effect = [
                Exception("Linked clone feature is not supported"),
                {"data": "UPID:pve:clone01"},
            ]
            mock_client.get.side_effect = [
                # pre-flight vm list
                {"data": []},
                # task status
                {"data": {"status": "stopped", "exitstatus": "OK"}},
                # vm config for disk resize
                {"data": {"bootdisk": "scsi0"}},
            ]
            mock_client.get_vm_ip.return_value = "192.168.1.199"

            mock_ssh.get_ssh_key.return_value = MagicMock(
                get_name=lambda: "ssh-ed25519",
                get_base64=lambda: "dummy_key",
            )
            mock_ssh.connect.return_value = (True, "Connected")
            mock_ssh.execute_command.return_value = (0, "Success")

            with patch("time.sleep", return_value=None):
                res_create_vm = self.client.post(
                    "/api/proxmox/create-vm",
                    json={
                        "template_vmid": 900,
                        "hostname": "my-cloud-vm",
                        "storage_size": 32,
                    },
                )
                self.assertEqual(res_create_vm.status_code, 201)
                vm_data = res_create_vm.get_json()
                self.assertEqual(vm_data.get("status"), "success")
                self.assertEqual(vm_data.get("ip"), "192.168.1.199")

    def test_get_device_details_route(self):
        """Verifies /get-device-details validation and snapshot parsing."""
        # 1. Missing fields
        res_missing = self.client.post("/get-device-details", json={})
        self.assertEqual(res_missing.status_code, 400)

        # 2. Scanner error
        self.mock_scanner.get_system_snapshot.return_value = (None, "SSH Timeout")
        res_err = self.client.post(
            "/get-device-details",
            json={
                "ip": "192.168.1.50",
                "username": "pi",
                "password": "pwd",
            },
        )
        self.assertEqual(res_err.status_code, 400)

        # 3. Successful snapshot
        snapshot_data = {
            "model": "Raspberry Pi 5",
            "serial": "10000000abcde",
            "os_version": "Debian 12",
            "docker_is_active": True,
            "resources": {
                "ram": {"total_mb": 8192},
                "disk": {"size": "64G", "pcent": "25%"},
            },
        }
        self.mock_scanner.get_system_snapshot.return_value = (
            snapshot_data,
            None,
        )
        res_ok = self.client.post(
            "/get-device-details",
            json={
                "ip": "192.168.1.50",
                "username": "pi",
                "password": "pwd",
            },
        )
        self.assertEqual(res_ok.status_code, 200)
        data = res_ok.get_json()
        self.assertEqual(data.get("model"), "Raspberry Pi 5")
        self.assertEqual(data.get("ram"), "8192 MB")

    def test_system_analyze_route(self):
        """Verifies /api/v1/system/analyze port conflicts and snapshot analysis."""
        # 1. Missing devices or components
        res_bad = self.client.post("/api/v1/system/analyze", json={})
        self.assertEqual(res_bad.status_code, 400)

        # 2. Internal port conflict
        self.mock_manager.get_all_components.return_value = []
        payload_conflict = {
            "devices": [{"ip": "192.168.1.50", "username": "pi", "password": "p"}],
            "components": [
                {"id": "comp_1", "name": "App 1", "ports": ["8080:80"]},
                {"id": "comp_2", "name": "App 2", "ports": ["8080:8080"]},
            ],
        }
        res_conflict = self.client.post("/api/v1/system/analyze", json=payload_conflict)
        self.assertEqual(res_conflict.status_code, 400)
        self.assertIn("Port 8080 is used by", res_conflict.get_json()["error"])

        # 3. Successful analysis
        payload_ok = {
            "devices": [{"ip": "192.168.1.50", "username": "pi", "password": "p"}],
            "components": [{"id": "caddy", "name": "Caddy", "ports": ["80:80"]}],
        }
        self.mock_scanner.get_system_snapshot.return_value = (
            {"resources": {}},
            None,
        )
        with patch("configurator_app.app.analyze_snapshot", return_value=([], [])):
            res_analysis = self.client.post("/api/v1/system/analyze", json=payload_ok)
            self.assertEqual(res_analysis.status_code, 200)

    def test_get_container_logs_route(self):
        """Verifies /get-container-logs validation and log retrieval."""
        # 1. Missing fields
        res_missing = self.client.post("/get-container-logs", json={})
        self.assertEqual(res_missing.status_code, 400)

        # 2. Invalid container name
        res_invalid_name = self.client.post(
            "/get-container-logs",
            json={
                "ip": "192.168.1.50",
                "username": "pi",
                "password": "pwd",
                "container_name": "bad; name&&injection",
            },
        )
        self.assertEqual(res_invalid_name.status_code, 400)

        # 3. SSH connection failure
        with patch("managers.ssh_manager.SSHManager") as mock_ssh_class:
            mock_ssh = mock_ssh_class.return_value
            mock_ssh.connect.return_value = (False, "Connection timed out")

            with patch("time.sleep", return_value=None):
                res_ssh_err = self.client.post(
                    "/get-container-logs",
                    json={
                        "ip": "192.168.1.50",
                        "username": "pi",
                        "password": "pwd",
                        "container_name": "njorddeploy-app",
                    },
                )
                self.assertEqual(res_ssh_err.status_code, 400)

            # 4. Successful log retrieval with ANSI color stripping
            mock_ssh.connect.return_value = (True, "Connected")

            def mock_exec(cmd, callback=None, **kwargs):
                if callback:
                    callback("\x1b[32mContainer started successfully\x1b[0m\n")
                return (0, "Container started successfully\n")

            mock_ssh.execute_command.side_effect = mock_exec

            res_ok = self.client.post(
                "/get-container-logs",
                json={
                    "ip": "192.168.1.50",
                    "username": "pi",
                    "password": "pwd",
                    "container_name": "njorddeploy-app",
                },
            )
            self.assertEqual(res_ok.status_code, 200)
            logs = res_ok.get_json().get("logs", "")
            self.assertIn("Container started successfully", logs)
            self.assertNotIn("\x1b[32m", logs)

    def test_get_generated_files_route(self):
        """Verifies /get-generated-files directory traversal protection and preview."""
        # 1. Missing output_path
        res_missing = self.client.post("/get-generated-files", json={})
        self.assertEqual(res_missing.status_code, 400)

        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            with patch("configurator_app.app.get_app_data_dir", return_value=base_dir):
                # 2. Directory does not exist
                res_404 = self.client.post(
                    "/get-generated-files",
                    json={"output_path": "nonexistent_folder"},
                )
                self.assertEqual(res_404.status_code, 404)

                # 3. Successful read with root compose and selected subdir
                out_dir = base_dir / "my_deploy"
                out_dir.mkdir()
                (out_dir / "docker-compose.yml").write_text(
                    "services:\n", encoding="utf-8"
                )

                sub_dir = out_dir / "vaultwarden"
                sub_dir.mkdir()
                (sub_dir / "config.env").write_text("KEY=VAL", encoding="utf-8")

                res_ok = self.client.post(
                    "/get-generated-files",
                    json={
                        "output_path": "my_deploy",
                        "selected_components": ["vaultwarden"],
                    },
                )
                self.assertEqual(res_ok.status_code, 200)
                files = res_ok.get_json().get("files", {})
                self.assertIn("docker-compose.yml", files)
                self.assertIn("vaultwarden/config.env", files)

    def test_backup_api_lifecycle_endpoints(self):
        """Verifies backup discover, inspect, create, list, and restore endpoints."""
        with (
            patch("configurator_app.app.SSHManager") as mock_ssh_class,
            patch("configurator_app.app.BackupManager") as mock_bm_class,
        ):
            mock_ssh = mock_ssh_class.return_value
            mock_bm = mock_bm_class.return_value

            # Missing credentials on discover
            res_bad_disc = self.client.post("/api/backup/discover-compose", json={})
            self.assertEqual(res_bad_disc.status_code, 400)

            # Successful discover
            mock_ssh.connect.return_value = (True, "Connected")
            mock_bm.discover_compose_files.return_value = [
                {"directory": "/opt/njorddeploy"}
            ]

            payload = {
                "ip": "192.168.1.50",
                "username": "pi",
                "password": "pwd",
            }

            res_disc = self.client.post("/api/backup/discover-compose", json=payload)
            self.assertEqual(res_disc.status_code, 200)
            self.assertEqual(res_disc.get_json()["suggested_path"], "/opt/njorddeploy")

            # Inspect
            mock_bm.inspect_target.return_value = {
                "status": "success",
                "storage": {},
            }
            res_insp = self.client.post("/api/backup/inspect", json=payload)
            self.assertEqual(res_insp.status_code, 200)

            # Create backup
            mock_bm.create_backup.return_value = {
                "status": "success",
                "archive": "backup.tar.gz",
            }
            res_create = self.client.post("/api/backup/create", json=payload)
            self.assertEqual(res_create.status_code, 200)

            # List backups
            mock_bm.list_backups.return_value = [{"filename": "backup.tar.gz"}]
            res_list = self.client.post("/api/backup/list", json=payload)
            self.assertEqual(res_list.status_code, 200)
            backups = res_list.get_json()["backups"]
            first_backup, *_ = backups
            self.assertEqual(first_backup["filename"], "backup.tar.gz")

            # Restore backup
            mock_bm.restore_backup.return_value = {
                "status": "success",
                "message": "Restored",
            }
            res_restore = self.client.post(
                "/api/backup/restore",
                json={**payload, "backup_filename": "backup.tar.gz"},
            )
            self.assertEqual(res_restore.status_code, 200)

    def test_proxmox_config_endpoints(self):
        """Verifies Proxmox status, test, and save endpoints."""
        # 1. Status: unconfigured
        with patch.dict(
            "os.environ",
            {
                "PROXMOX_HOST": "",
                "PROXMOX_TOKEN_ID": "",
                "PROXMOX_TOKEN_SECRET": "",
            },
        ):
            res_status = self.client.get("/api/config/proxmox/status")
            self.assertEqual(res_status.status_code, 200)
            data_status = res_status.get_json()
            self.assertFalse(data_status["configured"])
            self.assertFalse(data_status["has_token_secret"])

        # 2. Status: configured with live check
        with (
            patch.dict(
                "os.environ",
                {
                    "PROXMOX_HOST": "https://192.168.1.100:8006",
                    "PROXMOX_TOKEN_ID": "token",
                    "PROXMOX_TOKEN_SECRET": "secret",
                },
            ),
            patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class,
        ):
            mock_client = mock_pve_class.return_value
            mock_client.get.return_value = {"data": {"version": "8.2.4"}}
            res_live = self.client.get("/api/config/proxmox/status?check=true")
            self.assertEqual(res_live.status_code, 200)
            self.assertTrue(res_live.get_json()["configured"])
            self.assertTrue(res_live.get_json()["connection_healthy"])

        # 3. Test: missing credentials
        res_test_bad = self.client.post(
            "/api/config/proxmox/test",
            json={"host": "", "token_id": "", "token_secret": ""},
        )
        self.assertEqual(res_test_bad.status_code, 400)

        # 4. Test: success
        with patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class:
            mock_client = mock_pve_class.return_value
            mock_client.get_version.return_value = {
                "data": {"version": "8.2.4", "release": "8.2"}
            }
            res_test_ok = self.client.post(
                "/api/config/proxmox/test",
                json={
                    "host": "https://192.168.1.100:8006",
                    "user": "root@pam",
                    "token_id": "root@pam!token",
                    "token_secret": "secret",
                    "node": "pve",
                },
            )
            self.assertEqual(res_test_ok.status_code, 200)
            self.assertTrue(res_test_ok.get_json()["success"])
            self.assertEqual(res_test_ok.get_json()["pve_version"], "8.2.4")

        # 5. Test: connection exception
        with patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class:
            mock_client = mock_pve_class.return_value
            mock_client.get_version.side_effect = RuntimeError("Connection timeout")
            res_test_fail = self.client.post(
                "/api/config/proxmox/test",
                json={
                    "host": "https://192.168.1.100:8006",
                    "token_id": "tok",
                    "token_secret": "sec",
                },
            )
            self.assertEqual(res_test_fail.status_code, 200)
            self.assertFalse(res_test_fail.get_json()["success"])

        # 6. Save: missing required fields
        res_save_bad = self.client.post(
            "/api/config/proxmox/save",
            json={"host": "", "token_id": ""},
        )
        self.assertEqual(res_save_bad.status_code, 400)

        # 7. Save: success with mock open
        with patch("builtins.open", unittest.mock.mock_open(read_data="FOO=bar\n")):
            res_save_ok = self.client.post(
                "/api/config/proxmox/save",
                json={
                    "host": "https://192.168.1.100:8006",
                    "token_id": "root@pam!tok",
                    "token_secret": "new_secret",
                    "node": "pve",
                },
            )
            self.assertEqual(res_save_ok.status_code, 200)
            self.assertTrue(res_save_ok.get_json()["success"])

        # 8. Status with SSH manager exception
        with patch(
            "managers.ssh_manager.SSHManager.get_public_key_string",
            side_effect=RuntimeError("No key"),
        ):
            res_ssh_err = self.client.get("/api/config/proxmox/status")
            self.assertEqual(res_ssh_err.status_code, 200)
            self.assertEqual(res_ssh_err.get_json()["public_key"], "")

        # 9. Save: updating existing key in .env and chmod OSError fallback
        with (
            patch(
                "builtins.open",
                unittest.mock.mock_open(read_data="PROXMOX_HOST=old_host\n# comment\n"),
            ),
            patch("os.chmod", side_effect=OSError("chmod failed")),
        ):
            res_save_update = self.client.post(
                "/api/config/proxmox/save",
                json={
                    "host": "https://192.168.1.100:8006",
                    "token_id": "root@pam!tok",
                    "token_secret": "new_secret",
                    "node": "pve",
                },
            )
            self.assertEqual(res_save_update.status_code, 200)
            self.assertTrue(res_save_update.get_json()["success"])

        # 10. Save: file write error returns 500
        with patch("builtins.open", side_effect=OSError("Disk write error")):
            res_save_fail = self.client.post(
                "/api/config/proxmox/save",
                json={
                    "host": "https://192.168.1.100:8006",
                    "token_id": "root@pam!tok",
                },
            )
            self.assertEqual(res_save_fail.status_code, 500)
            self.assertFalse(res_save_fail.get_json()["success"])
