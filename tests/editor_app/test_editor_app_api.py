# tests/editor_app/test_editor_app_api.py

import json
import unittest
from unittest.mock import patch

from editor_app.app import create_app


class TestEditorAppAPI(unittest.TestCase):
    """Tests the editor application API endpoints."""

    def setUp(self):
        # Configure app in test mode
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    @patch("editor_app.app.AIGenerator.generate_component_data")
    def test_ai_generate_endpoint_success(self, mock_generate):
        """Tests successful component generation via AI route."""
        mock_generate.return_value = {
            "metadata": {
                "name": "Caddy",
                "image_name": "caddy",
                "description": "web server",
                "group": "reverse_proxy",
                "has_ui": False,
                "has_configuration": True,
            },
            "docker_compose": "services:",
            "variables": [],
        }

        payload = {
            "repo_url": "https://github.com/caddyserver/caddy",
            "custom_instructions": "none",
            "api_key": "dummy_key",
        }

        response = self.client.post(
            "/api/ai/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "success")
        self.assertEqual(res_data["data"]["metadata"]["name"], "Caddy")

        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        repo_url, instructions, groups, *_ = list(args) + [None]
        self.assertEqual(repo_url, "https://github.com/caddyserver/caddy")
        self.assertEqual(instructions, "none")
        self.assertIsInstance(groups, list)

    def test_ai_generate_endpoint_missing_url(self):
        """Tests that missing repo_url returns a bad request error."""
        payload = {"custom_instructions": "none", "api_key": "dummy_key"}

        response = self.client.post(
            "/api/ai/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("builtins.open")
    @patch("editor_app.app.AIGenerator.generate_component_data")
    def test_ai_generate_endpoint_save_key(self, mock_generate, mock_open):
        """Tests that api_key is saved to .env file when save_key is True."""
        mock_generate.return_value = {
            "metadata": {
                "name": "Caddy",
                "image_name": "caddy",
                "description": "web server",
                "group": "reverse_proxy",
                "has_ui": False,
                "has_configuration": True,
            },
            "docker_compose": "services:",
            "variables": [],
        }

        payload = {
            "repo_url": "https://github.com/caddyserver/caddy",
            "custom_instructions": "none",
            "api_key": "new_test_gemini_key",
            "save_key": True,
        }

        import pathlib
        import unittest.mock
        from unittest.mock import patch

        with patch.dict("os.environ", {}):
            with patch.object(pathlib.Path, "exists", return_value=False):
                response = self.client.post(
                    "/api/ai/generate",
                    data=json.dumps(payload),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertTrue(res_data["key_saved"])
        mock_open.assert_called_with(unittest.mock.ANY, "w", encoding="utf-8")

    @patch("builtins.open")
    @patch("editor_app.app.AIGenerator.generate_component_data")
    def test_ai_generate_endpoint_save_key_failure(self, mock_generate, mock_open):
        """Tests that api_key is NOT saved to .env file when generation fails."""
        mock_generate.side_effect = ValueError("Gemini API key is not configured.")

        payload = {
            "repo_url": "https://github.com/caddyserver/caddy",
            "custom_instructions": "none",
            "api_key": "invalid_gemini_key",
            "save_key": True,
        }

        import pathlib

        with patch.dict("os.environ", {}):
            with patch.object(pathlib.Path, "exists", return_value=False):
                response = self.client.post(
                    "/api/ai/generate",
                    data=json.dumps(payload),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 400)
        mock_open.assert_not_called()

    @patch("editor_app.app.ComponentManager.create_component")
    @patch("editor_app.app.ComponentManager.update_component_metadata")
    @patch("editor_app.app.ComponentManager.update_component_template_content")
    @patch("editor_app.app.ComponentManager.update_component_variables")
    @patch("editor_app.app.ComponentManager.load_metadata")
    @patch("editor_app.app.ComponentManager.save_metadata")
    def test_save_ai_component_success(
        self,
        _mock_save_meta,
        mock_load_meta,
        _mock_update_vars,
        _mock_update_template,
        mock_update_meta,
        mock_create,
    ):
        """Tests successful save of AI generated component."""
        mock_load_meta.return_value = {
            "_njorddeploy": {"components_order": []},
            "components": {},
        }

        payload = {
            "id": "caddy",
            "metadata": {
                "name": "Caddy",
                "image_name": "caddy",
                "description": "web server",
                "group": "reverse_proxy",
                "has_ui": False,
                "has_configuration": True,
            },
            "docker_compose": "services:",
            "variables": [],
            "config_templates": {"Caddyfile": "caddy/Caddyfile"},
        }

        # Mock the built-in open for writing config templates
        from unittest.mock import mock_open

        with patch("builtins.open", mock_open()):
            response = self.client.post(
                "/api/components/ai",
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "created")
        expected_metadata = payload["metadata"].copy()
        expected_metadata["config_templates"] = {"Caddyfile": "caddy/Caddyfile"}
        mock_update_meta.assert_called_once_with("caddy", expected_metadata)

    @patch("managers.sync_manager.SyncManager.fetch_from_remote")
    @patch("managers.sync_manager.SyncManager.get_sync_status")
    def test_sync_check_updates_route(self, mock_get_status, mock_fetch):
        """Tests /api/sync/check-updates endpoint."""
        mock_fetch.return_value = True
        mock_get_status.return_value = {
            "remote_fetched": True,
            "is_offline": False,
            "remote_updates_available": 2,
            "components": {},
        }

        response = self.client.get("/api/sync/check-updates")
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertIn("remote_updates_available", res_data)
        self.assertEqual(res_data["remote_updates_available"], 2)
        mock_fetch.assert_called_once_with(timeout=3)

    @patch("managers.component_manager.ComponentManager.mark_component_tested")
    def test_mark_component_tested_route(self, mock_mark):
        """Tests /api/components/<comp_id>/mark-tested endpoint."""
        response = self.client.post(
            "/api/components/pi-hole/mark-tested",
            data=json.dumps({"test_status": "stable"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "success")
        mock_mark.assert_called_once_with("pi-hole", test_status="stable")

    @patch("managers.component_manager.ComponentManager.get_component_configs")
    def test_get_component_configs_endpoint(self, mock_get_configs):
        """Tests GET /api/components/<comp_id>/configs endpoint."""
        mock_get_configs.return_value = {"config.yaml": "model_list: []\n"}
        response = self.client.get("/api/components/litellm/configs")
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["configs"], {"config.yaml": "model_list: []\n"})
        mock_get_configs.assert_called_once_with("litellm")

    @patch("managers.component_manager.ComponentManager.save_component_config")
    def test_save_component_config_endpoint(self, mock_save_config):
        """Tests PUT /api/components/<comp_id>/configs/<filename> endpoint."""
        mock_save_config.return_value = True
        response = self.client.put(
            "/api/components/litellm/configs/config.yaml",
            data="model_list:\n  - model_name: gpt-4\n",
            content_type="text/plain",
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "saved")
        mock_save_config.assert_called_once_with(
            "litellm", "config.yaml", "model_list:\n  - model_name: gpt-4\n"
        )

    @patch("managers.component_manager.ComponentManager.delete_component_config")
    def test_delete_component_config_endpoint(self, mock_delete_config):
        """Tests DELETE /api/components/<comp_id>/configs/<filename> endpoint."""
        mock_delete_config.return_value = True
        response = self.client.delete("/api/components/litellm/configs/config.yaml")
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "deleted")
        mock_delete_config.assert_called_once_with("litellm", "config.yaml")

    @patch("requests.get")
    def test_ai_status_ollama_online(self, mock_get):
        """Tests /api/ai/status with online Ollama instance."""
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "llama3:latest"}, {"name": "mistral:latest"}]
        }
        mock_get.return_value = mock_resp

        payload = {"provider": "ollama", "base_url": "http://localhost:11434/v1"}
        response = self.client.post(
            "/api/ai/status",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "online")
        self.assertEqual(res_data["models"], ["llama3:latest", "mistral:latest"])
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=3)

    def test_ai_status_ollama_ssrf_rejection(self):
        """Tests /api/ai/status rejects unsafe SSRF schemes and malicious URLs."""
        payload = {"provider": "ollama", "base_url": "file:///etc/passwd"}
        response = self.client.post(
            "/api/ai/status",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "offline")
        self.assertIn("Invalid Ollama URL", res_data["details"])

    @patch("requests.get")
    def test_ai_status_ollama_connection_error(self, mock_get):
        """Tests /api/ai/status handling when Ollama connection fails."""
        mock_get.side_effect = Exception("Connection refused")
        payload = {"provider": "ollama", "base_url": "http://localhost:11434/v1"}
        response = self.client.post(
            "/api/ai/status",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "offline")
        self.assertIn("Could not connect to Ollama", res_data["details"])

    @patch("managers.component_manager.ComponentManager.save_metadata")
    @patch("managers.component_manager.ComponentManager.update_component_metadata")
    @patch("managers.component_manager.ComponentManager.update_component_variables")
    @patch(
        "managers.component_manager.ComponentManager."
        "update_component_template_content"
    )
    @patch("managers.component_manager.ComponentManager.create_component")
    @patch("managers.component_manager.ComponentManager.load_metadata")
    def test_save_ai_component_new_success(
        self,
        mock_load,
        mock_create,
        mock_update_template,
        mock_update_vars,
        mock_update_meta,
        mock_save_meta,
    ):
        """Tests saving a newly generated AI component."""
        mock_load.return_value = {"components": {}, "_njorddeploy": {}}

        payload = {
            "id": "technitium-dns",
            "metadata": {"name": "Technitium DNS Server"},
            "docker_compose": "services:\n  dns:\n    image: technitium/dns-server\n",
            "variables": [],
            "overwrite": False,
        }

        response = self.client.post(
            "/api/components/ai",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "created")
        mock_create.assert_called_once_with("technitium-dns", "Technitium DNS Server")

    @patch("managers.component_manager.ComponentManager.load_metadata")
    def test_save_ai_component_already_exists_conflict(self, mock_load):
        """Tests that saving existing component without overwrite returns 409."""
        mock_load.return_value = {
            "components": {"dnsserver": {"name": "Technitium-Loes"}}
        }

        payload = {
            "id": "dnsserver",
            "metadata": {"name": "Technitium DNS"},
            "docker_compose": "services:\n",
            "variables": [],
            "overwrite": False,
        }

        response = self.client.post(
            "/api/components/ai",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["code"], "component_exists")
        self.assertEqual(res_data["suggested_id"], "dnsserver-1")

    @patch("managers.component_manager.ComponentManager.save_metadata")
    @patch("managers.component_manager.ComponentManager.update_component_metadata")
    @patch("managers.component_manager.ComponentManager.update_component_variables")
    @patch(
        "managers.component_manager.ComponentManager."
        "update_component_template_content"
    )
    @patch("managers.component_manager.ComponentManager.load_metadata")
    def test_save_ai_component_overwrite_success(
        self,
        mock_load,
        mock_update_template,
        mock_update_vars,
        mock_update_meta,
        mock_save_meta,
    ):
        """Tests that saving existing component with overwrite=True succeeds."""
        mock_load.return_value = {
            "components": {"dnsserver": {"name": "Technitium-Loes"}},
            "_njorddeploy": {},
        }

        payload = {
            "id": "dnsserver",
            "metadata": {"name": "Technitium DNS Updated"},
            "docker_compose": "services:\n  dns:\n    image: technitium/dns-server\n",
            "variables": [],
            "overwrite": True,
        }

        response = self.client.post(
            "/api/components/ai",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        res_data = json.loads(response.data.decode("utf-8"))
        self.assertEqual(res_data["status"], "created")
        mock_update_template.assert_called_once()

    @patch("utils.ai_generator.AIGenerator.generate_component_data")
    def test_ai_generate_streaming_success(self, mock_generate):
        """Tests /api/ai/generate with stream=True yields SSE progress and result."""

        def fake_generate(
            repo_url,
            custom_instructions=None,
            existing_groups=None,
            custom_component_id=None,
            progress_callback=None,
            **kwargs,
        ):
            if progress_callback:
                progress_callback("fetch_repo", "Fetching README...")
                progress_callback("init_llm", "Connecting to Ollama...")
                progress_callback("generate", "Drafting compose...")
                progress_callback("validate", "Validating...")
            return {
                "id": "test-comp",
                "metadata": {"name": "Test Comp"},
                "docker_compose": "services:\n  test:\n    image: test:latest\n",
                "variables": [],
            }

        mock_generate.side_effect = fake_generate

        payload = {
            "repo_url": "https://github.com/test/repo",
            "provider": "ollama",
            "stream": True,
        }

        response = self.client.post(
            "/api/ai/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/event-stream")
        data_text = response.data.decode("utf-8")
        self.assertIn('"type": "progress"', data_text)
        self.assertIn('"type": "result"', data_text)
        self.assertIn('"id": "test-comp"', data_text)

    @patch("utils.ai_generator.AIGenerator.generate_component_data")
    def test_ai_generate_streaming_error(self, mock_generate):
        """Tests /api/ai/generate with stream=True handles errors via SSE."""
        mock_generate.side_effect = RuntimeError("Ollama connection timed out.")

        payload = {
            "repo_url": "https://github.com/test/repo",
            "provider": "ollama",
            "stream": True,
        }

        response = self.client.post(
            "/api/ai/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/event-stream")
        data_text = response.data.decode("utf-8")
        self.assertIn('"type": "error"', data_text)
        self.assertIn("Ollama connection timed out", data_text)
