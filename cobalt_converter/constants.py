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
APP_NAME: str = _CONFIG["app_name"]
APP_VERSION: str = _CONFIG["app_version"]
APP_AUTHOR: str = _CONFIG["app_author"]
APP_AUTHOR_HE: str = _CONFIG["app_author_he"]
WINDOW_WIDTH: int = _CONFIG["window_width"]
WINDOW_HEIGHT: int = _CONFIG["window_height"]
WINDOW_MIN_WIDTH: int = _CONFIG["window_min_width"]
WINDOW_MIN_HEIGHT: int = _CONFIG["window_min_height"]


def get_file_type(file_path: str) -> str:
    ext = pathlib.Path(file_path).suffix.lower().lstrip(".")
    if ext in VIDEO_FORMATS:
        return "video"
    if ext in AUDIO_FORMATS:
        return "audio"
    if ext in IMAGE_FORMATS:
        return "image"
    return "unknown"
