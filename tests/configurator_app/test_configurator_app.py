# tests/configurator_app/test_configurator_app.py

import json
import unittest
from unittest.mock import patch

from src.configurator_app.app import create_app


class ConfiguratorAppTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test client and mock managers."""
        self.patcher_manager = patch("src.configurator_app.app.ComponentManager")
        self.patcher_setup = patch("src.configurator_app.app.SetupManager")
        self.patcher_scanner = patch("src.configurator_app.app.NodeScanner")
        self.patcher_deploy = patch("src.configurator_app.app.DeploymentManager")

        self.mock_manager_class = self.patcher_manager.start()
        self.mock_setup_class = self.patcher_setup.start()
        self.mock_scanner_class = self.patcher_scanner.start()
        self.mock_deploy_class = self.patcher_deploy.start()

        self.mock_manager = self.mock_manager_class.return_value
        self.mock_setup = self.mock_setup_class.return_value
        self.mock_scanner = self.mock_scanner_class.return_value
        self.mock_deploy = self.mock_deploy_class.return_value

        # Initialize App
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher_manager.stop()
        self.patcher_setup.stop()
        self.patcher_scanner.stop()
        self.patcher_deploy.stop()

    def test_get_components_api(self):
        """Test the GET /api/components endpoint."""
        self.mock_manager.get_all_components.return_value = [
            {"id": "pihole", "name": "Pi-hole"}
        ]
        response = self.client.get("/api/components")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("pihole", data)

    def test_scan_pis_success(self):
        """Test the network scanning endpoint."""
        self.mock_scanner.scan.return_value = (
            [{"ip": "192.168.1.50", "hostname": "pi"}],
            [],
            None,
            None,
        )
        response = self.client.post("/scan-pis")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data["hosts"]), 1)
        self.assertEqual(data["hosts"][0]["ip"], "192.168.1.50")

    def test_scan_pis_direct_ip(self):
        """Test scanning endpoint with direct IP targeting."""
        payload = {
            "discovery_method": "direct_ip",
            "direct_target_ip": "10.0.0.5",
        }
        response = self.client.post(
            "/scan-pis",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data["hosts"]), 1)
        self.assertEqual(data["hosts"][0]["ip"], "10.0.0.5")
        self.assertEqual(data["hosts"][0]["hostname"], "remote-tailscale-target")

    def test_scan_pis_direct_mac_success(self):
        """Test scanning endpoint with a direct MAC address that
        resolves successfully.
        """
        payload = {
            "discovery_method": "direct_ip",
            "direct_target_ip": "b8:27:eb:01:02:03",
        }
        self.mock_scanner.scan.return_value = (
            [
                {
                    "ip": "192.168.1.100",
                    "mac": "B8:27:EB:01:02:03",
                    "vendor": "Raspberry Pi Foundation",
                    "hostname": "my-pi",
                }
            ],
            [],
            None,
            None,
        )
        response = self.client.post(
            "/scan-pis",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data["hosts"]), 1)
        self.assertEqual(data["hosts"][0]["ip"], "192.168.1.100")
        self.assertEqual(data["hosts"][0]["mac"], "B8:27:EB:01:02:03")
        self.assertEqual(data["hosts"][0]["hostname"], "my-pi")

    def test_scan_pis_direct_mac_not_found(self):
        """Test scanning endpoint with a direct MAC address that
        is not found on the network.
        """
        payload = {
            "discovery_method": "direct_ip",
            "direct_target_ip": "b8:27:eb:01:02:03",
        }
        self.mock_scanner.scan.return_value = (
            [
                {
                    "ip": "192.168.1.100",
                    "mac": "B8:27:EB:99:99:99",
                    "vendor": "Raspberry Pi Foundation",
                    "hostname": "other-pi",
                }
            ],
            [],
            None,
            None,
        )
        response = self.client.post(
            "/scan-pis",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("Could not find any device with MAC address", data["error"])

    def test_deploy_configuration_success(self):
        """Test POST /deploy-configuration without conflicts."""
        payload = {
            "output_path": "/tmp/output",
            "devices": [{"ip": "192.168.1.50"}],
            "analysis_results": {"external_conflicts": {"ports": []}},
        }

        self.mock_deploy.start_deployment.return_value = None

        response = self.client.post(
            "/deploy-configuration",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data)
        self.assertIn("task_id", data)

    def test_deploy_blocks_on_critical_conflict(self):
        """Test that deployment stops if a port conflict is detected."""
        payload = {
            "output_path": "/tmp/output",
            "devices": [{"ip": "192.168.1.50"}],
            "analysis_results": {
                "external_conflicts": {
                    "ports": [
                        {
                            "port": 80,
                            "conflict_type": "DANGEROUS_NATIVE_PROCESS_CONFLICT",
                            "proposed_service": "Nginx",
                        }
                    ]
                }
            },
        }

        response = self.client.post(
            "/deploy-configuration",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Critical conflicts must be resolved first.", data["details"])
