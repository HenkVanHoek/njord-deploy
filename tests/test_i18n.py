# tests/test_i18n.py
"""Unit test suite for NjordDeploy i18n localization engine."""

import unittest

from flask import Flask, session

from src.utils.i18n import TranslationManager, _, init_i18n


class TestTranslationManager(unittest.TestCase):
    """Verifies i18n translation lookup, parameter formatting, and fallback."""

    def setUp(self):
        self.mgr = TranslationManager()
        self.mgr.translations = {
            "en": {
                "welcome": "Welcome to NjordDeploy",
                "hello_user": "Hello, {name}!",
                "items_count": "You have {count} items.",
            },
            "nl": {
                "welcome": "Welkom bij NjordDeploy",
                "hello_user": "Hallo, {name}!",
            },
        }

    def test_direct_translation(self):
        """Verify translating existing keys in target language."""
        self.assertEqual(
            self.mgr.gettext("welcome", lang="nl"),
            "Welkom bij NjordDeploy",
        )
        self.assertEqual(
            self.mgr.gettext("welcome", lang="en"),
            "Welcome to NjordDeploy",
        )

    def test_parameter_formatting(self):
        """Verify dynamic parameter substitution in translated text."""
        self.assertEqual(
            self.mgr.gettext("hello_user", lang="nl", name="Henk"),
            "Hallo, Henk!",
        )
        self.assertEqual(
            self.mgr.gettext("hello_user", lang="en", name="Henk"),
            "Hello, Henk!",
        )

    def test_fallback_to_english(self):
        """Verify fallback to English when key is missing in Dutch."""
        # 'items_count' exists in en, missing in nl
        self.assertEqual(
            self.mgr.gettext("items_count", lang="nl", count=5),
            "You have 5 items.",
        )

    def test_fallback_to_raw_key(self):
        """Verify return of raw key when missing in all languages."""
        self.assertEqual(
            self.mgr.gettext("completely_unknown_key", lang="nl"),
            "completely_unknown_key",
        )

    def test_language_detection_in_flask_context(self):
        """Verify language resolution hierarchy.

        Order: session > cookie > header > default.
        """
        app = Flask(__name__)
        app.secret_key = "test-secret"
        init_i18n(app, translation_manager=self.mgr)

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"},
        ):
            # Header detection
            self.assertEqual(self.mgr.get_locale(), "nl")

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "de-DE,de;q=0.9"},
        ):
            # Unsupported language falls back to default 'en'
            self.assertEqual(self.mgr.get_locale(), "en")

        with app.test_request_context("/"):
            # Session explicit override
            session["lang"] = "nl"
            self.assertEqual(self.mgr.get_locale(), "nl")
            self.assertEqual(_("welcome"), "Welkom bij NjordDeploy")

    def test_set_language_endpoint(self):
        """Verify language switching via configurator app API endpoint."""
        from src.configurator_app.app import create_app

        app = create_app(test_config={"TESTING": True, "AUTH_ENABLED": False})
        client = app.test_client()

        # Switch to Dutch
        res = client.get("/api/v1/set-language/nl")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("language"), "nl")

        # Verify invalid locale returns 400
        bad_res = client.get("/api/v1/set-language/invalid_lang")
        self.assertEqual(bad_res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
