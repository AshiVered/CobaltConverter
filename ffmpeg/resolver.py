import json
import logging
import pathlib
import shutil
from collections.abc import Callable

from exceptions.ffmpeg_exceptions import (
    FFmpegDownloadError,
    FFmpegExtractionError,
    UnsupportedPlatformError,
)
from ffmpeg.downloader import download_file
from ffmpeg.extractor import extract_ffmpeg_binary
from ffmpeg.platform_info import get_platform_key


class FFmpegResolver:
    def __init__(
        self,
        bin_dir: pathlib.Path,
        config_path: pathlib.Path,
        progress_callback: Callable[[int, int], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._bin_dir = bin_dir
        self._config = self._load_config(config_path)
        self._progress_callback = progress_callback
        self._status_callback = status_callback

    def resolve(self) -> pathlib.Path:
        platform_key = get_platform_key()
        source_key = self._config["platform_map"].get(platform_key)

        if not source_key:
            raise UnsupportedPlatformError(f"No FFmpeg source for platform: {platform_key}")

        source = self._config["sources"][source_key]
        binary_name = source["binary_name"]

        cached = self._bin_dir / binary_name
        if cached.is_file():
            logging.info("Found cached FFmpeg at %s", cached)
            return cached

        system_path = shutil.which("ffmpeg")
        if system_path:
            logging.info("Found FFmpeg on system PATH: %s", system_path)
            return pathlib.Path(system_path)

        return self._download_and_extract(source)

    def _download_and_extract(self, source: dict) -> pathlib.Path:
        url = source["url"]
        archive_type = source["archive_type"]
        extension = ".zip" if archive_type == "zip" else ".tar.xz"
        archive_path = self._bin_dir / f"ffmpeg_download{extension}"

        self._cleanup_partial(archive_path)

        if self._status_callback:
            self._status_callback("Downloading FFmpeg...")

        downloaded = download_file(
            url=url,
            destination=archive_path,
            progress_callback=self._progress_callback,
            timeout=30,
        )

        if self._status_callback:
            self._status_callback("Extracting FFmpeg...")

        return extract_ffmpeg_binary(
            archive_path=downloaded,
            binary_path_in_archive=source["binary_path_in_archive"],
            destination_dir=self._bin_dir,
            binary_name=source["binary_name"],
            archive_type=archive_type,
        )

    @staticmethod
    def _load_config(config_path: pathlib.Path) -> dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as e:
            raise FFmpegDownloadError(f"Config file not found: {config_path}") from e
        except json.JSONDecodeError as e:
            raise FFmpegDownloadError(f"Invalid config JSON: {e}") from e

    @staticmethod
    def _cleanup_partial(archive_path: pathlib.Path) -> None:
        part_path = archive_path.with_suffix(archive_path.suffix + ".part")
        if part_path.exists():
            part_path.unlink()
            logging.info("Removed partial download: %s", part_path)
