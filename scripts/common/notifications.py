# scripts/common/notifications.py
"""Centralized Signal and webhook notification service (CMMI Level 5).

Guarantees Zero-Leak redaction before transmitting any message over external networks.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

from scripts.common.redaction import sanitize_log_output

logger = logging.getLogger(__name__)


def is_signal_configured() -> bool:
    """Checks whether Signal API endpoints and credentials are configured."""
    api_url = os.getenv("SIGNAL_API_URL") or os.getenv("SIGNAL_API")
    sender = os.getenv("SIGNAL_SENDER")
    recipient = os.getenv("SIGNAL_RECIPIENT")
    return bool(api_url and sender and recipient)


def send_signal_notification(
    message: str,
    api_url: Optional[str] = None,
    sender: Optional[str] = None,
    recipient: Optional[str] = None,
    timeout: int = 15,
) -> bool:
    """Sends a Signal notification message with automatic CMMI Zero-Leak redaction.

    Args:
        message: The message body to transmit.
        api_url: Optional custom Signal API endpoint.
            Defaults to SIGNAL_API_URL or SIGNAL_API.
        sender: Optional sending phone number. Defaults to SIGNAL_SENDER.
        recipient: Optional recipient phone number. Defaults to SIGNAL_RECIPIENT.
        timeout: HTTP request timeout in seconds.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not message:
        return False

    # 1. Enforce Zero-Leak sanitization before network dispatch
    safe_message = sanitize_log_output(message)

    resolved_api = api_url or os.getenv("SIGNAL_API_URL") or os.getenv("SIGNAL_API")
    resolved_sender = sender or os.getenv("SIGNAL_SENDER")
    resolved_recipient = recipient or os.getenv("SIGNAL_RECIPIENT")

    if not (resolved_api and resolved_sender and resolved_recipient):
        logger.debug(
            "Signal notification skipped: SIGNAL_API_URL, SIGNAL_SENDER, "
            "or SIGNAL_RECIPIENT not set."
        )
        return False

    clean_api = resolved_api.rstrip("/")
    if not clean_api.endswith("/v2/send"):
        clean_api = f"{clean_api}/v2/send"

    payload: Dict[str, Any] = {
        "message": safe_message,
        "number": resolved_sender,
        "recipients": [resolved_recipient],
    }

    try:
        response = requests.post(clean_api, json=payload, timeout=timeout)
        if response.status_code in (200, 201):
            logger.info("Signal notification sent successfully.")
            return True
        logger.warning(
            f"Signal notification failed with status {response.status_code}: "
            f"{response.text}"
        )
        return False
    except Exception as exc:
        logger.error(f"Error dispatching Signal notification: {exc}")
        return False


# Compatibility alias
send_signal_message = send_signal_notification
