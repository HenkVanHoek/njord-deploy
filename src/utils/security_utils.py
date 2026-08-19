# src/utils/security_utils.py

import urllib.parse
from typing import Optional, Tuple

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
