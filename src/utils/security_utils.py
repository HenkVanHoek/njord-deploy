# src/utils/security_utils.py

import os
import re
import urllib.parse
from typing import Iterable, Optional, Set, Tuple

ALLOWED_HTTP_SCHEMES = {"http", "https"}


def validate_and_sanitize_url(
    raw_url: Optional[str],
    allowed_schemes: Optional[set[str]] = None,
    default_url: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validates and sanitizes a URL to defend against SSRF and injection attacks.

    Args:
        raw_url: The untrusted URL string to validate.
        allowed_schemes: Set of permitted URL schemes (defaults to {'http', 'https'}).
        default_url: Optional fallback URL if raw_url is None or empty.

    Returns:
        A tuple of (is_valid, sanitized_url, error_message).
    """
    schemes = allowed_schemes if allowed_schemes is not None else ALLOWED_HTTP_SCHEMES
    candidate = (raw_url or default_url or "").strip()

    if not candidate:
        return False, None, "URL cannot be empty."

    # Check for forbidden control characters or whitespace within the URL string
    if any(c in candidate for c in ("\r", "\n", "\t", "\x00")):
        return False, None, "URL contains illegal control characters."

    # noinspection PyBroadException
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except Exception as e:
        return False, None, f"Malformed URL: {e}"

    # 1. Validate Scheme
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    if not scheme or scheme not in schemes:
        allowed_str = ", ".join(sorted(schemes))
        return (
            False,
            None,
            f"Invalid URL scheme '{parsed.scheme}'. Only [{allowed_str}] are allowed.",
        )

    # 2. Validate Hostname / Netloc
    if not parsed.netloc or not parsed.hostname:
        return False, None, "URL must contain a valid hostname and network location."

    # 3. Clean and reconstruct normalized URL (stripping fragments)
    clean_url = urllib.parse.urlunsplit(
        (
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.query,
            "",  # Remove fragment
        )
    )
    return True, clean_url, None


def is_safe_redirect_url(target: Optional[str]) -> bool:
    """Validates that a URL is safe for internal redirection (prevents open redirects).

    Ensures the target is a relative path starting with '/', does not start with
    '//' or '/\\', contains no backslashes, and has no scheme or netloc.

    Args:
        target: The untrusted redirect target URL.

    Returns:
        True if safe for redirect, False otherwise.
    """
    if not target or not isinstance(target, str):
        return False

    cleaned = target.strip()
    if not cleaned or not cleaned.startswith("/"):
        return False

    # Disallow protocol-relative URLs (//evil.com) and backslash escapes (/\\evil.com)
    if cleaned.startswith("//") or cleaned.startswith("/\\"):
        return False

    # Disallow backslashes anywhere in path
    if "\\" in cleaned:
        return False

    # noinspection PyBroadException
    try:
        sanitized = cleaned.replace("\\", "")
        parsed = urllib.parse.urlsplit(sanitized)
        if parsed.scheme or parsed.netloc:
            return False
        return True
    except Exception:
        return False


def get_safe_redirect_target(target: Optional[str], default_target: str = "/") -> str:
    """Returns a sanitized, safe relative path for redirection.

    Extracts only the path component, ensuring it starts with '/' and never
    contains schemes, hostnames, protocol-relative prefixes, or backslashes.
    Falls back to default_target if unsafe or invalid.
    """
    if not is_safe_redirect_url(target):
        return default_target

    # noinspection PyBroadException
    try:
        parsed = urllib.parse.urlsplit(str(target).strip())
        path = parsed.path
        if (
            path
            and path.startswith("/")
            and not path.startswith("//")
            and "\\" not in path
        ):
            return path
    except Exception:
        return default_target
    return default_target


def build_safe_target_url(
    base_url: Optional[str],
    target_endpoint: str,
    strip_suffix: Optional[str] = None,
    default_url: Optional[str] = None,
    allowed_schemes: Optional[set[str]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validates a base URL and constructs a safe target URL endpoint.

    Args:
        base_url: Untrusted base URL supplied by user or environment.
        target_endpoint: The relative or absolute endpoint path (e.g. '/api/tags').
        strip_suffix: Optional suffix to strip from base path (e.g. '/v1').
        default_url: Fallback base URL if base_url is empty.
        allowed_schemes: Permitted schemes (defaults to {'http', 'https'}).

    Returns:
        A tuple of (is_valid, safe_target_url, error_message).
    """
    is_valid, sanitized_base, err = validate_and_sanitize_url(
        raw_url=base_url,
        allowed_schemes=allowed_schemes,
        default_url=default_url,
    )
    if not is_valid or not sanitized_base:
        return False, None, err

    # noinspection PyBroadException
    try:
        parsed = urllib.parse.urlsplit(sanitized_base)
        base_path = parsed.path.rstrip("/")

        if strip_suffix:
            clean_suffix = strip_suffix.rstrip("/")
            if base_path.endswith(clean_suffix):
                base_path = base_path[: -len(clean_suffix)].rstrip("/")

        clean_endpoint = "/" + target_endpoint.lstrip("/")
        full_path = f"{base_path}{clean_endpoint}" if base_path else clean_endpoint

        target_url = urllib.parse.urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                full_path,
                "",  # Query
                "",  # Fragment
            )
        )
        return True, target_url, None
    except Exception as e:
        return False, None, f"Failed to construct target URL: {e}"


ECHO_SUDO_PATTERN = re.compile(
    r"(echo\s+)(['\"][^'\"]*['\"]|[^\s|]+)(\s*\|\s*sudo(?:\s+-S)?)",
    re.IGNORECASE,
)

PASSWORD_PARAM_PATTERN = re.compile(
    r"((?:password|passwd|ansible_password|ansible_become_password|"
    r"secret|api_key|token)[\"']?\s*[:=]\s*['\"])(?:(?!\1)[^\"'\s]+)(['\"])",
    re.IGNORECASE,
)


def mask_passwords(
    text: str,
    extra_secrets: Optional[Iterable[str]] = None,
    mask: str = "*******",
) -> str:
    """Mask sensitive passwords and echo credentials from logs and strings.

    Replaces:
    1. 'echo <password> | sudo' and 'echo '<password>' | sudo -S' patterns.
    2. Sensitive key-value fields (password, ansible_password, token, etc.).
    3. Any explicit secrets passed in extra_secrets or environment variables
       (PROXMOX_PASSWORD, PROXMOX_VM_PASSWORD, etc.).

    Args:
        text: Input string potentially containing plaintext credentials.
        extra_secrets: Optional iterable of additional secret strings to mask.
        mask: Mask string to replace credentials (defaults to '*******').

    Returns:
        Sanitized string safe for logging, terminal streaming, and reports.
    """
    if not text:
        return text

    # 1. Mask 'echo <password> | sudo [-S]'
    sanitized = ECHO_SUDO_PATTERN.sub(rf"\1'{mask}'\3", text)

    # 2. Mask password fields in key-value config lines / JSON
    sanitized = PASSWORD_PARAM_PATTERN.sub(rf"\1{mask}\2", sanitized)

    # 3. Mask explicit secrets
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
    ):
        val = os.getenv(env_var)
        if val and len(val) >= 3:
            secrets_to_mask.add(val)

    for secret in secrets_to_mask:
        sanitized = sanitized.replace(secret, mask)

    return sanitized
