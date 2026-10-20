# tests/test_ai_provider_manager.py

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.ai_provider_manager import (
    get_ai_timeout,
    get_provider_resolved_config,
    load_ai_providers_registry,
    save_api_key_to_env_file,
)


class TestAIProviderManager(unittest.TestCase):
    """Tests for the dynamic AI provider registry and manager."""

    def test_load_ai_providers_registry(self):
        """Verify that the AI providers registry loads successfully."""
        registry = load_ai_providers_registry()
        self.assertIn("ollama", registry)
        self.assertIn("gemini", registry)
        self.assertIn("hostyourai", registry)
        self.assertIn("openai", registry)
        self.assertIn("anthropic", registry)
        self.assertIn("deepseek", registry)
        self.assertIn("openrouter", registry)
        self.assertIn("custom", registry)

    def test_get_provider_resolved_config_defaults(self):
        """Test resolving default configuration for hostyourai provider."""
        cfg = get_provider_resolved_config("hostyourai")
        self.assertEqual(cfg["provider"], "hostyourai")
        self.assertEqual(cfg["env_var"], "HOSTYOURAI_API_KEY")
        self.assertEqual(cfg["base_url"], "https://hostyourai.com/api/v1")
        self.assertEqual(cfg["model"], "deepseek-ai/DeepSeek-V4-Flash")

    def test_get_provider_resolved_config_anthropic(self):
        """Test resolving default configuration for anthropic provider."""
        cfg = get_provider_resolved_config("anthropic")
        self.assertEqual(cfg["provider"], "anthropic")
        self.assertEqual(cfg["env_var"], "ANTHROPIC_API_KEY")
        self.assertEqual(cfg["base_url"], "https://api.anthropic.com/v1")
        self.assertEqual(cfg["model"], "claude-3-5-sonnet-20241022")

    def test_get_provider_resolved_config_overrides(self):
        """Test runtime overrides for API key, base URL, and model."""
        cfg = get_provider_resolved_config(
            provider="hostyourai",
            api_key="custom_key_123",
            base_url="https://custom.hostyourai.com/v1",
            model="custom-model",
        )
        self.assertEqual(cfg["api_key"], "custom_key_123")
        self.assertEqual(cfg["base_url"], "https://custom.hostyourai.com/v1")
        self.assertEqual(cfg["model"], "custom-model")

    def test_get_provider_resolved_config_disallows_custom_base_url(self):
        """Verify that fixed-endpoint providers ignore arbitrary base_url overrides."""
        cfg = get_provider_resolved_config(
            provider="gemini",
            base_url="https://alien-endpoint.example.com/v1",
        )
        self.assertEqual(
            cfg["base_url"],
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    def test_get_provider_resolved_config_invalid_provider(self):
        """Test that invalid provider names raise ValueError."""
        with self.assertRaises(ValueError):
            get_provider_resolved_config("invalid_provider_xyz")

    def test_save_api_key_to_env_file(self):
        """Test saving an API key to a temporary .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / ".env"
            env_file.write_text("SOME_VAR=123\nHOSTYOURAI_API_KEY=old_key\n")

            success = save_api_key_to_env_file(
                key="new_secret_key", provider="hostyourai", project_root=temp_path
            )
            self.assertTrue(success)

            content = env_file.read_text()
            self.assertIn("HOSTYOURAI_API_KEY=new_secret_key\n", content)
            self.assertIn("SOME_VAR=123\n", content)

    def test_save_api_key_anthropic(self):
        """Test saving Anthropic API key to .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / ".env"
            env_file.write_text("SOME_VAR=123\n")

            success = save_api_key_to_env_file(
                key="sk-ant-testkey123", provider="anthropic", project_root=temp_path
            )
            self.assertTrue(success)

            content = env_file.read_text()
            self.assertIn("ANTHROPIC_API_KEY=sk-ant-testkey123\n", content)

    def test_save_ollama_base_url_to_env(self):
        """Test saving Ollama custom Base URL to .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / ".env"
            env_file.write_text("SOME_VAR=123\n")

            success = save_api_key_to_env_file(
                provider="ollama",
                base_url="http://192.168.178.72:11434/v1",
                project_root=temp_path,
            )
            self.assertTrue(success)

            content = env_file.read_text()
            self.assertIn("OLLAMA_BASE_URL=http://192.168.178.72:11434/v1\n", content)

    def test_load_ai_providers_registry_injects_env_base_url(self):
        """Test that configured environment base URLs are injected into registry."""
        with patch.dict(
            os.environ, {"OLLAMA_BASE_URL": "http://192.168.178.72:11434/v1"}
        ):
            providers = load_ai_providers_registry()
            self.assertEqual(
                providers["ollama"].get("configured_base_url"),
                "http://192.168.178.72:11434/v1",
            )

    def test_get_ai_timeout_local_defaults_and_env(self):
        """Test timeout calculation for localhost and Ollama providers."""
        # Default local timeout when no env vars set
        with patch.dict(os.environ, {}, clear=True):
            timeout = get_ai_timeout("ollama")
            self.assertEqual(timeout, 300.0)

            # Custom URL on localhost or private LAN IP
            timeout_custom = get_ai_timeout(
                "custom", base_url="http://127.0.0.1:8000/v1"
            )
            self.assertEqual(timeout_custom, 300.0)

            timeout_lan = get_ai_timeout(
                "custom", base_url="http://192.168.178.72:11434/v1"
            )
            self.assertEqual(timeout_lan, 300.0)

        # AI_LOCALHOST_TIMEOUT set
        with patch.dict(os.environ, {"AI_LOCALHOST_TIMEOUT": "150.5"}):
            timeout = get_ai_timeout("ollama")
            self.assertEqual(timeout, 150.5)

        # AI_TIMEOUT fallback for local when AI_LOCALHOST_TIMEOUT is not set
        with patch.dict(os.environ, {"AI_TIMEOUT": "75.0"}):
            timeout = get_ai_timeout("ollama")
            self.assertEqual(timeout, 75.0)

    def test_get_ai_timeout_remote_defaults_and_env(self):
        """Test timeout calculation for remote providers like OpenAI / HostYourAI."""
        # Default remote timeout
        with patch.dict(os.environ, {}, clear=True):
            timeout = get_ai_timeout("openai", base_url="https://api.openai.com/v1")
            self.assertEqual(timeout, 120.0)

            timeout_anthropic = get_ai_timeout("anthropic")
            self.assertEqual(timeout_anthropic, 120.0)

        # AI_TIMEOUT set
        with patch.dict(os.environ, {"AI_TIMEOUT": "110.0"}):
            timeout = get_ai_timeout("openai")
            self.assertEqual(timeout, 110.0)

        # AI_TIME_OUT alternative naming
        with patch.dict(os.environ, {"AI_TIME_OUT": "95.0"}):
            timeout = get_ai_timeout("hostyourai")
            self.assertEqual(timeout, 95.0)

    def test_ai_provider_manager_additional_coverage(self):
        """Test float parsing, corrupt config fallback, model saving,
        and custom provider."""
        # 1. _parse_float_or_none and set_env_key_value
        from utils.ai_provider_manager import _parse_float_or_none, set_env_key_value

        self.assertIsNone(_parse_float_or_none("invalid_float"))
        self.assertIsNone(_parse_float_or_none(""))
        self.assertEqual(set_env_key_value(["A=1\n"], "A", "2"), ["A=2\n"])

        # 2. Corrupt providers JSON fallback
        with tempfile.NamedTemporaryFile("w", delete=False) as tf:
            tf.write("{ not valid json")
            corrupt_path = Path(tf.name)
        try:
            with patch(
                "utils.ai_provider_manager.get_providers_json_path",
                return_value=corrupt_path,
            ):
                reg = load_ai_providers_registry()
                self.assertIn("gemini", reg)
        finally:
            corrupt_path.unlink()

        # 3. Model saving and custom provider env vars
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            # File with trailing text without newline
            (tp / ".env").write_text("FOO=bar")

            # Save model and custom base_url
            saved = save_api_key_to_env_file(
                provider="custom",
                base_url="http://custom.ai/v1",
                model="custom-coder-v1",
                project_root=tp,
            )
            self.assertTrue(saved)
            txt = (tp / ".env").read_text()
            self.assertIn("CUSTOM_AI_BASE_URL=http://custom.ai/v1", txt)
            self.assertIn("CUSTOM_AI_MODEL=custom-coder-v1", txt)

            # Nothing to save returns False
            self.assertFalse(save_api_key_to_env_file(project_root=tp))

        # 4. Custom provider resolved config from environment
        with patch.dict(
            os.environ,
            {
                "CUSTOM_AI_BASE_URL": "http://mycustom:8000/v1",
                "HOSTYOURAI_BASE_URL": "http://hy:8000/v1",
                "OLLAMA_BASE_URL": "http://ollama:11434",
                "OLLAMA_MODEL": "llama3.2:3b",
            },
        ):
            c_cfg = get_provider_resolved_config("custom")
            self.assertEqual(c_cfg["base_url"], "http://mycustom:8000/v1")

            hy_cfg = get_provider_resolved_config("hostyourai")
            self.assertEqual(hy_cfg["base_url"], "http://hy:8000/v1")

            o_cfg = get_provider_resolved_config("ollama")
            self.assertEqual(o_cfg["base_url"], "http://ollama:11434")
            self.assertEqual(o_cfg["model"], "llama3.2:3b")

        # 5. Default project_root in save_api_key_to_env_file
        with patch.object(Path, "exists", return_value=False):
            self.assertFalse(save_api_key_to_env_file(project_root=None))
