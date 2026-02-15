import json
import logging
import os

class QualityManager:
    PRESET_KEYS = ["low", "medium", "high", "maximum"]

    def __init__(self) -> None:
        self._config = self._load_config()

    @staticmethod
    def _load_config() -> dict:
        config_path = os.path.join(os.path.dirname(__file__), "config", "quality_presets.json")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def lossless_formats(self) -> list[str]:
        return self._config.get("lossless_formats", [])

    def is_lossless(self, output_format: str) -> bool:
        return output_format in self.lossless_formats

    def get_presets_for_format(self, output_format: str) -> dict[str, list[str]]:
        overrides = self._config.get("format_overrides", {})
        if output_format in overrides and "presets" in overrides[output_format]:
            return overrides[output_format]["presets"]

        file_type = self._get_type_for_format(output_format)
        type_defaults = self._config.get("type_defaults", {})
        if file_type in type_defaults:
            return type_defaults[file_type].get("presets", {})
        return {}

    def get_custom_params(self, output_format: str) -> list[dict]:
        overrides = self._config.get("format_overrides", {})
        if output_format in overrides and "custom" in overrides[output_format]:
            return overrides[output_format]["custom"]

        file_type = self._get_type_for_format(output_format)
        type_defaults = self._config.get("type_defaults", {})
        if file_type in type_defaults:
            return type_defaults[file_type].get("custom", [])
        return []

    def build_preset_flags(self, output_format: str, preset_key: str) -> list[str]:
        if preset_key == "default" or self.is_lossless(output_format):
            return []
        presets = self.get_presets_for_format(output_format)
        flags = list(presets.get(preset_key, []))
        logging.debug("Preset flags for %s/%s: %s", output_format, preset_key, flags)
        return flags

    def build_custom_flags(self, output_format: str, values: dict[str, str | int]) -> list[str]:
        if self.is_lossless(output_format):
            return []
        params = self.get_custom_params(output_format)
        flags: list[str] = []
        for param in params:
            name = param["name"]
            if name in values:
                value = str(values[name])
                suffix = param.get("suffix", "")
                flags.extend([param["flag"], f"{value}{suffix}"])
        logging.debug("Custom flags for %s (values=%s): %s", output_format, values, flags)
        return flags

    @staticmethod
    def _get_type_for_format(output_format: str) -> str:
        from cobalt_converter.constants import AUDIO_FORMATS, IMAGE_FORMATS, VIDEO_FORMATS

        if output_format in VIDEO_FORMATS:
            return "video"
        if output_format in AUDIO_FORMATS:
            return "audio"
        if output_format in IMAGE_FORMATS:
            return "image"
        return "unknown"
