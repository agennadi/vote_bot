import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Translator:
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = translations_dir
        self.translations: Dict[str, Dict[str, str]] = {}
        self.load_translations()

    def load_translations(self):
        """Load all translation files from the translations directory."""
        try:
            for filename in os.listdir(self.translations_dir):
                if filename.endswith('.json'):
                    lang_code = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(self.translations_dir, filename)

                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)

                    logger.info(
                        f"Loaded translations for language: {lang_code}")
        except Exception as e:
            logger.error(f"Error loading translations: {e}")

    def get_user_language(self, user) -> str:
        """
        Get user's preferred language from Telegram user object.
        Falls back to 'en' if no language is specified.
        """
        if hasattr(user, 'language_code') and user.language_code:
            # Extract language code (e.g., 'ru' from 'ru-RU')
            lang_code = user.language_code.split('-')[0].lower()
            if lang_code in self.translations:
                return lang_code

        return 'en'  # Default to English

    def translate(self, key: str, user=None, **kwargs) -> str:
        """
        Translate a message key for a specific user.

        Args:
            key: Translation key
            user: Telegram user object (optional)
            **kwargs: Format parameters for the translation string

        Returns:
            Translated string
        """
        if user:
            lang_code = self.get_user_language(user)
        else:
            lang_code = 'en'

        # Get translation
        translation = self.translations.get(lang_code, {}).get(key, key)

        # Format with parameters if provided
        try:
            if kwargs:
                return translation.format(**kwargs)
            return translation
        except KeyError as e:
            logger.warning(
                f"Missing format parameter {e} for key '{key}' in language '{lang_code}'")
            return translation

    def get_available_languages(self) -> list[str]:
        """Get list of available language codes."""
        return list(self.translations.keys())


# Global translator instance
translator = Translator()
