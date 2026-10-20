# tests/managers/test_chatwoot_bot_manager.py

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from managers.chatwoot_bot_manager import ChatwootBotManager


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

    def test_detect_language_metadata_and_heuristics(self):
        """Verify language detection via browser metadata, sender locale, and text."""
        # Test browser language in conversation metadata
        payload_nl = {
            "conversation": {"additional_attributes": {"browser_language": "nl-NL"}}
        }
        self.assertEqual(self.manager.detect_language(payload_nl, "Short note"), "nl")

        payload_en = {
            "conversation": {"additional_attributes": {"browser_language": "en-US"}}
        }
        self.assertEqual(
            self.manager.detect_language(payload_en, "Korte notitie"), "en"
        )

        # Test text heuristic fallback
        self.assertEqual(
            self.manager.detect_language(
                {}, "How can I install Nextcloud on Debian with Docker?"
            ),
            "en",
        )
        self.assertEqual(
            self.manager.detect_language(
                {}, "Hoe kan ik Nextcloud installeren op mijn server?"
            ),
            "nl",
        )

    @patch.object(ChatwootBotManager, "send_message")
    def test_localized_failover_reassurance(self, mock_send):
        """Verify failover reassurance callback sends English text for EN visitors."""

        def fake_generate(prompt, system_context=None, failover_callback=None):
            if failover_callback:
                failover_callback()
            return "Here is your answer!"

        self.mock_ai_engine.generate.side_effect = fake_generate

        payload_en = {
            "event": "message_created",
            "message_type": "incoming",
            "private": False,
            "content": "How do I configure Traefik SSL certificates?",
            "conversation": {
                "id": 88,
                "additional_attributes": {"browser_language": "en-US"},
            },
            "account": {"id": 1},
        }

        success, _ = self.manager.handle_webhook_event(payload_en, sync=True)
        self.assertTrue(success)

        # First message sent was the failover reassurance in English, then the AI answer
        call_contents = [call[1]["content"] for call in mock_send.call_args_list]
        self.assertTrue(any("Please hold on a moment" in c for c in call_contents))
        self.assertTrue(any("Here is your answer!" in c for c in call_contents))

    def test_webhook_event_filtering_and_formats(self):
        """Verifies payload validation, signature verification, and event filtering."""
        # 1. Disabled manager
        disabled_mgr = ChatwootBotManager(
            base_url="https://chat.njorddeploy.com",
            bot_token="token",
            enabled=False,
        )
        ok_dis, msg_dis = disabled_mgr.handle_webhook_event({})
        self.assertTrue(ok_dis)
        self.assertIn("disabled", msg_dis)

        # 2. Unsupported format (e.g. integer or list)
        ok_fmt, msg_fmt = self.manager.handle_webhook_event(12345)
        self.assertFalse(ok_fmt)
        self.assertIn("Unsupported", msg_fmt)

        # 3. String payload with invalid signature
        ok_sig, msg_sig = self.manager.handle_webhook_event(
            '{"event": "message_created"}',
            signature_header="invalid_sig",
        )
        self.assertFalse(ok_sig)
        self.assertIn("Invalid webhook signature", msg_sig)

        # 4. String payload with valid signature but malformed JSON
        import hmac

        bad_json = b"not-a-json{"
        sig = hmac.new(b"test_secret", bad_json, "sha256").hexdigest()
        ok_json, msg_json = self.manager.handle_webhook_event(
            bad_json, signature_header=sig
        )
        self.assertFalse(ok_json)
        self.assertIn("Malformed JSON", msg_json)

        # 5. Ignored event type
        ok_evt, _ = self.manager.handle_webhook_event(
            {"event": "conversation_status_changed"}
        )
        self.assertTrue(ok_evt)

        # 6. Ignored non-incoming message
        ok_out, _ = self.manager.handle_webhook_event(
            {"event": "message_created", "message_type": "outgoing"}
        )
        self.assertTrue(ok_out)

        # 7. Ignored private note
        ok_priv, _ = self.manager.handle_webhook_event(
            {
                "event": "message_created",
                "message_type": "incoming",
                "private": True,
            }
        )
        self.assertTrue(ok_priv)

        # 8. Asynchronous processing (sync=False) launches thread
        with patch("threading.Thread") as mock_thread:
            ok_async, msg_async = self.manager.handle_webhook_event(
                {
                    "event": "message_created",
                    "message_type": "incoming",
                    "private": False,
                },
                sync=False,
            )
            self.assertTrue(ok_async)
            self.assertIn("queued", msg_async)
            mock_thread.assert_called_once()

    def test_process_incoming_message_guard_clauses(self):
        """Tests edge cases and sanitization in _process_incoming_message."""
        # 1. Empty content -> no-op
        self.manager._process_incoming_message({"content": "   "})

        # 2. Missing or non-dict conversation
        self.manager._process_incoming_message(
            {"content": "Hello", "conversation": None}
        )

        # 3. Missing conversation ID or account ID
        self.manager._process_incoming_message(
            {"content": "Hello", "conversation": {"id": None}, "account": None}
        )

        # 4. Content truncation over 1000 characters
        long_content = "X" * 1500
        payload_long = {
            "content": long_content,
            "conversation": {"id": 12},
            "account": {"id": 1},
        }
        with patch.object(self.manager, "send_message") as mock_send:
            self.manager._process_incoming_message(payload_long)
            mock_send.assert_called_once()

    def test_detect_language_from_sender_custom_attributes(self):
        """Verifies language detection from sender custom_attributes."""
        payload_nl = {
            "sender": {"custom_attributes": {"language": "nl-NL"}},
        }
        self.assertEqual(self.manager.detect_language(payload_nl, "Kort bericht"), "nl")

        payload_en = {
            "sender": {"custom_attributes": {"language": "en-US"}},
        }
        self.assertEqual(self.manager.detect_language(payload_en, "Short note"), "en")

    def test_api_call_exceptions_and_failures(self):
        """Tests failure handling in send_message and toggle status methods."""
        # 1. send_message API HTTP error code
        mock_resp_500 = MagicMock(status_code=500, text="Internal error")
        with patch("requests.post", return_value=mock_resp_500):
            res_fail = self.manager.send_message(
                account_id=1, conversation_id=10, content="test"
            )
            self.assertFalse(res_fail)

        # 2. send_message Exception
        with patch("requests.post", side_effect=Exception("Network drop")):
            res_exc = self.manager.send_message(
                account_id=1, conversation_id=10, content="test"
            )
            self.assertFalse(res_exc)

        # 3. toggle_conversation_status Exception
        with patch("requests.post", side_effect=Exception("Network drop")):
            res_toggle_exc = self.manager.toggle_conversation_status(
                account_id=1, conversation_id=10, status="resolved"
            )
            self.assertFalse(res_toggle_exc)

        # 4. toggle_typing_status Exception
        with patch("requests.post", side_effect=Exception("Network drop")):
            res_typing_exc = self.manager.toggle_typing_status(
                account_id=1, conversation_id=10, typing_status="off"
            )
            self.assertFalse(res_typing_exc)

    def test_chatwoot_bot_manager_edge_cases(self):
        """Test default enabled, knowledge IO errors, signature without secret,
        and AI error fallbacks."""
        # 1. enabled=None uses CHATWOOT_AI_ENABLED env var (line 109)
        with patch.dict(os.environ, {"CHATWOOT_AI_ENABLED": "false"}):
            m1 = ChatwootBotManager()
            self.assertFalse(m1.enabled)

        # 2. Knowledge context file read errors (lines 140-141, 148-149)
        m2 = ChatwootBotManager()
        with patch.object(Path, "read_text", side_effect=IOError("Corrupt text")):
            ctx = m2.get_knowledge_context()
            self.assertIn("NjordDeploy", ctx)

        # 3. is_escalation_request with empty string (line 157)
        self.assertFalse(m2.is_escalation_request(""))

        # 4. verify_signature without webhook secret (line 259)
        m2.webhook_secret = ""
        self.assertTrue(m2.verify_signature(b"{}", None))

        # 5. AI engine without generate attribute (lines 406, 409)
        mock_send = MagicMock()
        payload = {
            "content": "Hello",
            "conversation": {"id": 10},
            "account": {"id": 1},
        }
        with patch.object(self.manager, "send_message", mock_send):
            self.manager._explicit_ai_engine = object()
            self.manager._process_incoming_message(payload)
            self.assertTrue(mock_send.called)

        # 6. AI engine throws exception (lines 410-412)
        mock_send2 = MagicMock()
        mock_broken_engine = MagicMock()
        mock_broken_engine.generate.side_effect = RuntimeError("AI server crashed")
        self.manager._explicit_ai_engine = mock_broken_engine
        with patch.object(self.manager, "send_message", mock_send2):
            self.manager._process_incoming_message(payload)
            self.assertTrue(mock_send2.called)


if __name__ == "__main__":
    unittest.main()
