import json
import os
import pathlib


def _load_formats() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", "formats.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


_CONFIG = _load_formats()

VIDEO_FORMATS: list[str] = _CONFIG["video"]
AUDIO_FORMATS: list[str] = _CONFIG["audio"]
IMAGE_FORMATS: list[str] = _CONFIG["image"]
LANGUAGES: dict[str, str] = _CONFIG["languages"]


def get_file_type(file_path: str) -> str:
    ext = pathlib.Path(file_path).suffix.lower().lstrip(".")
    if ext in VIDEO_FORMATS:
        return "video"
    if ext in AUDIO_FORMATS:
        return "audio"
    if ext in IMAGE_FORMATS:
        return "image"
    return "unknown"
