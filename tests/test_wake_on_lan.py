"""Tests for Wake-on-LAN and emergency AI failover."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from utils.ai_generator_engine import AIGeneratorEngine
from utils.wake_on_lan import send_wake_on_lan


def test_send_wake_on_lan_success():
    """Verifies that send_wake_on_lan builds the 102-byte magic packet."""
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value.__enter__.return_value = mock_sock

        mac = "e8:9c:25:29:f0:0c"
        result = send_wake_on_lan(mac, broadcast_ip="192.168.178.255", port=9)

        assert result is True
        mock_sock.setsockopt.assert_called_once_with(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1
        )

        args, _ = mock_sock.sendto.call_args
        packet, dest = args
        assert dest == ("192.168.178.255", 9)
        # Magic packet: 6 bytes 0xFF + 16 * 6 bytes MAC = 102 bytes
        assert len(packet) == 102
        assert packet[:6] == b"\xff" * 6
        expected_mac_bytes = bytes.fromhex("e89c2529f00c")
        assert packet[6:12] == expected_mac_bytes
        assert packet[96:102] == expected_mac_bytes


def test_send_wake_on_lan_invalid_mac():
    """Verifies that invalid MAC addresses return False safely."""
    assert send_wake_on_lan("invalid-mac") is False
    assert send_wake_on_lan("12:34") is False


def test_emergency_wol_and_signal_failover():
    """Verifies that emergency failover triggers WOL and Signal when clouds fail."""
    engine = AIGeneratorEngine(provider="gemini")

    with (
        patch.object(
            engine,
            "_generate_openai_compatible",
            side_effect=RuntimeError("Cloud unavailable"),
        ),
        patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "fake-key",
                "HOSTYOURAI_API_KEY": "fake-key",
                "WOL_LOCAL_AI_MAC": "e8:9c:25:29:f0:0c",
                "WOL_BROADCAST_IP": "255.255.255.255",
                "SIGNAL_RECIPIENT": "+31651107603",
            },
        ),
        patch("utils.wake_on_lan.send_wake_on_lan") as mock_wol,
        patch("utils.fums_notifier.FUMSNotifier.send_signal") as mock_signal,
    ):
        mock_wol.return_value = True
        mock_signal.return_value = True

        with pytest.raises(RuntimeError):
            engine.generate("test emergency prompt")

        mock_wol.assert_called_once_with(
            "e8:9c:25:29:f0:0c", broadcast_ip="255.255.255.255"
        )
        mock_signal.assert_called_once()
        sent_msg, sent_rec = mock_signal.call_args[0]
        assert "+31651107603" == sent_rec
        assert "NjordDeploy Nood-Failover" in sent_msg
