# tests/test_ai_generator.py

import unittest
from unittest.mock import MagicMock, patch

import requests

from utils.ai_generator import AIGenerator


class TestAIGenerator(unittest.TestCase):
    """Tests the AIGenerator utility class under various conditions."""

    def setUp(self):
        self.generator = AIGenerator(api_key="test_api_key")

    @patch("requests.post")
    def test_generate_component_data_success(self, mock_post):
        """Tests successful generation when API returns valid data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"metadata": {"name": "Caddy", "image_name": '
                                    '"caddy", "description": "web server", '
                                    '"group": "reverse_proxy", "has_ui": false, '
                                    '"has_configuration": true}, "docker_compose": '
                                    '"services:", "variables": []}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        repo_url = "https://github.com/caddyserver/caddy"
        result = self.generator.generate_component_data(repo_url)

        self.assertEqual(result["id"], "caddy")
        self.assertEqual(result["metadata"]["name"], "Caddy")
        self.assertEqual(result["docker_compose"], "services:")
        self.assertEqual(result["variables"], [])
        mock_post.assert_called_once()

    def test_invalid_url_raises_value_error(self):
        """Tests that invalid GitHub URLs cause a ValueError."""
        with self.assertRaises(ValueError):
            self.generator.generate_component_data("https://invalid.com/repo")

        with self.assertRaises(ValueError):
            self.generator.generate_component_data("https://github.com/")

    @patch("requests.post")
    def test_api_failure_raises_runtime_error(self, mock_post):
        """Tests that HTTP errors trigger a RuntimeError."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with self.assertRaises(RuntimeError):
            self.generator.generate_component_data("https://github.com/owner/repo")

    @patch("requests.post")
    def test_api_quota_exceeded_friendly_message(self, mock_post):
        """Verify friendly error message for 429 Too Many Requests."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Quota Exceeded", response=mock_response
        )
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.generator.generate_component_data("https://github.com/owner/repo")

        self.assertIn("quota exceeded", str(context.exception))

    @patch("requests.post")
    def test_api_service_unavailable_friendly_message(self, mock_post):
        """Verify friendly error message for 503 Service Unavailable."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Service Unavailable", response=mock_response
        )
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.generator.generate_component_data("https://github.com/owner/repo")

        self.assertIn("temporarily unavailable", str(context.exception))

    def test_run_security_checks_detects_issues(self):
        """Verify that _run_security_checks correctly flags vulnerabilities."""
        # Setup data with various security issues
        test_data = {
            "docker_compose": (
                "services:\n"
                "  my-web:\n"
                "    privileged: true\n"
                "    network_mode: host\n"
                "    cap_add:\n"
                "      - SYS_ADMIN\n"
                "    volumes:\n"
                "      - /var/run/docker.sock:/var/run/docker.sock\n"
                "      - /etc:/etc\n"
            ),
            "variables": [
                {
                    "id": "MYSQL_PASSWORD",
                    "default": "12345",
                },
                {
                    "id": "ADMIN_TOKEN",
                    "default": "admin",
                },
                {
                    "id": "NORMAL_VAR",
                    "default": "safe_value",
                },
            ],
        }

        warnings = self.generator._run_security_checks(test_data)

        # Verify warnings
        self.assertTrue(any("privileged mode" in w for w in warnings))
        self.assertTrue(any("host network mode" in w for w in warnings))
        self.assertTrue(any("Docker socket" in w for w in warnings))
        self.assertTrue(any("sensitive host system path" in w for w in warnings))
        self.assertTrue(any("broad capability" in w for w in warnings))
        self.assertTrue(any("MYSQL_PASSWORD" in w for w in warnings))
        self.assertTrue(any("ADMIN_TOKEN" in w for w in warnings))
        self.assertFalse(any("NORMAL_VAR" in w for w in warnings))

    @patch("requests.get")
    def test_check_docker_image_exists_docker_hub(self, mock_get):
        """Test checking images on Docker Hub (both library and namespaces)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 1. Official image
        res = self.generator._check_docker_image_exists("ubuntu:latest")
        self.assertTrue(res)
        mock_get.assert_called_with(
            "https://hub.docker.com/v2/repositories/library/ubuntu/", timeout=5
        )

        # 2. Namespaced image
        mock_get.reset_mock()
        res = self.generator._check_docker_image_exists("advplyr/audiobookshelf")
        self.assertTrue(res)
        mock_get.assert_called_with(
            "https://hub.docker.com/v2/repositories/advplyr/audiobookshelf/",
            timeout=5,
        )

    @patch("requests.get")
    def test_check_docker_image_exists_oci_immediate_success(self, mock_get):
        """Test checking images on custom OCI registry with immediate success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        res = self.generator._check_docker_image_exists("quay.io/keycloak/keycloak")
        self.assertTrue(res)
        mock_get.assert_called_once_with(
            "https://quay.io/v2/keycloak/keycloak/tags/list", timeout=5
        )

    @patch("requests.get")
    def test_check_docker_image_exists_oci_token_auth(self, mock_get):
        """Test checking images on custom OCI registry with token auth."""
        # First call to tags/list: 401 with Www-Authenticate header
        mock_res_401 = MagicMock()
        mock_res_401.status_code = 401
        mock_res_401.headers = {
            "Www-Authenticate": (
                'Bearer realm="https://ghcr.io/token",'
                'service="ghcr.io",scope="repository:advplyr/audiobookshelf:pull"'
            )
        }

        # Second call to get token: 200 with token in JSON
        mock_res_token = MagicMock()
        mock_res_token.status_code = 200
        mock_res_token.json.return_value = {"token": "mock_token"}

        # Third call to tags/list: 200
        mock_res_200 = MagicMock()
        mock_res_200.status_code = 200

        mock_get.side_effect = [mock_res_401, mock_res_token, mock_res_200]

        res = self.generator._check_docker_image_exists(
            "ghcr.io/advplyr/audiobookshelf"
        )
        self.assertTrue(res)

        # Verify calls
        self.assertEqual(mock_get.call_count, 3)
        call_1, call_2, call_3 = mock_get.call_args_list

        args_2, kwargs_2 = call_2
        (url_2,) = args_2
        self.assertEqual(url_2, "https://ghcr.io/token")
        self.assertEqual(kwargs_2["params"]["service"], "ghcr.io")

        args_3, kwargs_3 = call_3
        (url_3,) = args_3
        self.assertEqual(url_3, "https://ghcr.io/v2/advplyr/audiobookshelf/tags/list")
        self.assertEqual(kwargs_3["headers"]["Authorization"], "Bearer mock_token")

    @patch("requests.post")
    def test_generate_component_data_with_existing_groups(self, mock_post):
        """Test generating component with existing_groups constraint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"metadata": {"name": "Caddy", "image_name": '
                                    '"caddy", "description": "web server", '
                                    '"group": "reverse_proxy", "has_ui": false, '
                                    '"has_configuration": true}, "docker_compose": '
                                    '"services:", "variables": []}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        repo_url = "https://github.com/caddyserver/caddy"
        existing_groups = ["reverse_proxy", "databases"]
        self.generator.generate_component_data(
            repo_url, existing_groups=existing_groups
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        json_data = kwargs.get("json", {})
        (contents,) = json_data.get("contents", [])
        parts = contents.get("parts", [])
        (part,) = parts
        prompt = part.get("text", "")

        expected_group_rule = (
            "14. In the metadata, the `group` property MUST be selected from "
            "the following list of existing groups: 'reverse_proxy', 'databases'"
        )
        self.assertIn(expected_group_rule, prompt)

        expected_var_rule = (
            "15. For any variable object in the `variables` list, the `type` "
            "property MUST be one of: 'port' (for host port mappings)"
        )
        self.assertIn(expected_var_rule, prompt)
