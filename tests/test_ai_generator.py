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
