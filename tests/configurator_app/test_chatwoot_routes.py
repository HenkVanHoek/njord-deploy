# tests/configurator_app/test_chatwoot_routes.py

import json
import unittest
from unittest.mock import patch

from src.configurator_app.app import create_app


class TestChatwootRoutes(unittest.TestCase):
    """Test suite for Chatwoot webhook endpoints in configurator app."""

    def setUp(self):
        """Set up test client and patch ChatwootBotManager."""
        self.patcher_chatwoot = patch("src.configurator_app.app.ChatwootBotManager")
        self.mock_chatwoot_class = self.patcher_chatwoot.start()
        self.mock_chatwoot = self.mock_chatwoot_class.return_value
        self.mock_chatwoot.handle_webhook_event.return_value = (
            True,
            "Message queued for AI processing.",
        )

        self.app = create_app({"TESTING": True, "AUTH_ENABLED": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher_chatwoot.stop()

    def test_webhook_public_access_no_auth_required(self):
        """Verify webhook is whitelisted and reachable without session cookie."""
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "Hallo, test!",
            "conversation": {"id": 1},
            "account": {"id": 1},
        }
        response = self.client.post(
            "/api/v1/chatwoot/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "processed")
        self.mock_chatwoot.handle_webhook_event.assert_called_once()

    def test_webhook_alias_endpoint(self):
        """Verify /api/chatwoot/webhook alias works identically."""
        payload = {"event": "conversation_created"}
        response = self.client.post(
            "/api/chatwoot/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.mock_chatwoot.handle_webhook_event.assert_called_once()

    def test_webhook_failure_returns_400(self):
        """Verify failed webhook event returns HTTP 400."""
        self.mock_chatwoot.handle_webhook_event.return_value = (
            False,
            "Invalid webhook signature.",
        )
        response = self.client.post(
            "/api/v1/chatwoot/webhook",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
