# tests/utils/test_fums_notifier.py
"""Unit tests for FUMS Notification Dispatcher."""

from unittest.mock import MagicMock, patch

from utils.fums_notifier import FUMSNotifier


def test_format_client_proposal():
    notifier = FUMSNotifier()
    risk_info = {
        "risk_level": "RED",
        "gatekeeper_certified": True,
        "reasons": ["Major version bump", "Database migration detected"],
    }
    proposal = notifier.format_client_proposal(
        component_name="Nextcloud",
        old_version="v29.0.5",
        new_version="v30.0.0",
        risk_info=risk_info,
        approval_token="secret-token-123",
    )
    assert (
        "Nextcloud v29.0.5 -> v30.0.0 (Major Release)" in proposal
        or "Nextcloud v29.0.5 -> v30.0.0" in proposal
    )
    assert "GECERTIFICEERD (100% geslaagd in Proxmox sandbox)" in proposal
    assert "High-Safety:" in proposal
    assert "token=secret-token-123" in proposal


@patch("requests.post")
def test_send_signal_success(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = FUMSNotifier(
        signal_api="https://signal.local/v2/send",
        signal_sender="+31600000000",
    )
    res = notifier.send_signal("Hello", "+31611111111")
    assert res is True
    assert mock_post.called


@patch("requests.post")
def test_send_matrix_success(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = FUMSNotifier(
        matrix_homeserver="https://matrix.org",
        matrix_token="token_abc",
    )
    res = notifier.send_matrix("!room:matrix.org", "Test Matrix Message")
    assert res is True
    assert mock_post.called


@patch("requests.post")
def test_escalate_p1_admin(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = FUMSNotifier(
        signal_api="https://signal.local/v2/send",
        signal_sender="+31600000000",
        admin_signal_recipient="+31699999999",
    )
    res = notifier.escalate_p1_admin(
        component_name="Immich",
        target_host="192.168.1.50",
        error_reason="Container crash on DB migration",
        rollback_performed=True,
    )
    assert res is True
    call_args, call_kwargs = mock_post.call_args
    assert "P1 ESCALATIE" in call_kwargs["json"]["message"]
    assert "HERSTELD" in call_kwargs["json"]["message"]
