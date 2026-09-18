# tests/managers/test_chatwoot_bot_manager.py

import unittest
from unittest.mock import MagicMock, patch

from src.managers.chatwoot_bot_manager import ChatwootBotManager


class TestChatwootBotManager(unittest.TestCase):
    """Unit test suite for ChatwootBotManager."""

    def setUp(self):
        """Set up ChatwootBotManager with mocked AI engine."""
        self.mock_ai_engine = MagicMock()
        self.mock_ai_engine.generate.return_value = (
            "NjordDeploy draait soeverein op Debian 12 en Raspberry Pi!"
        )
        self.manager = ChatwootBotManager(
            base_url="https://chat.njorddeploy.com",
            bot_token="test_bot_token_123",
            ai_engine=self.mock_ai_engine,
            enabled=True,
            webhook_secret="test_secret",
        )

    def test_escalation_detection(self):
        """Verify keyword detection for human operator escalation."""
        self.assertTrue(
            self.manager.is_escalation_request("Kan ik met een mens spreken?")
        )
        self.assertTrue(
            self.manager.is_escalation_request("Ik wil graag een medewerker bellen.")
        )
        self.assertTrue(
            self.manager.is_escalation_request("Please connect me to a human agent.")
        )
        self.assertTrue(
            self.manager.is_escalation_request("Kan ik Henk hierover bereiken?")
        )
        self.assertFalse(
            self.manager.is_escalation_request("Hoe installeer ik Nextcloud?")
        )
        self.assertFalse(
            self.manager.is_escalation_request("Wat zijn de systeemeisen?")
        )

    def test_signature_verification(self):
        """Verify HMAC SHA-256 signature validation."""
        import hmac

        payload = b'{"hello": "world"}'
        valid_sig = hmac.new(b"test_secret", payload, "sha256").hexdigest()
        self.assertTrue(self.manager.verify_signature(payload, valid_sig))
        self.assertFalse(self.manager.verify_signature(payload, "invalid_sig"))
        self.assertFalse(self.manager.verify_signature(payload, None))

    def test_knowledge_context_loading(self):
        """Verify that knowledge context contains core tenets."""
        context = self.manager.get_knowledge_context()
        self.assertIn("Njord Assistant", context)
        self.assertIn("Soeverein", context)
        self.assertIn("Agentless", context)

    @patch("src.managers.chatwoot_bot_manager.requests.post")
    def test_send_message_success(self, mock_post):
        """Verify successful message delivery via Chatwoot API."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = self.manager.send_message(
            account_id=1,
            conversation_id=42,
            content="Test response",
            private=False,
        )
        self.assertTrue(result)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["json"]["content"], "Test response")
        self.assertFalse(call_kwargs["json"]["private"])

    @patch("src.managers.chatwoot_bot_manager.requests.post")
    def test_toggle_conversation_status(self, mock_post):
        """Verify toggling conversation status in Chatwoot."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = self.manager.toggle_conversation_status(
            account_id=1, conversation_id=42, status="open"
        )
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch.object(ChatwootBotManager, "send_message")
    def test_handle_webhook_event_ai_response(self, mock_send):
        """Verify normal question generates AI reply."""
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "private": False,
            "content": "Hoe werkt het deployen van AdGuard Home?",
            "conversation": {"id": 10},
            "account": {"id": 1},
        }
        success, msg = self.manager.handle_webhook_event(payload, sync=True)
        self.assertTrue(success)
        self.mock_ai_engine.generate.assert_called_once()
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        self.assertIn("Debian 12", kwargs.get("content", ""))

    @patch.object(ChatwootBotManager, "send_message")
    @patch.object(ChatwootBotManager, "toggle_conversation_status")
    def test_handle_webhook_event_escalation(self, mock_toggle, mock_send):
        """Verify human escalation triggers handoff and status change."""
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "private": False,
            "content": "Ik wil graag een menselijke medewerker spreken",
            "conversation": {"id": 10},
            "account": {"id": 1},
        }
        success, msg = self.manager.handle_webhook_event(payload, sync=True)
        self.assertTrue(success)
        mock_toggle.assert_called_once_with(1, 10, "open")
        self.assertEqual(mock_send.call_count, 2)

    @patch.object(ChatwootBotManager, "send_message")
    def test_rate_limiter_exceeded(self, mock_send):
        """Verify rapid repeated messages trigger rate limiter warning."""
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "private": False,
            "content": "Snel bericht",
            "conversation": {"id": 99},
            "account": {"id": 1},
        }
        for _ in range(5):
            self.manager.handle_webhook_event(payload, sync=True)

        # 6th message should be blocked by rate limiter
        self.manager.handle_webhook_event(payload, sync=True)
        call_contents = [
            c[1]["content"] for c in mock_send.call_args_list if "content" in c[1]
        ]
        self.assertTrue(
            any("te veel berichten" in content for content in call_contents)
        )

    def test_dynamic_ai_engine_resolution(self):
        """Verify dynamic AI engine provider resolution from environment."""
        mgr = ChatwootBotManager(enabled=True)
        with patch.dict("os.environ", {"CHATWOOT_AI_PROVIDER": "gemini"}):
            engine = mgr.ai_engine
            self.assertEqual(engine.provider, "gemini")

        with patch.dict(
            "os.environ",
            {
                "CHATWOOT_AI_PROVIDER": "ollama",
                "CHATWOOT_AI_MODEL": "custom-model",
            },
        ):
            engine2 = mgr.ai_engine
            self.assertEqual(engine2.provider, "ollama")
            self.assertEqual(engine2.model, "custom-model")


if __name__ == "__main__":
    unittest.main()
