import pathlib

VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "gif"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

LANGUAGES = {"en": "English", "he": "עברית"}


def get_file_type(file_path: str) -> str:
    ext = pathlib.Path(file_path).suffix.lower().lstrip(".")
    if ext in VIDEO_FORMATS:
        return "video"
    if ext in AUDIO_FORMATS:
        return "audio"
    if ext in IMAGE_FORMATS:
        return "image"
    return "unknown"
