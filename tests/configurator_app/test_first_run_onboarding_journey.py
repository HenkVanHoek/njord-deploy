# tests/configurator_app/test_first_run_onboarding_journey.py
"""End-to-End Simulation of the First-Run User Journey.

Simulates a brand new user launching NjordDeploy on a clean system without
a .env file, inspecting the unconfigured state, testing Proxmox credentials,
saving them via the Connection Manager, and dynamically retrieving VM templates.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from configurator_app.app import create_app


class TestFirstRunOnboardingJourney(unittest.TestCase):
    """Verifies the complete first-run onboarding lifecycle for clean installs."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.env_file = self.tmp_path / ".env"

        # Start clean: clear Proxmox environment variables
        self.clean_env = {
            "PROXMOX_HOST": "",
            "PROXMOX_USER": "",
            "PROXMOX_TOKEN_ID": "",
            "PROXMOX_TOKEN_SECRET": "",
            "PROXMOX_NODE": "",
            "NJORD_DATA_DIR": str(self.tmp_path / "data"),
        }

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_complete_clean_user_journey(self):
        """Simulates full step-by-step user onboarding flow."""
        with (
            patch.dict(os.environ, self.clean_env),
            patch(
                "configurator_app.app.Path",
                side_effect=lambda *args: (
                    self.env_file if ".env" in str(args) else Path(*args)
                ),
            ),
        ):
            app = create_app()
            app.config["TESTING"] = True
            client = app.test_client()

            # 1. User loads the homepage
            res_home = client.get("/")
            self.assertEqual(res_home.status_code, 200)
            home_html = res_home.get_data(as_text=True)
            self.assertIn("proxmoxConfigModal", home_html)
            self.assertIn("nav-proxmox-status-badge", home_html)
            self.assertIn("proxmox-unconfigured-alert", home_html)

            # 2. Frontend polls initial status
            res_status = client.get("/api/config/proxmox/status")
            self.assertEqual(res_status.status_code, 200)
            status_data = res_status.get_json()
            self.assertFalse(status_data["configured"])
            self.assertFalse(status_data["has_token_secret"])
            self.assertTrue(status_data["public_key"].startswith("ssh-ed25519 "))

            # 3. Wizard loads templates in unconfigured state -> Graceful 200
            res_templates_initial = client.post("/api/proxmox/list-templates")
            self.assertEqual(res_templates_initial.status_code, 200)
            tmpl_data = res_templates_initial.get_json()
            self.assertFalse(tmpl_data["configured"])
            self.assertEqual(tmpl_data["templates"], [])
            self.assertIn("Proxmox is nog niet geconfigureerd", tmpl_data["message"])

            # 4. User opens Connection Manager and tests with missing token
            res_test_empty = client.post(
                "/api/config/proxmox/test",
                json={
                    "host": "https://192.168.1.100:8006",
                    "user": "root@pam",
                    "token_id": "",
                    "token_secret": "",
                },
            )
            self.assertEqual(res_test_empty.status_code, 400)
            self.assertFalse(res_test_empty.get_json()["success"])

            # 5. User enters valid credentials and tests connection
            with patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class:
                mock_client = mock_pve_class.return_value
                mock_client.get_version.return_value = {
                    "data": {"version": "9.2.21", "release": "9.2"}
                }
                res_test_valid = client.post(
                    "/api/config/proxmox/test",
                    json={
                        "host": "https://192.168.1.100:8006",
                        "user": "root@pam",
                        "token_id": "root@pam!token",
                        "token_secret": "test-secret-uuid",
                        "node": "pve",
                    },
                )
                self.assertEqual(res_test_valid.status_code, 200)
                valid_data = res_test_valid.get_json()
                self.assertTrue(valid_data["success"])
                self.assertEqual(valid_data["pve_version"], "9.2.21")

            # 6. User saves configuration
            with patch("builtins.open", unittest.mock.mock_open(read_data="")):
                res_save = client.post(
                    "/api/config/proxmox/save",
                    json={
                        "host": "https://192.168.1.100:8006",
                        "user": "root@pam",
                        "token_id": "root@pam!token",
                        "token_secret": "test-secret-uuid",
                        "node": "pve",
                    },
                )
                self.assertEqual(res_save.status_code, 200)
                self.assertTrue(res_save.get_json()["success"])

            # 7. Frontend verifies status is now configured
            with (
                patch.dict(
                    os.environ,
                    {
                        "PROXMOX_HOST": "https://192.168.1.100:8006",
                        "PROXMOX_TOKEN_ID": "root@pam!token",
                        "PROXMOX_TOKEN_SECRET": "test-secret-uuid",
                        "PROXMOX_NODE": "pve",
                    },
                ),
                patch("utils.proxmox_client.ProxmoxClient") as mock_pve_class,
            ):
                mock_client = mock_pve_class.return_value
                mock_client.get.return_value = {
                    "data": [
                        {"vmid": 1000, "name": "debian-clean", "template": 1},
                        {"vmid": 1001, "name": "ubuntu-clean", "template": 1},
                    ]
                }

                res_status_configured = client.get(
                    "/api/config/proxmox/status?check=true"
                )
                self.assertEqual(res_status_configured.status_code, 200)
                conf_data = res_status_configured.get_json()
                self.assertTrue(conf_data["configured"])
                self.assertTrue(conf_data["has_token_secret"])
                self.assertTrue(conf_data["connection_healthy"])

                # 8. Template list is now dynamically populated
                res_templates_ready = client.post("/api/proxmox/list-templates")
                self.assertEqual(res_templates_ready.status_code, 200)
                ready_data = res_templates_ready.get_json()
                self.assertEqual(len(ready_data["templates"]), 2)
                self.assertEqual(ready_data["templates"][0]["name"], "debian-clean")
