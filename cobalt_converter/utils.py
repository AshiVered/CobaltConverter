import json
import locale
import logging
import os
import platform
import re
import subprocess
import sys

from cobalt_converter.constants import LANGUAGES

_debug_mode = False


def is_debug_mode() -> bool:
    return _debug_mode


def set_debug_mode(debug: bool) -> None:
    global _debug_mode
    _debug_mode = debug

    root_logger = logging.getLogger()
    new_level = logging.DEBUG if debug else logging.INFO

    root_logger.setLevel(new_level)
    for handler in root_logger.handlers:
        handler.setLevel(new_level)

    if debug:
        has_console = any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
            for h in root_logger.handlers
        )
        if not has_console:
            config_path = os.path.join(os.path.dirname(__file__), "config", "logging.json")
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(logging.Formatter(config["format"], config["date_format"]))
            root_logger.addHandler(console_handler)
        _log_system_info()
    else:
        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                root_logger.removeHandler(handler)

    logging.info("Debug mode %s", "enabled" if debug else "disabled")
    _flush_all_handlers()


def _flush_all_handlers() -> None:
    for handler in logging.getLogger().handlers:
        handler.flush()


def get_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup_logging(debug: bool = False) -> str:
    global _debug_mode
    _debug_mode = debug

    config_path = os.path.join(os.path.dirname(__file__), "config", "logging.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    base_path = get_base_path()
    log_path = os.path.join(base_path, config["log_filename"])

    try:
        if os.path.exists(log_path):
            os.remove(log_path)
    except OSError:
        pass

    level = config["debug_level"] if debug else config["default_level"]

    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=getattr(logging, level),
        format=config["format"],
        datefmt=config["date_format"],
        encoding="utf-8",
    )

    if debug:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(config["format"], config["date_format"]))
        logging.getLogger().addHandler(console_handler)

    logging.info("Logging initialized (level=%s). Log file: %s", level, log_path)

    if debug:
        _log_system_info()

    _flush_all_handlers()
    return log_path


def _log_system_info() -> None:
    logging.debug("=== System Information (DEBUG mode) ===")
    logging.debug("OS: %s %s", platform.system(), platform.release())
    logging.debug("OS Version: %s", platform.version())
    logging.debug("Architecture: %s", platform.machine())
    logging.debug("Platform: %s", platform.platform())
    logging.debug("Python: %s", sys.version)
    logging.debug("Python Path: %s", sys.executable)
    logging.debug("Working Directory: %s", os.getcwd())
    logging.debug("Base Path: %s", get_base_path())
    logging.debug("Frozen: %s", getattr(sys, "frozen", False))

    try:
        import wx as wx_module
        logging.debug("wxPython: %s", wx_module.version())
    except ImportError:
        logging.debug("wxPython: not installed")

    ffmpeg_path = _find_ffmpeg_for_info()
    if ffmpeg_path:
        version = get_ffmpeg_version(ffmpeg_path)
        logging.debug("FFmpeg Path: %s", ffmpeg_path)
        logging.debug("FFmpeg Version: %s", version or "unknown")
    else:
        logging.debug("FFmpeg: not found")

    logging.debug("Locale: %s", locale.getdefaultlocale())
    logging.debug("LANG env: %s", os.environ.get("LANG", "not set"))
    logging.debug("========================================")


def _find_ffmpeg_for_info() -> str | None:
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    local_path = os.path.join(get_base_path(), "bin", ffmpeg_name)
    if os.path.isfile(local_path):
        return local_path
    try:
        subprocess.run([ffmpeg_name, "-version"], capture_output=True, **get_subprocess_flags())
        return ffmpeg_name
    except FileNotFoundError:
        return None


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
