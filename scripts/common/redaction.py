# scripts/common/redaction.py
"""Centralized Zero-Leak Redaction & Log Sanitization (CMMI Level 5).

Ensures all output, logs, Signal notifications, and CLI messages are stripped of
ANSI escape codes and scrubbed of sensitive credentials, tokens, and keys.
"""

import os
import re
from typing import Iterable, Optional, Set

ANSI_ESCAPE_PATTERN = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")

# Standard credential patterns
ECHO_SUDO_PATTERN = re.compile(
    r"(echo\s+)(['\"]?[^|'\"]+['\"]?)(\s*\|\s*sudo(?:\s+-S)?)",
    re.IGNORECASE,
)

PASSWORD_PARAM_PATTERN = re.compile(
    r"((?:password|passwd|ansible_password|secret|token|api_key|auth_token|"
    r"bearer|keyring)[\"'\s:=]+)([\"'][^\"'\n\r\t]+[\"']|[^\s,;\"'}{\]]+)",
    re.IGNORECASE,
)

BEARER_TOKEN_PATTERN = re.compile(
    r"(Bearer\s+)([A-Za-z0-9_\-\.]{10,})",
    re.IGNORECASE,
)

PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----",
    re.DOTALL,
)

REDACTED_MASK = "***REDACTED***"


def strip_ansi(text: str) -> str:
    """Removes all ANSI escape code sequences from text."""
    if not text:
        return ""
    return ANSI_ESCAPE_PATTERN.sub("", text)


def mask_secret_value(value: Optional[str], visible_chars: int = 0) -> str:
    """Masks a secret string completely or leaving visible_chars prefix."""
    if not value:
        return REDACTED_MASK
    if visible_chars <= 0 or len(value) <= visible_chars:
        return REDACTED_MASK
    return f"{value[:visible_chars]}...{REDACTED_MASK}"


def redact_sensitive_text(
    text: str,
    extra_secrets: Optional[Iterable[str]] = None,
    mask: str = REDACTED_MASK,
) -> str:
    """Redacts passwords, tokens, API keys, private keys, and environment secrets.

    Guarantees CMMI Zero-Leak compliance across all log files and notification payloads.
    """
    if not text:
        return ""

    sanitized = text

    # 1. Mask private keys
    sanitized = PRIVATE_KEY_PATTERN.sub(
        f"-----BEGIN PRIVATE KEY-----\n{mask}\n-----END PRIVATE KEY-----",
        sanitized,
    )

    # 2. Mask 'echo <password> | sudo'
    sanitized = ECHO_SUDO_PATTERN.sub(rf"\1'{mask}'\3", sanitized)

    # 3. Mask Bearer tokens
    sanitized = BEARER_TOKEN_PATTERN.sub(rf"\1{mask}", sanitized)

    # 4. Mask key-value configurations (password, token, api_key, etc.)
    def _mask_kv(match: re.Match) -> str:
        prefix = match.group(1)
        val = match.group(2)
        quote = ""
        if val.startswith(('"', "'")) and val.endswith(('"', "'")) and len(val) >= 2:
            quote = val[0]
        return f"{prefix}{quote}{mask}{quote}"

    sanitized = PASSWORD_PARAM_PATTERN.sub(_mask_kv, sanitized)

    # 5. Mask explicit secrets from callers and known secret env vars
    secrets_to_mask: Set[str] = set()
    if extra_secrets:
        for s in extra_secrets:
            if s and len(s) >= 3:
                secrets_to_mask.add(s)

    for env_var in (
        "PROXMOX_PASSWORD",
        "PROXMOX_VM_PASSWORD",
        "PVE_PASSWORD",
        "VM_PASSWORD",
        "ANSIBLE_PASSWORD",
        "SSH_PASSWORD",
        "SIGNAL_TOKEN",
        "GITHUB_TOKEN",
        "FORGEJO_TOKEN",
        "CODEBERG_TOKEN",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        val = os.getenv(env_var)
        if val and len(val) >= 3:
            secrets_to_mask.add(val)

    for secret in sorted(secrets_to_mask, key=len, reverse=True):
        sanitized = sanitized.replace(secret, mask)

    return sanitized


def sanitize_log_output(
    text: str,
    extra_secrets: Optional[Iterable[str]] = None,
    mask: str = REDACTED_MASK,
) -> str:
    """Strips ANSI sequences and redacts sensitive credentials in one pass."""
    clean_ansi = strip_ansi(text)
    return redact_sensitive_text(clean_ansi, extra_secrets=extra_secrets, mask=mask)
