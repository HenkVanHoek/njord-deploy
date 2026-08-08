# tests/test_ai_provider_manager.py

import tempfile
import unittest
from pathlib import Path

from utils.ai_provider_manager import (
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
        self.assertIn("deepseek", registry)
        self.assertIn("openrouter", registry)
        self.assertIn("custom", registry)

    def test_get_provider_resolved_config_defaults(self):
        """Test resolving default configuration for hostyourai provider."""
        cfg = get_provider_resolved_config("hostyourai")
        self.assertEqual(cfg["provider"], "hostyourai")
        self.assertEqual(cfg["env_var"], "HOSTYOURAI_API_KEY")
        self.assertEqual(cfg["base_url"], "https://api.hostyourai.eu/v1")
        self.assertEqual(cfg["model"], "mistral-7b-instruct")

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
