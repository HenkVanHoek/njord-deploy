# tests/test_ai_generator.py

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from utils.ai_generator import AIGenerator, suggest_unique_component_id
from utils.ai_generator_engine import AIGeneratorEngine


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

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_custom_component_id(self, mock_generate):
        """Tests that explicit custom_component_id is respected."""
        mock_generate.return_value = (
            '{"metadata": {"name": "Technitium DNS", "image_name": '
            '"technitium/dns-server", "description": "DNS server", '
            '"group": "networking", "has_ui": true, "ui_port_variable": "DNS_PORT"}, '
            '"docker_compose": "services:\\n  dns:\\n    image: '
            'technitium/dns-server\\n    ports:\\n      - \\"{{ DNS_PORT }}:5380\\"", '
            '"variables": [{"id": "DNS_PORT", "label": "Port", '
            '"type": "port", "default": "5380", "description": "Web port"}]}'
        )

        repo_url = "https://github.com/TechnitiumSoftware/DnsServer"
        result = self.generator.generate_component_data(
            repo_url, custom_component_id="technitium-dns"
        )

        self.assertEqual(result["id"], "technitium-dns")
        self.assertEqual(result["metadata"]["name"], "Technitium DNS")

    def test_suggest_unique_component_id(self):
        """Tests calculating unique non-conflicting component IDs."""
        existing = ["caddy", "technitium-dns", "technitium-dns-1", "grafana"]

        # If not taken, returns base
        self.assertEqual(suggest_unique_component_id("nginx", existing), "nginx")

        # If taken, appends -1
        self.assertEqual(suggest_unique_component_id("caddy", existing), "caddy-1")

        # If -1 is also taken, increments to -2
        self.assertEqual(
            suggest_unique_component_id("technitium-dns", existing),
            "technitium-dns-2",
        )

        # Handles uppercase and special characters cleanly
        self.assertEqual(
            suggest_unique_component_id("Grafana Server!", existing),
            "grafana-server",
        )

    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_data_with_existing_ids_attaches_duplicate_info(
        self, mock_generate
    ):
        """Tests that passing existing_component_ids sets is_duplicate
        and suggested_id.
        """
        mock_generate.return_value = (
            '{"metadata": {"name": "Caddy", "image_name": "caddy", '
            '"description": "web server", "group": "reverse_proxy"}, '
            '"docker_compose": "services:\\n  caddy:\\n    image: caddy\\n", '
            '"variables": []}'
        )

        repo_url = "https://github.com/caddyserver/caddy"
        result = self.generator.generate_component_data(
            repo_url, existing_component_ids=["caddy", "caddy-1"]
        )

        self.assertEqual(result["id"], "caddy")
        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["suggested_id"], "caddy-2")

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
            import urllib.parse

            mock_res = MagicMock()
            parsed = urllib.parse.urlsplit(url)
            if parsed.netloc == "ghcr.io" or parsed.netloc.endswith(".ghcr.io"):
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

    @patch("requests.get")
    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_gitlab_success(self, mock_generate, mock_get):
        """Tests successful generation for GitLab repository with nested namespace."""
        mock_get.return_value.status_code = 404
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

    @patch("requests.get")
    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_codeberg_success(self, mock_generate, mock_get):
        """Tests successful generation for Codeberg/Forgejo repository."""
        mock_get.return_value.status_code = 404
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

    def test_run_security_checks_with_complex_jinja_urls(self):
        """Test that URLs with multiple Jinja variables parse cleanly without errors."""
        test_data = {
            "metadata": {
                "name": "LiteLLM",
                "image_name": "ghcr.io/berriai/litellm",
                "has_ui": True,
                "ui_port_variable": "LITELLM_PORT",
            },
            "docker_compose": (
                "services:\n"
                "  litellm:\n"
                "    image: ghcr.io/berriai/litellm:main-latest\n"
                "    ports:\n"
                '      - "{{ LITELLM_PORT }}:4000"\n'
                "    environment:\n"
                '      - DATABASE_URL="postgresql://{{ POSTGRES_USER }}:'
                "{{ POSTGRES_PASSWORD }}@njorddeploy-litellm-db:5432/"
                '{{ POSTGRES_DB }}"\n'
                '      - STORE_MODEL_IN_DB="True"\n'
            ),
            "variables": [
                {"id": "LITELLM_PORT", "type": "port", "default": "4000"},
                {"id": "POSTGRES_USER", "type": "text", "default": "litellm_user"},
                {
                    "id": "POSTGRES_PASSWORD",
                    "type": "password",
                    "default": "very_secure_db_pass_123",
                },
                {"id": "POSTGRES_DB", "type": "text", "default": "litellm_db"},
            ],
        }

        warnings = self.generator._run_security_checks(test_data)
        # Should have zero parsing warnings
        parse_warnings = [w for w in warnings if "Failed to parse Docker Compose" in w]
        self.assertEqual(parse_warnings, [])


