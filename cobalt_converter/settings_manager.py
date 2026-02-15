import json
import logging
import os

from cobalt_converter.utils import get_base_path

_SETTINGS_FILENAME = "settings.json"
_DEFAULTS: dict[str, bool | str] = {
    "debug": False,
}


class SettingsManager:
    def __init__(self) -> None:
        self._path = os.path.join(get_base_path(), _SETTINGS_FILENAME)
        self._data: dict[str, bool | str] = dict(_DEFAULTS)
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                self._data.update(stored)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning("Failed to load settings from %s: %s", self._path, e)

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logging.error("Failed to save settings to %s: %s", self._path, e)

    @property
    def debug(self) -> bool:
        return bool(self._data.get("debug", False))

    @debug.setter
    def debug(self, value: bool) -> None:
        self._data["debug"] = value
        self._save()
