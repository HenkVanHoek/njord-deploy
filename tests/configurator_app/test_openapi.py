# tests/configurator_app/test_openapi.py

import json
import unittest
from unittest.mock import patch

from src.configurator_app.app import create_app
from src.configurator_app.openapi import get_openapi_spec


class OpenApiTestCase(unittest.TestCase):

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

        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher_manager.stop()
        self.patcher_setup.stop()
        self.patcher_scanner.stop()
        self.patcher_deploy.stop()

    def test_get_openapi_spec_structure(self):
        """Verify that get_openapi_spec returns valid OpenAPI 3.0 elements."""
        spec = get_openapi_spec()
        self.assertEqual(spec.get("openapi"), "3.0.3")
        self.assertIn("info", spec)
        self.assertIn("title", spec["info"])
        self.assertIn("paths", spec)
        self.assertIn("/api/components", spec["paths"])
        self.assertIn("/api/v1/system/analyze", spec["paths"])
        self.assertIn("/deploy-configuration", spec["paths"])
        self.assertIn("/api/proxmox/create-lxc", spec["paths"])

    def test_api_openapi_json_endpoint(self):
        """Verify that GET /api/openapi.json returns 200 OK and valid JSON."""
        response = self.client.get("/api/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get("openapi"), "3.0.3")
        self.assertEqual(
            data.get("info", {}).get("title"), "NjordDeploy Configurator REST API"
        )

    def test_api_docs_swagger_ui_endpoint(self):
        """Verify that GET /api/docs returns 200 OK and renders Swagger UI."""
        response = self.client.get("/api/docs")
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("swagger-ui", content)
        self.assertIn("/api/openapi.json", content)