class TestAIGeneratorEngine(unittest.TestCase):
    """Tests for the multi-provider AIGeneratorEngine."""

    @patch("requests.post")
    def test_generate_anthropic_success(self, mock_post):
        """Test Anthropic generation using /v1/messages protocol."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": '{"result": "anthropic_ok"}'}]
        }
        mock_post.return_value = mock_response

        engine = AIGeneratorEngine(provider="anthropic", api_key="sk-ant-test")
        res = engine.generate(
            prompt="Hello Claude", system_context="You are an assistant"
        )

        self.assertEqual(res, '{"result": "anthropic_ok"}')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        call_url, *_ = args
        self.assertEqual(call_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(kwargs["headers"]["x-api-key"], "sk-ant-test")
        self.assertEqual(kwargs["json"]["system"], "You are an assistant")
        self.assertEqual(
            kwargs["json"]["messages"], [{"role": "user", "content": "Hello Claude"}]
        )

    @patch("utils.ai_generator_engine.OpenAI", None)
    @patch("requests.post")
    def test_generate_openai_compatible_requests_fallback(self, mock_post):
        """Test OpenAI-compatible endpoint with requests fallback."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"result": "openai_ok"}'}}]
        }
        mock_post.return_value = mock_response

        engine = AIGeneratorEngine(provider="openai", api_key="sk-test-openai")
        res = engine.generate(
            prompt=[{"role": "user", "content": "Hi"}],
            system_context="Sys context",
        )

        self.assertEqual(res, '{"result": "openai_ok"}')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        call_url, *_ = args
        self.assertEqual(call_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-test-openai")

    def test_generate_missing_api_key_raises(self):
        """Test that missing API key for cloud provider raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            engine = AIGeneratorEngine(provider="anthropic", api_key=None)
            with self.assertRaises(ValueError):
                engine.generate(prompt="Hello")

    def test_run_security_checks_detects_malformed_sqlite_and_missing_forge(self):
        """Verify _run_security_checks flags malformed SQLite and missing forge."""
        generator = AIGenerator(api_key="test_api_key")
        test_data = {
            "metadata": {
                "name": "Woodpecker and Noco",
                "image_name": "woodpecker/woodpecker-server",
                "has_ui": False,
            },
            "docker_compose": (
                "services:\n"
                "  woodpecker-server:\n"
                "    image: woodpecker/woodpecker-server:latest\n"
                "    environment:\n"
                "      - NC_DB=sqlite3:///usr/app/data/noco.db\n"
            ),
            "variables": [],
        }

        warnings = generator._run_security_checks(test_data)
        self.assertTrue(any("malformed SQLite URI" in w for w in warnings))
        self.assertTrue(any("missing forge configuration" in w for w in warnings))

    def test_run_security_checks_detects_missing_laravel_app_key(self):
        """Verify _run_security_checks flags Laravel apps without APP_KEY."""
        generator = AIGenerator(api_key="test_api_key")
        test_data_missing = {
            "metadata": {
                "name": "BookStack",
                "image_name": "lscr.io/linuxserver/bookstack",
                "has_ui": False,
            },
            "docker_compose": (
                "services:\n"
                "  bookstack:\n"
                "    image: lscr.io/linuxserver/bookstack:latest\n"
                "    environment:\n"
                "      - APP_URL=http://localhost:8115\n"
            ),
            "variables": [],
        }

        warnings = generator._run_security_checks(test_data_missing)
        warning_target = "missing mandatory environment variable 'APP_KEY'"
        self.assertTrue(any(warning_target in w for w in warnings))

        test_data_ok = {
            "metadata": {
                "name": "BookStack",
                "image_name": "lscr.io/linuxserver/bookstack",
                "has_ui": False,
            },
            "docker_compose": (
                "services:\n"
                "  bookstack:\n"
                "    image: lscr.io/linuxserver/bookstack:latest\n"
                "    environment:\n"
                '      - "APP_KEY=base64:J8e0Kz+z56fG0B/1Y76LqQ+2n9NqK48x/'
                '5H9mH7vV4A="\n'
            ),
            "variables": [],
        }

        warnings_ok = generator._run_security_checks(test_data_ok)
        self.assertFalse(any(warning_target in w for w in warnings_ok))

    def test_run_security_checks_detects_missing_duplicati_key(self):
        """Verify _run_security_checks flags Duplicati without encryption key."""
        generator = AIGenerator(api_key="test_api_key")
        test_data_missing = {
            "metadata": {
                "name": "Duplicati",
                "image_name": "lscr.io/linuxserver/duplicati",
                "has_ui": False,
            },
            "docker_compose": (
                "services:\n"
                "  duplicati:\n"
                "    image: lscr.io/linuxserver/duplicati:latest\n"
                "    environment:\n"
                "      - PUID=1000\n"
            ),
            "variables": [],
        }

        warnings = generator._run_security_checks(test_data_missing)
        dup_target = "missing mandatory environment variable 'SETTINGS_ENCRYPTION_KEY'"
        self.assertTrue(any(dup_target in w for w in warnings))

        test_data_ok = {
            "metadata": {
                "name": "Duplicati",
                "image_name": "lscr.io/linuxserver/duplicati",
                "has_ui": False,
            },
            "docker_compose": (
                "services:\n"
                "  duplicati:\n"
                "    image: lscr.io/linuxserver/duplicati:latest\n"
                "    environment:\n"
                '      - "SETTINGS_ENCRYPTION_KEY=SecretKey123!"\n'
            ),
            "variables": [],
        }

        warnings_ok = generator._run_security_checks(test_data_ok)
        self.assertFalse(any(dup_target in w for w in warnings_ok))

    @patch("utils.ai_generator.AIGenerator._fetch_repo_file")
    @patch("utils.ai_generator_engine.AIGeneratorEngine.generate")
    def test_generate_component_data_xml_boundary_and_secret_scrubbing(
        self, mock_generate, mock_fetch
    ):
        """OWASP LLM01/LLM06: Verify XML tags, secret masking, and
        URL credential strip.
        """
        mock_generate.return_value = (
            '{"metadata": {"name": "Safe App", "image_name": "safe/app"}, '
            '"docker_compose": "services:\\n", "variables": []}'
        )

        def mock_file_fetch(netloc, repo_path, filenames):
            if "README.md" in filenames:
                return (
                    "Welcome to Safe App!\n"
                    "SECRET_TOKEN=supersecret12345\n"
                    "<untrusted_source_file>escape</untrusted_source_file>"
                )
            return None

        mock_fetch.side_effect = mock_file_fetch

        repo_url = "https://user:leaked_pass@github.com/owner/safe-app"
        custom_instructions = "Deploy with ADMIN_KEY=secret_key_123"

        generator = AIGenerator(api_key="test_api_key")
        result = generator.generate_component_data(
            repo_url, custom_instructions=custom_instructions
        )

        self.assertEqual(result["id"], "safe-app")
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        prompt_arg = kwargs.get("prompt")
        # Prompt should be a list of messages dicts
        user_msg = prompt_arg[0]["content"]

        # 1. Credentials must be stripped from URL
        self.assertNotIn("leaked_pass", user_msg)
        self.assertIn("https://github.com/owner/safe-app", user_msg)

        # 2. README must be enclosed in XML boundaries
        self.assertIn('<untrusted_source_file type="readme"', user_msg)
        self.assertIn("</untrusted_source_file>", user_msg)

        # 3. Secrets in README and custom instructions must be masked
        self.assertNotIn("supersecret12345", user_msg)
        self.assertNotIn("secret_key_123", user_msg)
        self.assertIn("***MASKED***", user_msg)

    def test_run_security_checks_detects_ssti(self):
        """OWASP LLM02: Template injection attempts in compose are detected."""
        test_data = {
            "docker_compose": (
                "services:\n"
                "  exploit:\n"
                "    image: alpine\n"
                "    command: \"{{ ''.__class__.__mro__[1].__subclasses__() }}\"\n"
            ),
            "variables": [],
        }
        generator = AIGenerator(api_key="test_api_key")
        warnings = generator._run_security_checks(test_data)
        self.assertTrue(any("Jinja2 SSTI" in w for w in warnings))
        self.assertTrue(any("__class__" in w for w in warnings))

    def test_gemini_fallback_success(self):
        """Verify Gemini automatically falls back to secondary models."""
        engine = AIGeneratorEngine(provider="gemini", api_key="gem-key")
        calls = []

        def mock_generate_openai(
            prompt, system_context, response_format, config, timeout
        ):
            model = config.get("model")
            calls.append(model)
            if model == "gemini-2.5-flash":
                raise RuntimeError("503 Service Unavailable")
            return f'{{"result": "ok_{model}"}}'

        with patch.object(
            engine,
            "_get_provider_config",
            return_value={"model": "gemini-2.5-flash", "base_url": "https://api"},
        ):
            with patch.object(
                engine,
                "_generate_openai_compatible",
                side_effect=mock_generate_openai,
            ):
                res = engine.generate("Hello")
                self.assertIn("ok_gemini-3.8-flash", res)
                self.assertIn("gemini-3.8-flash", calls)

    def test_gemini_sovereign_failover_hostyourai(self):
        """Verify Sovereign failover to HostYourAI when Gemini is unreachable."""
        engine = AIGeneratorEngine(provider="gemini", api_key="gem-key")

        with patch.dict(os.environ, {"HOSTYOURAI_API_KEY": "hy-secret"}):
            with patch.object(
                engine,
                "_generate_openai_compatible",
                side_effect=[
                    RuntimeError("Gemini down"),
                    RuntimeError("fb1 down"),
                    RuntimeError("fb2 down"),
                    RuntimeError("fb3 down"),
                    RuntimeError("fb4 down"),
                    '{"result": "hostyourai_ok"}',
                ],
            ):
                with patch.object(
                    engine,
                    "_get_provider_config",
                    return_value={"model": "gemini-2.5-flash"},
                ):
                    res = engine.generate("Hello Sovereign")
                    self.assertEqual(res, '{"result": "hostyourai_ok"}')

    def test_gemini_emergency_wol_and_signal(self):
        """Verify emergency WOL packet and Signal alert on total cloud failure."""
        engine = AIGeneratorEngine(provider="gemini", api_key="gem-key")
        failover_cb = MagicMock()

        env_vars = {
            "WOL_LOCAL_AI_MAC": "AA:BB:CC:DD:EE:FF",
            "SIGNAL_RECIPIENT": "+31612345678",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            with patch.object(
                engine,
                "_generate_openai_compatible",
                side_effect=RuntimeError("Total network blackout"),
            ):
                with patch.object(
                    engine,
                    "_get_provider_config",
                    return_value={"model": "gemini-2.5-flash"},
                ):
                    with patch("utils.wake_on_lan.send_wake_on_lan") as mock_wol:
                        with patch(
                            "utils.fums_notifier.FUMSNotifier.send_signal"
                        ) as mock_signal:
                            with self.assertRaises(RuntimeError):
                                engine.generate("Hello", failover_callback=failover_cb)

                            failover_cb.assert_called_once()
                            mock_wol.assert_called_once_with(
                                "AA:BB:CC:DD:EE:FF",
                                broadcast_ip="255.255.255.255",
                            )
                            mock_signal.assert_called_once()

    @patch("requests.post")
    def test_anthropic_system_messages_and_empty_content(self, mock_post):
        """Verify Anthropic message format extraction and empty response handling."""
        engine = AIGeneratorEngine(provider="anthropic", api_key="sk-ant")

        # 1. System messages in prompt list
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "content": [{"type": "text", "text": "Anthropic reply"}]
        }
        mock_post.return_value = mock_resp

        prompt_msgs = [
            {"role": "system", "content": "Extra system context"},
            {"role": "user", "content": "User question"},
        ]
        res = engine._generate_anthropic(
            prompt=prompt_msgs,
            system_context="Base system context",
            config={
                "api_key": "sk-ant",
                "model": "claude-3-opus",
                "base_url": "https://api.anthropic.com/v1",
            },
        )
        self.assertEqual(res, "Anthropic reply")

        # 2. Empty content list or non-dict first block
        mock_resp.json.return_value = {"content": []}
        empty_res = engine._generate_anthropic(
            prompt="Hi",
            config={
                "api_key": "sk-ant",
                "model": "claude",
                "base_url": "https://api",
            },
        )
        self.assertEqual(empty_res, "")

        mock_resp.json.return_value = {"content": ["not_a_dict"]}
        empty_res2 = engine._generate_anthropic(
            prompt="Hi",
            config={
                "api_key": "sk-ant",
                "model": "claude",
                "base_url": "https://api",
            },
        )
        self.assertEqual(empty_res2, "")

    def test_openai_client_chat_completions(self):
        """Verify OpenAI SDK interaction and response extraction."""
        engine = AIGeneratorEngine(provider="openai", api_key="sk-test")
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "sdk_content"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("utils.ai_generator_engine.OpenAI", return_value=mock_client):
            res = engine._generate_openai_compatible(
                prompt="Hello SDK",
                config={
                    "model": "gpt-4o",
                    "api_key": "sk-test",
                    "base_url": "https://api.openai.com/v1",
                },
            )
            self.assertEqual(res, "sdk_content")

            # Empty choices returns empty string
            mock_response.choices = []
            empty_res = engine._generate_openai_compatible(
                prompt="Hello SDK",
                config={
                    "model": "gpt-4o",
                    "api_key": "sk-test",
                    "base_url": "https://api.openai.com/v1",
                },
            )
            self.assertEqual(empty_res, "")

    def test_suggest_unique_component_id_edge_cases(self):
        """
        Verify suggest_unique_component_id with empty input and
        incrementing suffix.
        """
        # Empty base returns custom-component
        self.assertEqual(suggest_unique_component_id("", None), "custom-component")
        # Existing ID with numerical suffix increments
        self.assertEqual(suggest_unique_component_id("app-1", ["app-1"]), "app-2")
        self.assertEqual(
            suggest_unique_component_id("app-1", ["app-1", "app-2"]), "app-3"
        )

    @patch("requests.get")
    def test_generate_component_data_progress_and_corrections(self, mock_get):
        """Verify progress_callback, self-correction, and root privilege detection."""
        mock_get.return_value.status_code = 404
        generator = AIGenerator(api_key="test_api_key")
        progress_mock = MagicMock()

        valid_payload = json.dumps(
            {
                "id": "my-priv-app",
                "metadata": {"name": "Privileged App"},
                "docker_compose": (
                    "services:\n"
                    "  app:\n"
                    "    image: my-priv-app:latest\n"
                    "    privileged: true\n"
                    "    volumes:\n"
                    "      - STORAGE_BASE_PATH/data:/data\n"
                ),
                "config_templates": [{"name": "app.cfg", "content": "config"}],
                "variables": [],
            }
        )

        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            side_effect=["malformed_json_first_try", valid_payload],
        ):
            with patch.object(generator, "_run_security_checks", return_value=[]):
                res = generator.generate_component_data(
                    "https://github.com/org/priv-app",
                    progress_callback=progress_mock,
                )

        self.assertEqual(res["id"], "my-priv-app")
        self.assertTrue(res["metadata"]["requires_root"])
        self.assertEqual(res["metadata"]["podman_mode"], "rootful")
        self.assertIn("CONFIG_BASE_PATH/data", res["docker_compose"])
        self.assertIn("app.cfg", res["config_templates"])
        self.assertTrue(progress_mock.called)

    def test_generate_component_data_timeout_errors(self):
        """Verify custom timeout exceptions for local and cloud models."""
        generator = AIGenerator(api_key="test_api_key")

        # Local Ollama timeout message
        generator.provider = "ollama"
        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            side_effect=RuntimeError("connection timed out"),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                generator.generate_component_data("https://github.com/org/app")
            self.assertIn("local AI model took longer", str(ctx.exception))

        # Cloud API timeout message
        generator.provider = "openai"
        generator.base_url = "https://api.openai.com/v1"
        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            side_effect=RuntimeError("connection timed out"),
        ):
            with self.assertRaises(RuntimeError) as ctx2:
                generator.generate_component_data("https://github.com/org/app")
            self.assertIn("AI API request timed out", str(ctx2.exception))

    @patch("requests.get")
    def test_check_docker_and_oci_images(self, mock_get):
        """Verify Docker Hub and OCI image validation with bearer authentication."""
        generator = AIGenerator(api_key="test_api_key")
        self.assertFalse(generator._check_docker_image_exists(""))

        # Library image on Docker Hub
        mock_get.return_value.status_code = 200
        self.assertTrue(generator._check_docker_image_exists("nginx:alpine"))

        # OCI image with 401 Bearer Token flow
        resp_401 = MagicMock(status_code=401)
        resp_401.headers = {
            "Www-Authenticate": 'Bearer realm="https://ghcr.io/token",service="ghcr.io"'
        }
        resp_token = MagicMock(status_code=200)
        resp_token.json.return_value = {"token": "ghcr_test_token"}
        resp_200 = MagicMock(status_code=200)

        mock_get.side_effect = [resp_401, resp_token, resp_200]
        self.assertTrue(generator._check_oci_image("ghcr.io", "owner/repo"))

    def test_security_checks_extended_branches(self):
        """Verify detection of log-only volumes, port numbers, cap_add, and pihole."""
        generator = AIGenerator(api_key="test_api_key")
        data = {
            "metadata": {
                "name": "Pi-hole Server",
                "image_name": "pihole/pihole:latest",
                "has_ui": True,
                "first_run_info": {
                    "auth_type": "log_token",
                    # Missing log_token_regex
                },
            },
            "docker_compose": (
                "services:\n"
                "  postgres:\n"
                "    image: postgres:15\n"
                "    cap_add:\n"
                "      - SYS_ADMIN\n"
                "    ports:\n"
                '      - "5432:5432"\n'
                "    volumes:\n"
                '      - "/data/logs:/var/log"\n'
            ),
            "variables": [{"id": "DB_PASSWORD", "default": "admin"}],
        }

        warnings = generator._run_security_checks(data)
        self.assertTrue(any("only mounts log directories" in w for w in warnings))
        self.assertTrue(any("hardcoded host port" in w for w in warnings))
        self.assertTrue(any("broad capability: SYS_ADMIN" in w for w in warnings))
        self.assertTrue(any('user: "0:0"' in w for w in warnings))
        self.assertTrue(any("log_token_regex" in w for w in warnings))
        self.assertTrue(any("weak default value" in w for w in warnings))
        # Pi-hole should automatically configure /admin ui_path
        self.assertEqual(data["metadata"].get("ui_path"), "/admin")

    def test_engine_remaining_branches(self):
        """Verify remaining error handling and branches in AIGeneratorEngine."""
        engine = AIGeneratorEngine(provider="gemini", api_key="gem-key")

        # 1. fb_model == current_model & HostYourAI failover fails
        with patch.dict(os.environ, {"HOSTYOURAI_API_KEY": "hy-secret"}):
            with patch.object(
                engine,
                "_get_provider_config",
                side_effect=[
                    {"model": "gemini-3.8-flash", "base_url": "https://api"},
                    {"model": "hy-model", "base_url": "https://hy-api"},
                ],
            ):
                with patch.object(
                    engine,
                    "_generate_openai_compatible",
                    side_effect=RuntimeError("Failure"),
                ):
                    with self.assertRaises(RuntimeError):
                        engine.generate("Hello")

        # 2. failover_callback raises Exception & WOL failover raises
        engine2 = AIGeneratorEngine(provider="gemini", api_key="gem-key")
        bad_cb = MagicMock(side_effect=RuntimeError("Callback exploded"))
        with patch.dict(os.environ, {"WOL_LOCAL_AI_MAC": "AA:BB:CC:DD:EE:FF"}):
            with patch.object(
                engine2,
                "_generate_openai_compatible",
                side_effect=RuntimeError("Network down"),
            ):
                with patch(
                    "utils.wake_on_lan.send_wake_on_lan",
                    side_effect=RuntimeError("WOL socket error"),
                ):
                    with self.assertRaises(RuntimeError):
                        engine2.generate("Hello", failover_callback=bad_cb)

        # 3. _generate_anthropic default config=None, non-dict msg, sys_text
        engine_ant = AIGeneratorEngine(provider="anthropic", api_key="sk-ant")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"content": [{"type": "text", "text": "ant-ok"}]},
            )
            prompt_list = [
                "not_a_dict",
                {"role": "system", "content": "Initial sys"},
                {"role": "user", "content": "Hi"},
            ]
            res = engine_ant._generate_anthropic(prompt=prompt_list, config=None)
            self.assertEqual(res, "ant-ok")

        # 4. _generate_openai_compatible config=None & requests fallback empty
        with patch("utils.ai_generator_engine.OpenAI", None):
            with patch("requests.post") as mock_req:
                mock_req.return_value = MagicMock(
                    status_code=200, json=lambda: {"choices": []}
                )
                res_empty = engine._generate_openai_compatible(
                    prompt="Hello Prompt",
                    system_context="System Context",
                    response_format={"type": "json_object"},
                    config=None,
                )
                self.assertEqual(res_empty, "")

    def test_generator_remaining_branches(self):
        """Verify remaining error handling, security checks, and parsing."""
        generator = AIGenerator(api_key="test_key")

        # 1. Rate limit 429 error
        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            side_effect=RuntimeError("429 Too Many Requests"),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                generator.generate_component_data("https://github.com/org/app")
            self.assertIn("rate limit reached", str(ctx.exception))

        # 2. Exceeded max_attempts on JSONDecodeError
        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            return_value="not_json",
        ):
            with self.assertRaises(RuntimeError) as ctx2:
                generator.generate_component_data("https://github.com/org/app")
            self.assertIn("Received malformed response", str(ctx2.exception))

        # 2b. Ollama provider without API key and GitLab URL
        gen_ollama = AIGenerator(provider="ollama", api_key=None)
        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            return_value='{"id": "ok", "metadata": {}, "variables": []}',
        ):
            with patch.object(gen_ollama, "_run_security_checks", return_value=[]):
                with patch("requests.get", return_value=MagicMock(status_code=404)):
                    gen_res = gen_ollama.generate_component_data(
                        "https://gitlab.com/group/repo"
                    )
                    self.assertEqual(gen_res["id"], "ok")

        # 2c. Fixable warning triggers self-correction loop
        gen_fix = AIGenerator(api_key="key")
        with patch(
            "utils.ai_generator_engine.AIGeneratorEngine.generate",
            side_effect=[
                '{"id": "fix", "metadata": {}, "variables": []}',
                '{"id": "fix", "metadata": {}, "variables": []}',
            ],
        ):
            with patch.object(
                gen_fix,
                "_run_security_checks",
                side_effect=[["Service 's' has hardcoded host port '80'"], []],
            ):
                with patch("requests.get", return_value=MagicMock(status_code=404)):
                    res_fix = gen_fix.generate_component_data("https://github.com/a/b")
                    self.assertEqual(res_fix["id"], "fix")

        # 3. URL host with port & _fetch_repo_file exception
        urls = generator._get_raw_file_urls("git.local:8080", "team/app", "README.md")
        self.assertTrue(len(urls) > 0)
        with patch("requests.get", side_effect=OSError("Network error")):
            self.assertIsNone(
                generator._fetch_repo_file("github.com", "a/b", ["f.txt"])
            )

        # 4. _check_docker_image_exists exception & OCI auth failures
        with patch("requests.get", side_effect=OSError("DNS fail")):
            self.assertFalse(generator._check_docker_image_exists("nginx:alpine"))

        with patch("requests.get") as mock_g:
            mock_g.return_value = MagicMock(status_code=401, headers={})
            self.assertFalse(generator._check_oci_image("ghcr.io", "repo"))

            mock_g.return_value = MagicMock(
                status_code=401,
                headers={"Www-Authenticate": 'Bearer service="ghcr.io"'},
            )
            self.assertFalse(generator._check_oci_image("ghcr.io", "repo"))

            resp_auth = MagicMock(
                status_code=401,
                headers={"Www-Authenticate": 'Bearer realm="https://auth",service="s"'},
            )
            resp_tok = MagicMock(status_code=200, json=lambda: {})
            mock_g.side_effect = [resp_auth, resp_tok]
            self.assertFalse(generator._check_oci_image("ghcr.io", "repo"))

        # 5. Security checks branches
        bad_yaml_data = {"docker_compose": "services: [invalid yaml"}
        warns1 = generator._run_security_checks(bad_yaml_data)
        self.assertTrue(any("Failed to parse Docker Compose" in w for w in warns1))

        complex_data = {
            "docker_compose": (
                "services:\n"
                "  bad_service: not_a_dict\n"
                "  good_service:\n"
                "    image: test/app:latest\n"
                "    volumes:\n"
                "      - type: bind\n"
                "        source: /var/data\n"
                "        target: /app/data\n"
                "    environment:\n"
                "      APP_PORT: '{{ UNKNOWN_PORT }}'\n"
            ),
            "variables": [
                "not_a_dict_var",
                {
                    "id": "PORT_A",
                    "type": "port",
                    "default": "8080",
                },
            ],
            "metadata": {
                "has_ui": True,
                "ui_port_variable": "PORT_A",
                "first_run_info": "not_a_dict",
            },
        }
        warns2 = generator._run_security_checks(complex_data)
        self.assertTrue(any("UNKNOWN_PORT" in w for w in warns2))
        self.assertTrue(
            any("not referenced in the docker-compose template" in w for w in warns2)
        )
        self.assertTrue(any("Invalid 'first_run_info'" in w for w in warns2))

        wizard_data = {
            "metadata": {"first_run_info": {"auth_type": "wizard", "guidance": ""}}
        }
        warns3 = generator._run_security_checks(wizard_data)
        self.assertTrue(any("missing 'guidance'" in w for w in warns3))

    def test_ai_generator_missing_lines_coverage(self):
        generator = AIGenerator(api_key="test_api_key")

        # 1. Lines 135-137: Rules file load exception
        with patch("builtins.open", side_effect=OSError("rules missing")):
            with self.assertRaises(RuntimeError) as ctx:
                generator.generate_component_data(
                    repo_url="https://github.com/org/repo"
                )
            self.assertIn("Failed to load AI generator rules", str(ctx.exception))

        # 2. Line 176: Port in clean_netloc & Line 280: Non-list config_templates
        valid_response = json.dumps(
            {
                "id": "my-service",
                "metadata": {
                    "name": "My Service",
                    "image_name": "ghcr.io/org/repo:1.0",
                    "description": "A service",
                    "group": "tools",
                    "has_ui": False,
                    "has_configuration": False,
                    "docker_service_name": "mysvc",
                    "component_version": "1.0",
                },
                "docker_compose": "services:\n  mysvc:\n    image: test:latest\n",
                "variables": [],
                "config_templates": {"sample.conf": "param=1\n"},
            }
        )
        with (
            patch.object(generator, "_fetch_repo_file", return_value=""),
            patch(
                "utils.ai_generator_engine.AIGeneratorEngine.generate",
                return_value=valid_response,
            ),
        ):
            res = generator.generate_component_data(
                repo_url="https://github.com:8443/org/repo"
            )
            self.assertEqual(res.get("config_templates"), {"sample.conf": "param=1\n"})

        # 4. Line 366: progress_callback called during self-correction
        progress_calls = []

        def dummy_progress(step, msg):
            progress_calls.append((step, msg))

        with (
            patch.object(generator, "_fetch_repo_file", return_value=""),
            patch(
                "utils.ai_generator_engine.AIGeneratorEngine.generate",
                return_value=valid_response,
            ),
            patch.object(
                generator,
                "_run_security_checks",
                side_effect=[["Fixable warning"], []],
            ),
        ):
            generator.generate_component_data(
                repo_url="https://github.com/org/repo",
                progress_callback=dummy_progress,
            )
            self.assertTrue(any(s == "validate" for s, _ in progress_calls))

        # 5. Line 443: 400 Bad Request exception from API
        with (
            patch.object(generator, "_fetch_repo_file", return_value=""),
            patch(
                "utils.ai_generator_engine.AIGeneratorEngine.generate",
                side_effect=Exception("Error code 400: bad request sent"),
            ),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                generator.generate_component_data(
                    repo_url="https://github.com/org/repo"
                )
            self.assertIn("400 Bad Request", str(ctx.exception))

        # 6. Line 521: Unexpected exception type from API
        with (
            patch.object(generator, "_fetch_repo_file", return_value=""),
            patch(
                "utils.ai_generator_engine.AIGeneratorEngine.generate",
                side_effect=TypeError("Unexpected NoneType in generator engine"),
            ),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                generator.generate_component_data(
                    repo_url="https://github.com/org/repo"
                )
            self.assertIn("Failed to communicate with AI API", str(ctx.exception))

        # 7. Line 610: Image with registry and tag
        with patch.object(generator, "_check_oci_image", return_value=True):
            self.assertTrue(
                generator._check_docker_image_exists("ghcr.io/org/repo:v1.2.3")
            )

        # 8. Lines 667-669: OCI check response != 200/401 and exception
        with patch("requests.get", return_value=MagicMock(status_code=500)):
            self.assertFalse(generator._check_oci_image("ghcr.io", "repo"))
        with patch("requests.get", side_effect=OSError("Network down")):
            self.assertFalse(generator._check_oci_image("ghcr.io", "repo"))

        # 9. Line 731: pull_policy inside build block
        build_pull_policy_data = {
            "metadata": {"name": "Test"},
            "docker_compose": (
                "services:\n" "  app:\n" "    build:\n" "      pull_policy: always\n"
            ),
        }
        warns_pull = generator._run_security_checks(build_pull_policy_data)
        self.assertTrue(
            any("pull_policy' nested inside the 'build' block" in w for w in warns_pull)
        )

        # 10. Line 972: Disallowed path variable
        disallowed_var_data = {
            "metadata": {"name": "Test"},
            "docker_compose": (
                "services:\n"
                "  app:\n"
                "    image: test:latest\n"
                "    volumes:\n"
                "      - '{{ STORAGE_BASE_PATH }}/data:/data'\n"
            ),
        }
        warns_path = generator._run_security_checks(disallowed_var_data)
        self.assertTrue(
            any(
                "invalid path variable '{{ STORAGE_BASE_PATH }}'" in w
                for w in warns_path
            )
        )
