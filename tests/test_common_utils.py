# tests/test_common_utils.py
"""Tests for Central Shared Utilities (scripts/common).

Validates Zero-Leak redaction, Signal notifications, and Vault resolution under
CMMI Level 5.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.common.notifications import (
    is_signal_configured,
    send_signal_message,
    send_signal_notification,
)
from scripts.common.redaction import (
    REDACTED_MASK,
    mask_secret_value,
    redact_sensitive_text,
    sanitize_log_output,
    strip_ansi,
)
from scripts.common.vault import get_vault_password, resolve_vault_password_file


def test_strip_ansi():
    """Verifies ANSI escape codes are stripped cleanly."""
    ansi_text = "\x1b[31mError:\x1b[0m Failed connection \x1b[1;32mOK\x1b[0m"
    assert strip_ansi(ansi_text) == "Error: Failed connection OK"
    assert strip_ansi("") == ""


def test_mask_secret_value():
    """Verifies masking logic for secret values."""
    assert mask_secret_value("my_super_secret", visible_chars=0) == REDACTED_MASK
    assert (
        mask_secret_value("ghp_1234567890abcdef", visible_chars=4)
        == f"ghp_...{REDACTED_MASK}"
    )
    assert mask_secret_value(None) == REDACTED_MASK
    assert mask_secret_value("short", visible_chars=10) == REDACTED_MASK


def test_redact_sensitive_text_credentials():
    """Verifies passwords, sudo echo, and bearer tokens are masked."""
    # Sudo echo pattern
    text_sudo = "echo 'my_secret_pass' | sudo -S systemctl restart docker"
    redacted = redact_sensitive_text(text_sudo)
    assert "my_secret_pass" not in redacted
    assert f"'{REDACTED_MASK}'" in redacted

    # Key-value pattern
    text_kv = (
        'ansible_password="SecretPass123!" api_key: "ai_token_xyz" password=testpass'
    )
    redacted_kv = redact_sensitive_text(text_kv)
    assert "SecretPass123!" not in redacted_kv
    assert "ai_token_xyz" not in redacted_kv
    assert "testpass" not in redacted_kv
    assert REDACTED_MASK in redacted_kv

    # Bearer token
    text_bearer = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted_bearer = redact_sensitive_text(text_bearer)
    assert "eyJhbGciOi" not in redacted_bearer
    assert REDACTED_MASK in redacted_bearer

    # Private key
    text_privkey = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0\n"
        "-----END RSA PRIVATE KEY-----"
    )
    redacted_key = redact_sensitive_text(text_privkey)
    assert "MIIEowIBA" not in redacted_key
    assert REDACTED_MASK in redacted_key

    # Extra secrets
    text_custom = "Host 192.168.1.100 used internal_top_secret_code for auth"
    redacted_custom = redact_sensitive_text(
        text_custom, extra_secrets=["internal_top_secret_code"]
    )
    assert "internal_top_secret_code" not in redacted_custom
    assert REDACTED_MASK in redacted_custom

    assert redact_sensitive_text("") == ""


def test_sanitize_log_output():
    """Verifies combined ANSI strip and redaction."""
    raw = "\x1b[33mWARN: ansible_password='VerySecret123!' failed\x1b[0m"
    clean = sanitize_log_output(raw)
    assert "\x1b" not in clean
    assert "VerySecret123!" not in clean
    assert REDACTED_MASK in clean


def test_is_signal_configured():
    """Verifies detection of configured Signal credentials."""
    with patch.dict(
        os.environ,
        {
            "SIGNAL_API_URL": "http://127.0.0.1:8080",
            "SIGNAL_SENDER": "+31612345678",
            "SIGNAL_RECIPIENT": "+31687654321",
        },
        clear=True,
    ):
        assert is_signal_configured() is True

    with patch.dict(os.environ, {}, clear=True):
        assert is_signal_configured() is False


def test_send_signal_notification():
    """Verifies Signal notification dispatch and automatic sanitization."""
    # Empty message returns False
    assert send_signal_notification("") is False

    # Not configured returns False
    with patch.dict(os.environ, {}, clear=True):
        assert send_signal_notification("Test msg") is False

    with patch.dict(
        os.environ,
        {
            "SIGNAL_API_URL": "http://127.0.0.1:8080",
            "SIGNAL_SENDER": "+31612345678",
            "SIGNAL_RECIPIENT": "+31687654321",
        },
    ):
        # Success case
        mock_resp = MagicMock(status_code=201)
        with patch("requests.post", return_value=mock_resp) as mock_post:
            ok = send_signal_notification(
                "Deployment alert with password=TopSecretPass999!"
            )
            assert ok is True
            mock_post.assert_called_once()
            called_payload = mock_post.call_args[1]["json"]
            # Enforce zero-leak in sent payload
            assert "TopSecretPass999!" not in called_payload["message"]
            assert REDACTED_MASK in called_payload["message"]

        # Failure HTTP status
        mock_fail = MagicMock(status_code=500, text="Internal server error")
        with patch("requests.post", return_value=mock_fail):
            assert send_signal_notification("Alert") is False

        # Exception
        with patch("requests.post", side_effect=RuntimeError("Network down")):
            assert send_signal_message("Alert") is False


def test_vault_resolution(tmp_path: Path):
    """Verifies Ansible Vault password resolution."""
    # Direct env var
    with patch.dict(os.environ, {"ANSIBLE_VAULT_PASSWORD": "direct_vault_pass"}):
        assert get_vault_password() == "direct_vault_pass"

    # Password file
    vfile = tmp_path / "vault.txt"
    vfile.write_text("file_vault_pass\n")
    with patch.dict(
        os.environ,
        {"ANSIBLE_VAULT_PASSWORD": "", "ANSIBLE_VAULT_PASSWORD_FILE": str(vfile)},
    ):
        assert resolve_vault_password_file() == vfile
        assert get_vault_password() == "file_vault_pass"

    # Missing file returns None
    with patch.dict(
        os.environ,
        {"ANSIBLE_VAULT_PASSWORD": "", "ANSIBLE_VAULT_PASSWORD_FILE": "/nonexistent"},
    ):
        assert get_vault_password() is None
