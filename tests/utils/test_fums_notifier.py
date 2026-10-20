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


def test_fums_notifier_unconfigured_and_errors():
    """Test unconfigured, invalid url, failed responses, and exceptions."""
    # 1. Unconfigured
    empty = FUMSNotifier()
    assert empty.send_signal("msg", "+316") is False
    assert empty.send_matrix("!room", "msg") is False
    assert empty.escalate_p1_admin("app", "host", "err") is False

    # 2. Invalid API URL
    bad_url_notifier = FUMSNotifier(
        signal_api="javascript:alert(1)",
        signal_sender="+316",
        matrix_homeserver="ftp://bad",
        matrix_token="tok",
    )
    assert bad_url_notifier.send_signal("msg", "+316") is False
    assert bad_url_notifier.send_matrix("!room", "msg") is False

    # 3. HTTP status 500 and exceptions
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=500)
        n = FUMSNotifier(
            signal_api="https://sig.local",
            signal_sender="+316",
            matrix_homeserver="https://mat.local",
            matrix_token="tok",
            admin_signal_recipient="+3169",
        )
        assert n.send_signal("msg", "+316") is False
        assert n.send_matrix("!room", "msg") is False

        # Rollback not performed check
        mock_post.return_value = MagicMock(status_code=200)
        n.escalate_p1_admin("app", "host", "err", rollback_performed=False)
        last_kwargs = mock_post.call_args[1]
        assert "ROLLBACK NIET BEVESTIGD" in last_kwargs["json"]["message"]

        # Exceptions
        mock_post.side_effect = Exception("network down")
        assert n.send_signal("msg", "+316") is False
        assert n.send_matrix("!room", "msg") is False
