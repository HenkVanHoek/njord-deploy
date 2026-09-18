"""NjordDeploy i18n Localization Engine.

Provides lightweight, robust internationalization for Flask Jinja2 templates,
session-based language selection (EN / NL), header negotiation, and parameter
formatting conforming to the KISS architectural principle.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, request, session

logger = logging.getLogger(__name__)

SUPPORTED_LOCALES: List[str] = ["en", "nl"]
DEFAULT_LOCALE: str = "en"


class TranslationManager:
    """Manages loading, caching, and querying translation dictionaries."""

    def __init__(self, locales_dir: Optional[Path] = None) -> None:
        self.locales_dir = locales_dir or (
            Path(__file__).resolve().parent.parent / "locales"
        )
        self.translations: Dict[str, Dict[str, str]] = {}
        self.load_translations()

    def load_translations(self) -> None:
        """Loads all available locale JSON files into memory."""
        if not self.locales_dir.exists():
            logger.debug(
                "Locales directory not found at %s. Initializing empty.",
                self.locales_dir,
            )
            return

        for lang in SUPPORTED_LOCALES:
            lang_file = self.locales_dir / f"{lang}.json"
            if lang_file.is_file():
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self.translations[lang] = data
                except Exception as exc:
                    logger.error(
                        "Failed to load translation file %s: %s", lang_file, exc
                    )

    def get_locale(self) -> str:
        """Resolves active locale based on session, cookies, or HTTP headers."""
        try:
            # 1. Explicit session preference
            if session and isinstance(session, dict):
                sess_lang = session.get("lang")
                if isinstance(sess_lang, str) and sess_lang in SUPPORTED_LOCALES:
                    return sess_lang

            # 2. Cookie preference
            if request and hasattr(request, "cookies"):
                cookie_lang = request.cookies.get("njord_lang")
                if cookie_lang in SUPPORTED_LOCALES:
                    return cookie_lang

            # 3. HTTP Accept-Language negotiation
            if request and hasattr(request, "accept_languages"):
                best = request.accept_languages.best_match(SUPPORTED_LOCALES)
                if best in SUPPORTED_LOCALES:
                    return best
        except Exception as exc:
            logger.debug("Failed resolving request locale context: %s", exc)

        return DEFAULT_LOCALE

    def gettext(self, key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
        """Translates a message key into the target language with formatting."""
        active_lang = lang or self.get_locale()
        trans_dict = self.translations.get(active_lang, {})
        text = trans_dict.get(key)

        # Fallback to default locale (English) if missing
        if text is None and active_lang != DEFAULT_LOCALE:
            fallback_dict = self.translations.get(DEFAULT_LOCALE, {})
            text = fallback_dict.get(key)

        # Fallback to key itself if not found anywhere
        if text is None:
            text = key

        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception as exc:
                logger.debug("Failed to format translation string '%s': %s", text, exc)

        return text


_global_translation_manager = TranslationManager()


def get_translation_manager() -> TranslationManager:
    """Returns singleton translation manager instance."""
    return _global_translation_manager


def set_translation_manager(mgr: TranslationManager) -> None:
    """Overrides the global translation manager (useful for tests)."""
    global _global_translation_manager
    _global_translation_manager = mgr


def gettext(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    """Global gettext wrapper."""
    return _global_translation_manager.gettext(key, lang=lang, **kwargs)


# Shorthand alias standard for gettext
_ = gettext


def init_i18n(
    app: Flask, translation_manager: Optional[TranslationManager] = None
) -> None:
    """Registers Jinja2 context processors and template globals in Flask app."""
    if translation_manager is not None:
        set_translation_manager(translation_manager)

    mgr = _global_translation_manager

    @app.context_processor
    def inject_i18n() -> Dict[str, Any]:
        curr_lang = mgr.get_locale()
        return {
            "_": lambda key, **kw: mgr.gettext(key, lang=curr_lang, **kw),
            "current_locale": curr_lang,
            "supported_locales": SUPPORTED_LOCALES,
        }
