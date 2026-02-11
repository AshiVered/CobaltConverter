import locale
import logging
import os
import re
import subprocess
import sys

from cobalt_converter.constants import LANGUAGES


def get_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup_logging() -> str:
    base_path = get_base_path()
    log_path = os.path.join(base_path, "CobaltConverter.log")
    try:
        if os.path.exists(log_path):
            os.remove(log_path)
    except OSError:
        pass

    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    logging.info("Logging initialized. Log file: %s", log_path)
    return log_path


def get_subprocess_flags() -> dict:
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}
    return {}


def detect_system_language() -> str:
    if sys.platform == "win32":
        try:
            import ctypes

            windll = ctypes.windll.kernel32
            lcid = windll.GetUserDefaultUILanguage()
            lang_name = locale.windows_locale.get(lcid)
            if lang_name:
                primary_lang = lang_name.split("_")[0].lower()
                if primary_lang in LANGUAGES:
                    return primary_lang
        except (OSError, AttributeError):
            pass
    else:
        lang_code = os.environ.get("LANG")
        if lang_code:
            primary_lang = lang_code.split("_")[0].lower()
            if primary_lang in LANGUAGES:
                return primary_lang
    return "en"


def get_ffmpeg_version(ffmpeg_path: str | None) -> str | None:
    if not ffmpeg_path:
        return None
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            **get_subprocess_flags(),
        )
        if result.returncode == 0:
            first_line = result.stdout.split("\n")[0]
            match = re.search(r"ffmpeg version (\S+)", first_line)
            if match:
                return match.group(1)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None
