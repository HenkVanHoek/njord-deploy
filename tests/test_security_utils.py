# tests/test_security_utils.py

import unittest

from utils.security_utils import (
    build_safe_target_url,
    is_safe_redirect_url,
    mask_passwords,
    validate_and_sanitize_url,
)


class TestSecurityUtils(unittest.TestCase):
    """Unit tests for URL validation and SSRF prevention utilities."""

    def test_validate_valid_urls(self):
        """Tests that standard http and https URLs pass validation."""
        valid_cases = [
            ("http://localhost:11434/v1", "http://localhost:11434/v1"),
            ("https://api.openai.com/v1", "https://api.openai.com/v1"),
            ("http://192.168.1.50:8080/api", "http://192.168.1.50:8080/api"),
            ("https://example.com/test?query=1", "https://example.com/test?query=1"),
            (
                "http://example.com/path#fragment",
                "http://example.com/path",
            ),  # Fragment stripped
        ]
        for raw, expected in valid_cases:
            is_valid, clean_url, err = validate_and_sanitize_url(raw)
            self.assertTrue(is_valid, f"Failed for {raw}: {err}")
            self.assertEqual(clean_url, expected)
            self.assertIsNone(err)

    def test_validate_default_fallback(self):
        """Tests that empty URL falls back to default_url if provided."""
        is_valid, clean_url, err = validate_and_sanitize_url(
            "", default_url="http://localhost:11434/v1"
        )
        self.assertTrue(is_valid)
        self.assertEqual(clean_url, "http://localhost:11434/v1")
        self.assertIsNone(err)

    def test_validate_empty_fails(self):
        """Tests that empty or None URL without default fails validation."""
        is_valid, clean_url, err = validate_and_sanitize_url(None)
        self.assertFalse(is_valid)
        self.assertIsNone(clean_url)
        self.assertIn("cannot be empty", err or "")

    def test_validate_disallowed_schemes(self):
        """Tests rejection of dangerous schemes (file, gopher, ftp, javascript)."""
        disallowed = [
            "file:///etc/passwd",
            "gopher://127.0.0.1:70",
            "ftp://ftp.example.com",
            "javascript:alert(1)",
            "data:text/plain;base64,SGVsbG8=",
        ]
        for raw in disallowed:
            is_valid, clean_url, err = validate_and_sanitize_url(raw)
            self.assertFalse(is_valid, f"Expected invalid for scheme in: {raw}")
            self.assertIsNone(clean_url)
            self.assertIn("Invalid URL scheme", err or "")

    def test_validate_control_characters_injection(self):
        """Tests rejection of URLs with CRLF or null bytes."""
        injections = [
            "http://localhost:11434/v1\r\nHost: evil.com",
            "http://localhost:11434/v1\nSet-Cookie: test=1",
            "http://localhost:11434/v1\x00/evil",
        ]
        for raw in injections:
            is_valid, clean_url, err = validate_and_sanitize_url(raw)
            self.assertFalse(is_valid, f"Expected invalid for injection in: {raw}")
            self.assertIsNone(clean_url)
            self.assertIn("illegal control characters", err or "")

    def test_validate_missing_hostname(self):
        """Tests rejection of URLs lacking a hostname."""
        is_valid, clean_url, err = validate_and_sanitize_url("http://")
        self.assertFalse(is_valid)
        self.assertIsNone(clean_url)
        self.assertIn("valid hostname", err or "")

    def test_build_safe_target_url_ollama(self):
        """Tests safe URL construction for Ollama tags endpoint."""
        cases = [
            (
                "http://localhost:11434/v1",
                "/api/tags",
                "/v1",
                "http://localhost:11434/api/tags",
            ),
            (
                "http://localhost:11434/v1/",
                "/api/tags",
                "/v1",
                "http://localhost:11434/api/tags",
            ),
            (
                "http://localhost:11434",
                "/api/tags",
                "/v1",
                "http://localhost:11434/api/tags",
            ),
            (
                "http://192.168.1.100:11434/",
                "/api/tags",
                "/v1",
                "http://192.168.1.100:11434/api/tags",
            ),
        ]
        for base, endpoint, strip, expected in cases:
            is_valid, target, err = build_safe_target_url(
                base_url=base,
                target_endpoint=endpoint,
                strip_suffix=strip,
            )
            self.assertTrue(is_valid, f"Failed for {base}: {err}")
            self.assertEqual(target, expected)
            self.assertIsNone(err)

    def test_build_safe_target_url_invalid_base(self):
        """Tests build_safe_target_url with invalid base URL."""
        is_valid, target, err = build_safe_target_url(
            base_url="file:///etc/shadow",
            target_endpoint="/api/tags",
        )
        self.assertFalse(is_valid)
        self.assertIsNone(target)
        self.assertIn("Invalid URL scheme", err or "")

    def test_mask_echo_sudo(self):
        """Tests that passwords in echo ... | sudo -S are properly masked."""
        cases = [
            (
                "echo 'SecretPass123!' | sudo -S podman ps -a",
                "echo '*******' | sudo -S podman ps -a",
            ),
            (
                'echo "SecretP@ss" | sudo -S systemctl restart docker',
                "echo '*******' | sudo -S systemctl restart docker",
            ),
            (
                "echo MyPlainSecret | sudo systemctl status",
                "echo '*******' | sudo systemctl status",
            ),
            (
                "--- Output of 'echo 'SecretPass123!' | sudo -S cat /etc/hosts' ---",
                "--- Output of 'echo '*******' | sudo -S cat /etc/hosts' ---",
            ),
        ]
        for raw, expected in cases:
            self.assertEqual(mask_passwords(raw), expected)

    def test_mask_password_params(self):
        """Tests that password attributes in JSON or configs are masked."""
        raw = '{"ansible_password": "SecretPass123!", "port": 8080}'
        expected = '{"ansible_password": "*******", "port": 8080}'
        self.assertEqual(mask_passwords(raw), expected)

    def test_mask_extra_and_env_secrets(self):
        """Tests explicit secrets and environment variables masking."""
        raw = "Connecting with SuperSecretHostKey and custom token 999xyz"
        masked = mask_passwords(
            raw,
            extra_secrets=["SuperSecretHostKey", "999xyz"],
        )
        self.assertNotIn("SuperSecretHostKey", masked)
        self.assertNotIn("999xyz", masked)
        self.assertEqual(masked, "Connecting with ******* and custom token *******")

    def test_is_safe_redirect_url(self):
        """Tests that open redirects are rejected and internal paths allowed."""
        safe_targets = [
            "/",
            "/index",
            "/services/adguard-home",
            "/setup?step=2",
            "/api/status?format=json",
        ]
        for target in safe_targets:
            self.assertTrue(
                is_safe_redirect_url(target),
                f"Expected '{target}' to be recognized as safe",
            )

        unsafe_targets = [
            None,
            "",
            "   ",
            "https://evil.com",
            "http://evil.com/phish",
            "//evil.com",
            "/\\evil.com",
            "\\\\evil.com",
            "javascript:alert(1)",
            "data:text/html,<html>alert</html>",
            "http://localhost:5000",
            "/path/with/\\backslash",
        ]
        for target in unsafe_targets:
            self.assertFalse(
                is_safe_redirect_url(target),
                f"Expected '{target}' to be rejected as unsafe",
            )
