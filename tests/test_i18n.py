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

    def test_editor_and_configurator_template_i18n(self):
        """Verifies editor_app and configurator_app templates render without 500."""
        from src.configurator_app.app import create_app as create_conf_app
        from src.editor_app.app import create_app as create_edit_app

        c_app = create_conf_app(test_config={"TESTING": True, "AUTH_ENABLED": False})
        c_client = c_app.test_client()
        res_conf = c_client.get("/")
        self.assertEqual(res_conf.status_code, 200)

        e_app = create_edit_app(test_config={"TESTING": True, "AUTH_ENABLED": False})
        e_client = e_app.test_client()
        res_edit = e_client.get("/")
        self.assertEqual(res_edit.status_code, 200)

    def test_cookie_and_error_handling(self):
        """Verifies cookie detection, format errors, and corrupt translation
        handling."""
        import tempfile

        from src.utils.i18n import get_translation_manager

        # get_translation_manager
        self.assertIsNotNone(get_translation_manager())

        # Cookie detection
        app = Flask(__name__)
        app.secret_key = "test"
        with app.test_request_context("/", headers={"Cookie": "njord_lang=nl"}):
            self.assertEqual(self.mgr.get_locale(), "nl")

        # Formatting error fallback
        self.mgr.translations["en"]["broken"] = "Broken {missing}"
        res = self.mgr.gettext("broken", lang="en", extra="val")
        self.assertEqual(res, "Broken {missing}")

        # Non-existent locales directory
        from pathlib import Path

        mgr_nonexist = TranslationManager(locales_dir=Path("/nonexistent/locales/dir"))
        self.assertEqual(mgr_nonexist.translations, {})

        # Corrupt translation file
        with tempfile.TemporaryDirectory() as tmpdir:
            loc_dir = Path(tmpdir)
            (loc_dir / "nl.json").write_text("{ invalid json")
            mgr_corrupt = TranslationManager(locales_dir=loc_dir)
            self.assertEqual(mgr_corrupt.translations, {})

        # Exception in get_locale when outside request context
        self.assertEqual(self.mgr.get_locale(), "en")

        # Exception caught inside get_locale request context
        from unittest.mock import MagicMock, patch

        mock_req = MagicMock()
        mock_req.cookies.get.side_effect = RuntimeError("Explosion")
        with patch("src.utils.i18n.request", mock_req):
            self.assertEqual(self.mgr.get_locale(), "en")

    def test_pyinstaller_meipass_discovery(self):
        """Verify PyInstaller sys._MEIPASS bundle discovery."""
        import sys
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            loc1 = tmp_path / "src" / "locales"
            loc1.mkdir(parents=True)
            (loc1 / "en.json").write_text('{"test_key": "from_src_locales"}')

            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                # Fake Path(__file__) non-existent parent.parent / locales
                with patch("src.utils.i18n.Path.exists") as mock_exists:
                    # Make cand1 not exist, cand2 exist
                    def side_effect(*args, **kwargs):
                        return bool(args and "src/locales" in str(args[0]))

                    mock_exists.side_effect = side_effect
                    mgr = TranslationManager()
                    self.assertIn("src", str(mgr.locales_dir))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            loc2 = tmp_path / "locales"
            loc2.mkdir(parents=True)
            (loc2 / "en.json").write_text('{"test_key": "from_locales"}')

            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                with patch("src.utils.i18n.Path.exists") as mock_exists:

                    def side_effect2(*args, **kwargs):
                        s = str(args[0]) if args else ""
                        return s.endswith("/locales") and "src" not in s

                    mock_exists.side_effect = side_effect2
                    mgr = TranslationManager()
                    self.assertIn("locales", str(mgr.locales_dir))


if __name__ == "__main__":
    unittest.main()
