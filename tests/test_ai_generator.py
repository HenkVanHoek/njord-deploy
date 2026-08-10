# tests/test_ai_generator.py

import unittest
from unittest.mock import MagicMock, patch

from utils.ai_generator import AIGenerator


class TestAIGenerator(unittest.TestCase):
    """Tests the AIGenerator utility class under various conditions."""

    def setUp(self):
        self.generator = AIGenerator(api_key="test_api_key")

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_success(self, mock_generate):
        """Tests successful generation when API returns valid data."""
        mock_generate.return_value = (
            '{"metadata": {"name": "Caddy", "image_name": '
            '"caddy", "description": "web server", '
            '"group": "reverse_proxy", "has_ui": false, '
            '"has_configuration": true, "docker_service_name": "caddy", '
            '"component_version": "1.0"}, "docker_compose": '
            '"services:", "variables": []}'
        )

        repo_url = "https://github.com/caddyserver/caddy"
        result = self.generator.generate_component_data(repo_url)

        self.assertEqual(result["id"], "caddy")
        self.assertEqual(result["metadata"]["name"], "Caddy")
        self.assertEqual(result["docker_compose"], "services:")
        self.assertEqual(result["variables"], [])
        mock_generate.assert_called_once()

    def test_invalid_url_raises_value_error(self):
        """Tests that invalid Git URLs cause a ValueError."""
        with self.assertRaises(ValueError):
            self.generator.generate_component_data("")

        with self.assertRaises(ValueError):
            self.generator.generate_component_data("not_a_valid_url")

        with self.assertRaises(ValueError):
            self.generator.generate_component_data("https:///no-host")

        with self.assertRaises(ValueError):
            self.generator.generate_component_data("https://github.com/")

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_api_failure_raises_runtime_error(self, mock_generate):
        """Tests that HTTP errors trigger a RuntimeError."""
        mock_generate.side_effect = RuntimeError("Connection error.")

        with self.assertRaises(RuntimeError):
            self.generator.generate_component_data("https://github.com/owner/repo")

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_api_quota_exceeded_friendly_message(self, mock_generate):
        """Verify friendly error message for 429 Too Many Requests."""
        mock_generate.side_effect = RuntimeError("quota exceeded or rate limit reached")

        with self.assertRaises(RuntimeError) as context:
            self.generator.generate_component_data("https://github.com/owner/repo")

        self.assertIn("quota exceeded", str(context.exception))

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_api_service_unavailable_friendly_message(self, mock_generate):
        """Verify friendly error message for 503 Service Unavailable."""
        mock_generate.side_effect = RuntimeError(
            "temporarily unavailable or overloaded"
        )

        with self.assertRaises(RuntimeError) as context:
            self.generator.generate_component_data("https://github.com/owner/repo")

        self.assertIn("temporarily unavailable", str(context.exception))

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_ollama_connection_refused_friendly_message(self, mock_generate):
        """Verify friendly error message when Ollama server is offline."""
        mock_generate.side_effect = Exception(
            "Connection error. [Errno 111] Connection refused"
        )
        ollama_gen = AIGenerator(provider="ollama")

        with self.assertRaises(RuntimeError) as context:
            ollama_gen.generate_component_data("https://github.com/owner/repo")

        self.assertIn(
            "Could not connect to Ollama local server", str(context.exception)
        )
        self.assertIn("running locally", str(context.exception))

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_remote_connection_error_friendly_message(self, mock_generate):
        """Verify friendly error message when remote AI API connection fails."""
        mock_generate.side_effect = Exception("APIConnectionError - Connection error.")
        remote_gen = AIGenerator(
            provider="openai", base_url="https://api.openai.com/v1"
        )

        with self.assertRaises(RuntimeError) as context:
            remote_gen.generate_component_data("https://github.com/owner/repo")

        self.assertIn("Could not connect to AI API endpoint", str(context.exception))

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
                "    environment:\n"
                "      - DB_PASS={{ MYSQL_PASSWORD }}\n"
                "      - TOKEN={{ ADMIN_TOKEN }}\n"
                "      - NORMAL={{ NORMAL_VAR }}\n"
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

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_with_existing_groups(self, mock_generate):
        """Test generating component with existing_groups constraint."""
        mock_generate.return_value = (
            '{"metadata": {"name": "Caddy", "image_name": '
            '"caddy", "description": "web server", '
            '"group": "reverse_proxy", "has_ui": false, '
            '"has_configuration": true, "docker_service_name": "caddy", '
            '"component_version": "1.0"}, "docker_compose": '
            '"services:", "variables": []}'
        )

        repo_url = "https://github.com/caddyserver/caddy"
        existing_groups = ["reverse_proxy", "databases"]
        self.generator.generate_component_data(
            repo_url, existing_groups=existing_groups
        )

        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        sys_context = kwargs.get("system_context", "")

        expected_group_rule = (
            "14. In the metadata, the `group` property MUST be selected from "
            "the following list of existing groups: 'reverse_proxy', 'databases'"
        )
        self.assertIn(expected_group_rule, sys_context)

        expected_var_rule = (
            "15. For any variable object in the `variables` list, the `type` "
            "property MUST be one of: 'port' (for host port mappings)"
        )
        self.assertIn(expected_var_rule, sys_context)

    @patch("requests.get")
    def test_registry_replacement_ignores_build_context(self, mock_get):
        """Verify image registry replacement doesn't alter build context."""

        def mock_exists(url, **kwargs):
            mock_res = MagicMock()
            if "ghcr.io" in url:
                mock_res.status_code = 200
            else:
                mock_res.status_code = 404
            return mock_res

        mock_get.side_effect = mock_exists

        test_data = {
            "metadata": {"image_name": "jamiepine/voicebox"},
            "docker_compose": (
                "services:\n"
                "  voicebox:\n"
                "    build:\n"
                "      context: https://github.com/jamiepine/voicebox.git#main\n"
                '    image: "jamiepine/voicebox:latest"\n'
            ),
        }

        self.generator._run_security_checks(test_data)

        # The image in docker_compose should be updated
        self.assertIn(
            'image: "ghcr.io/jamiepine/voicebox:latest"', test_data["docker_compose"]
        )
        # The build context URL should remain completely untouched
        self.assertIn(
            "context: https://github.com/jamiepine/voicebox.git#main",
            test_data["docker_compose"],
        )

    def test_run_security_checks_detects_variable_mismatches(self):
        """Verify that _run_security_checks flags mismatched variables."""
        test_data = {
            "metadata": {"has_ui": True, "ui_port_variable": "MISMATCHED_PORT"},
            "docker_compose": (
                "services:\n"
                "  my-web:\n"
                "    ports:\n"
                '      - "{{ USED_BUT_NOT_DEFINED_PORT }}:80"\n'
            ),
            "variables": [
                {
                    "id": "DEFINED_BUT_NOT_USED_VAR",
                    "type": "text",
                    "default": "value",
                }
            ],
        }

        warnings = self.generator._run_security_checks(test_data)

        self.assertTrue(any("USED_BUT_NOT_DEFINED_PORT" in w for w in warnings))
        self.assertTrue(any("DEFINED_BUT_NOT_USED_VAR" in w for w in warnings))
        self.assertTrue(any("MISMATCHED_PORT" in w for w in warnings))

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_self_correction(self, mock_generate):
        """Verify that validation warnings trigger the self-correction loop."""
        text_1 = (
            '{"metadata": {"name": "Caddy", "image_name": '
            '"caddy", "description": "web server", '
            '"group": "reverse_proxy", "has_ui": false, '
            '"has_configuration": true, "docker_service_name": "caddy", '
            '"component_version": "1.0"}, "docker_compose": '
            '"services:", "variables": [{"id": '
            '"DEFINED_BUT_NOT_USED_VAR", "label": "L", '
            '"type": "text", "default": "D", '
            '"description": "D"}]}'
        )

        text_2 = (
            '{"metadata": {"name": "Caddy", "image_name": '
            '"caddy", "description": "web server", '
            '"group": "reverse_proxy", "has_ui": false, '
            '"has_configuration": true, "docker_service_name": "caddy", '
            '"component_version": "1.0"}, "docker_compose": '
            '"services:", "variables": []}'
        )

        mock_generate.side_effect = [text_1, text_2]

        repo_url = "https://github.com/caddyserver/caddy"
        result = self.generator.generate_component_data(repo_url)

        self.assertEqual(result["id"], "caddy")
        self.assertEqual(result["variables"], [])
        self.assertEqual(mock_generate.call_count, 2)

    def test_get_raw_file_urls_across_platforms(self):
        """Test building raw URLs for GitHub, GitLab, Codeberg, Bitbucket, etc."""
        # 1. GitHub
        gh_urls = self.generator._get_raw_file_urls(
            "github.com", "owner/repo", "README.md"
        )
        self.assertIn(
            "https://raw.githubusercontent.com/owner/repo/main/README.md", gh_urls
        )
        self.assertIn(
            "https://raw.githubusercontent.com/owner/repo/master/README.md", gh_urls
        )

        # 2. GitLab (with nested namespaces)
        gl_urls = self.generator._get_raw_file_urls(
            "gitlab.com", "group/subgroup/project", "docker-compose.yml"
        )
        self.assertIn(
            "https://gitlab.com/group/subgroup/project/-/raw/main/docker-compose.yml",
            gl_urls,
        )
        self.assertIn(
            "https://gitlab.com/group/subgroup/project/-/raw/master/docker-compose.yml",
            gl_urls,
        )

        # 3. Codeberg / Gitea / Forgejo
        cb_urls = self.generator._get_raw_file_urls(
            "codeberg.org", "forgejo/forgejo", "README.md"
        )
        self.assertIn(
            "https://codeberg.org/forgejo/forgejo/raw/branch/main/README.md", cb_urls
        )
        self.assertIn(
            "https://codeberg.org/forgejo/forgejo/raw/branch/master/README.md", cb_urls
        )

        # 4. Bitbucket
        bb_urls = self.generator._get_raw_file_urls(
            "bitbucket.org", "workspace/repo", "compose.yaml"
        )
        self.assertIn(
            "https://bitbucket.org/workspace/repo/raw/main/compose.yaml", bb_urls
        )

        # 5. Self-hosted generic Git instance
        sh_urls = self.generator._get_raw_file_urls(
            "git.example.com", "team/app", "README.md"
        )
        self.assertTrue(
            any(
                "https://git.example.com/team/app/raw/branch/main/README.md" in u
                for u in sh_urls
            )
        )
        self.assertTrue(
            any(
                "https://git.example.com/team/app/-/raw/main/README.md" in u
                for u in sh_urls
            )
        )

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_gitlab_success(self, mock_generate):
        """Tests successful generation for GitLab repository with nested namespace."""
        mock_generate.return_value = (
            '{"metadata": {"name": "My Service", "image_name": '
            '"myservice", "description": "gitlab service", '
            '"group": "tools", "has_ui": false, '
            '"has_configuration": false, "docker_service_name": "myservice", '
            '"component_version": "1.0"}, "docker_compose": '
            '"services:", "variables": []}'
        )

        repo_url = "https://gitlab.com/my-org/backend/service.git"
        result = self.generator.generate_component_data(repo_url)

        self.assertEqual(result["id"], "service")
        self.assertEqual(result["metadata"]["name"], "My Service")
        mock_generate.assert_called_once()

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_codeberg_success(self, mock_generate):
        """Tests successful generation for Codeberg/Forgejo repository."""
        mock_generate.return_value = (
            '{"metadata": {"name": "Forgejo", "image_name": '
            '"forgejo", "description": "git forge", '
            '"group": "development", "has_ui": false, '
            '"has_configuration": true, "docker_service_name": "forgejo", '
            '"component_version": "1.0"}, "docker_compose": '
            '"services:", "variables": []}'
        )

        repo_url = "https://codeberg.org/forgejo/forgejo"
        result = self.generator.generate_component_data(repo_url)

        self.assertEqual(result["id"], "forgejo")
        self.assertEqual(result["metadata"]["name"], "Forgejo")
        mock_generate.assert_called_once()

    @patch("requests.get")
    def test_fetch_repo_file_and_github_wrapper(self, mock_get):
        """Test _fetch_repo_file and backwards-compatible _fetch_github_file."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Hello World"
        mock_get.return_value = mock_response

        # Test _fetch_repo_file
        content = self.generator._fetch_repo_file(
            "github.com", "owner/repo", ["README.md"]
        )
        self.assertEqual(content, "# Hello World")

        # Test _fetch_github_file wrapper
        content_wrapper = self.generator._fetch_github_file(
            "owner", "repo", "README.md"
        )
        self.assertEqual(content_wrapper, "# Hello World")

        # Test failure fallback
        mock_404 = MagicMock()
        mock_404.status_code = 404
        mock_404.text = ""
        mock_get.return_value = mock_404

        content_none = self.generator._fetch_repo_file(
            "github.com", "owner/repo", ["nonexistent.txt"]
        )
        self.assertIsNone(content_none)
