# tests/configurator_app/test_configurator_routes_extended.py

"""
Comprehensive extended route coverage for configurator_app.
Covers metadata, documentation, Proxmox orchestration, language switching,
task streaming, evaluation, and backup download endpoints.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from configurator_app.app import create_app


class ConfiguratorExtendedRoutesTestCase(unittest.TestCase):

    def setUp(self):
        """Initializes the Flask test client with mocks for managers."""
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

    def test_static_and_doc_routes(self):
        """Verifies documentation, crawler, and meta endpoints."""
        res_robots = self.client.get("/robots.txt")
        self.assertEqual(res_robots.status_code, 200)

        res_llms = self.client.get("/llms.txt")
        self.assertEqual(res_llms.status_code, 200)

        res_llms_full = self.client.get("/llms-full.txt")
        self.assertEqual(res_llms_full.status_code, 200)

        res_help = self.client.get("/help")
        self.assertEqual(res_help.status_code, 200)

        res_settings = self.client.get("/settings")
        self.assertEqual(res_settings.status_code, 200)

    def test_system_status_routes(self):
        """Verifies nmap, tailscale, and first-run status checks."""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            res_nmap = self.client.get("/nmap-status")
            self.assertEqual(res_nmap.status_code, 200)
            self.assertTrue(res_nmap.get_json()["installed"])

            res_tailscale = self.client.get("/tailscale-status")
            self.assertEqual(res_tailscale.status_code, 200)

        res_first_run = self.client.get("/api/first-run-status")
        self.assertEqual(res_first_run.status_code, 200)

    def test_language_switching(self):
        """Verifies session language mutation and validation."""
        res_nl = self.client.post("/api/v1/set-language/nl")
        self.assertEqual(res_nl.status_code, 200)
        self.assertEqual(res_nl.get_json()["language"], "nl")

        res_en = self.client.get("/set-language/en")
        self.assertEqual(res_en.status_code, 302)

        res_invalid = self.client.post("/api/v1/set-language/invalid_lang")
        self.assertEqual(res_invalid.status_code, 400)

    def test_engine_switch(self):
        """Verifies container engine switching between docker and podman."""
        with patch("builtins.open", unittest.mock.mock_open()):
            res_switch = self.client.post(
                "/api/engine-switch",
                json={"engine": "podman"},
            )
            self.assertEqual(res_switch.status_code, 200)

            res_bad = self.client.post(
                "/api/engine-switch",
                json={"engine": "invalid_engine"},
            )
            self.assertEqual(res_bad.status_code, 400)

    def test_validate_repo(self):
        """Verifies remote repository URL and branch validation."""
        with patch(
            "managers.sync_manager.SyncManager.validate_remote_repo",
            return_value=(True, "OK"),
        ):
            res = self.client.post(
                "/api/validate-repo",
                json={
                    "url": (
                        "https://github.com/HenkVanHoek/" "njord-deploy-components.git"
                    ),
                    "branch": "main",
                },
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()["valid"])

    def test_software_and_groups_endpoints(self):
        """Verifies /get-available-software and /get-software-groups."""
        self.mock_manager.get_all_components.return_value = [
            {"id": "adguard-home", "name": "AdGuard", "group": "dns"}
        ]
        self.mock_manager.get_all_packages.return_value = []
        self.mock_manager.get_njorddeploy_meta.return_value = {
            "group_rules": {"dns": {"name": "DNS Services", "is_exclusive": True}},
            "group_order": ["dns"],
        }

        res_software = self.client.post("/get-available-software")
        self.assertEqual(res_software.status_code, 200)
        self.assertIn("available_software", res_software.get_json())

        res_groups = self.client.get("/get-software-groups")
        self.assertEqual(res_groups.status_code, 200)
        self.assertIn("DNS Services", res_groups.get_json()["groups"])

    def test_get_required_variables(self):
        """Verifies /get-required-variables payload handling."""
        res_empty = self.client.post("/get-required-variables", json={})
        self.assertEqual(res_empty.status_code, 400)

        self.mock_manager.get_all_components.return_value = [
            {"id": "caddy", "name": "Caddy", "variables": [{"name": "PORT"}]}
        ]
        res_valid = self.client.post(
            "/get-required-variables",
            json={"selected_components": ["caddy"]},
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertIn("caddy", res_valid.get_json()["components"])

    def test_validate_selection(self, tmp_path=None):
        """Verifies /validate-selection directory and variable verification."""
        res_bad = self.client.post("/validate-selection", json={})
        self.assertEqual(res_bad.status_code, 400)

        # Path traversal mitigation check
        res_traversal = self.client.post(
            "/validate-selection",
            json={"selected_components": ["../../etc/passwd"]},
        )
        self.assertEqual(res_traversal.status_code, 400)

    def test_task_status_and_streaming(self):
        """Verifies /task-status and /stream-deployment endpoints."""
        res_404 = self.client.get("/task-status/nonexistent_task")
        self.assertEqual(res_404.status_code, 404)

        # Register task in deployment_tasks dictionary
        self.app.deployment_tasks["test_task_123"] = {
            "status": "completed",
            "logs": ["Step 1 done", "Step 2 done"],
        }

        res_200 = self.client.get("/task-status/test_task_123")
        self.assertEqual(res_200.status_code, 200)
        self.assertEqual(res_200.get_json()["status"], "completed")

        res_stream = self.client.get("/stream-deployment/test_task_123")
        self.assertEqual(res_stream.status_code, 200)
        self.assertIn("text/event-stream", res_stream.content_type)
        stream_data = res_stream.data.decode("utf-8")
        self.assertIn("Step 1 done", stream_data)

    def test_evaluate_deployment_task(self):
        """Verifies /api/deployment/<task_id>/evaluate endpoint."""
        res_404 = self.client.post("/api/deployment/unknown_task/evaluate")
        self.assertEqual(res_404.status_code, 404)

        self.app.deployment_tasks["eval_task_456"] = {
            "status": "completed",
            "logs": ["Deployment finished successfully."],
        }
        with patch(
            "src.configurator_app.app.evaluate_deployment",
            return_value={"status": "GREEN", "summary": "Healthy"},
        ):
            res = self.client.post(
                "/api/deployment/eval_task_456/evaluate",
                json={"component_name": "adguard-home", "use_ai": False},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.get_json()["status"], "GREEN")

    def test_backup_download_route(self, tmp_path=None):
        """Verifies /api/backup/download/<filename> security and download delivery."""
        # Bad filename format (must match regex)
        res_bad_format = self.client.get("/api/backup/download/malicious.sh")
        self.assertEqual(res_bad_format.status_code, 400)

        # Valid filename format
        valid_fname = "njorddeploy_backup_20261001_120000.tar.gz"

        with patch("configurator_app.app.get_app_data_dir") as mock_dir:
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                staging = Path(temp_dir) / "backups_download"
                staging.mkdir(parents=True, exist_ok=True)
                mock_dir.return_value = Path(temp_dir)

                target_file = staging / valid_fname
                target_file.write_bytes(b"dummy_tar_gz_content")

                res_dl = self.client.get(f"/api/backup/download/{valid_fname}")
                self.assertEqual(res_dl.status_code, 200)
                self.assertEqual(res_dl.data, b"dummy_tar_gz_content")

    def test_proxmox_routes(self):
        """Verifies Proxmox VE orchestration routes."""
        env_vars = {
            "PROXMOX_TOKEN_ID": "token",
            "PROXMOX_TOKEN_SECRET": "secret",
            "PROXMOX_NODE": "pve",
        }
        with (
            patch.dict("os.environ", env_vars),
            patch("utils.proxmox_client.ProxmoxClient") as mock_pve,
        ):
            mock_client = mock_pve.return_value
            mock_client.connect.return_value = (True, "Connected")
            mock_client.list_templates.return_value = [{"vmid": 900, "name": "tmpl"}]
            mock_client.list_targets.return_value = [{"vmid": 100, "name": "ct"}]
            mock_client.get_target_ip.return_value = "192.168.1.150"
            mock_client.get.return_value = {
                "data": [{"name": "eth0", "inet": "192.168.1.150/24"}]
            }
            mock_client.start_target.return_value = (True, "Started")

            payload = {
                "ip": "192.168.1.10",
                "username": "root@pam",
                "password": "pve_password",
                "node": "pve",
                "vmid": 100,
                "type": "lxc",
            }

            res_tmpl = self.client.post("/api/proxmox/list-templates", json=payload)
            self.assertEqual(res_tmpl.status_code, 200)

            res_targets = self.client.post("/api/proxmox/list-targets", json=payload)
            self.assertEqual(res_targets.status_code, 200)

            res_ip = self.client.post("/api/proxmox/get-target-ip", json=payload)
            self.assertEqual(res_ip.status_code, 200)

            res_start = self.client.post("/api/proxmox/start-target", json=payload)
            self.assertEqual(res_start.status_code, 200)
