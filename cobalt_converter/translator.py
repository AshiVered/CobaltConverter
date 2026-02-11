import json
import os

from cobalt_converter.utils import get_base_path


class Translator:
    def __init__(self, initial_language: str = "en") -> None:
        self.language = initial_language
        self.translations: dict[str, dict[str, str]] = {}
        self._load_languages()

    def _load_languages(self) -> None:
        base_path = os.path.join(get_base_path(), "cobalt_converter", "Languages")
        if not os.path.exists(base_path):
            return

        for filename in os.listdir(base_path):
            if filename.endswith(".json"):
                lang_code = os.path.splitext(filename)[0].lower()
                file_path = os.path.join(base_path, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass

    def set_language(self, lang_code: str) -> None:
        if lang_code in self.translations:
            self.language = lang_code

    def get(self, key: str, **kwargs: str | int | float) -> str:
        try:
            template = self.translations[self.language][key]
            return template.format(**kwargs) if kwargs else template
        except KeyError:
            try:
                template = self.translations.get("en", {}).get(key, key)
                return template.format(**kwargs) if kwargs else template
            except (KeyError, IndexError):
                return key
