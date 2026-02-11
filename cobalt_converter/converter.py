import logging
import os
import pathlib
import subprocess
import sys
import threading
from collections.abc import Callable

from cobalt_converter.constants import (
    AUDIO_FORMATS,
    IMAGE_FORMATS,
    VIDEO_FORMATS,
    get_file_type,
)
from cobalt_converter.utils import get_base_path, get_subprocess_flags


class ConversionEngine:
    def __init__(
        self,
        progress_callback: Callable[[int, int], None],
        status_callback: Callable[[str], None],
        incompatible_callback: Callable[[str, list[str]], str | None],
        finished_callback: Callable[[], None],
    ) -> None:
        self._progress_callback = progress_callback
        self._status_callback = status_callback
        self._incompatible_callback = incompatible_callback
        self._finished_callback = finished_callback
        self._stop_requested = False
        self._current_process: subprocess.Popen | None = None
        self.custom_ffmpeg_path: str | None = None

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    def get_ffmpeg_path(self) -> str | None:
        if self.custom_ffmpeg_path and os.path.isfile(self.custom_ffmpeg_path):
            return self.custom_ffmpeg_path
        ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        local_path = os.path.join(get_base_path(), "bin", ffmpeg_name)
        if os.path.isfile(local_path):
            return local_path
        try:
            subprocess.run(
                [ffmpeg_name, "-version"],
                capture_output=True,
                **get_subprocess_flags(),
            )
            return ffmpeg_name
        except FileNotFoundError:
            return None

    def start(
        self,
        files: list[str],
        output_format: str,
        output_folder: str | None,
        quality_flags: list[str] | None = None,
    ) -> None:
        self._stop_requested = False
        threading.Thread(
            target=self._convert_all,
            args=(files, output_format, output_folder, quality_flags or []),
            daemon=True,
        ).start()

    def stop(self) -> None:
        self._stop_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
            except OSError:
                pass

    def _convert_all(self, files: list[str], initial_format: str, output_folder: str | None, quality_flags: list[str] | None = None) -> None:
        quality_flags = quality_flags or []
        ffmpeg_path = self.get_ffmpeg_path()
        total = len(files)
        processed = 0

        for file in files:
            if self._stop_requested:
                break

            current_format = self._resolve_format(file, initial_format)
            if current_format is None:
                self._status_callback(f"Skipping {os.path.basename(file)}")
                processed += 1
                self._progress_callback(processed, total)
                continue

            output_file = self._build_output_path(file, current_format, output_folder)

            if os.path.exists(output_file):
                processed += 1
                self._progress_callback(processed, total)
                continue

            self._status_callback(f"Converting ({processed + 1}/{total}): {os.path.basename(file)}...")
            logging.info("Starting conversion for %s", file)
            self._run_ffmpeg(ffmpeg_path, file, output_file, quality_flags)

            if not self._stop_requested:
                processed += 1
                self._progress_callback(processed, total)

        if not self._stop_requested:
            logging.info("All conversions complete.")

        self._finished_callback()

    def _resolve_format(self, file: str, initial_format: str) -> str | None:
        file_type = get_file_type(file)
        valid_formats: list[str] = []
        if file_type == "video":
            valid_formats = VIDEO_FORMATS + AUDIO_FORMATS
        elif file_type == "audio":
            valid_formats = AUDIO_FORMATS
        elif file_type == "image":
            valid_formats = IMAGE_FORMATS

        if initial_format in valid_formats:
            return initial_format

        return self._incompatible_callback(file, valid_formats)

    @staticmethod
    def _build_output_path(file: str, output_format: str, output_folder: str | None) -> str:
        if output_folder:
            output_filename = pathlib.Path(file).stem + f".{output_format}"
            return os.path.join(output_folder, output_filename)
        return str(pathlib.Path(file).with_suffix(f".{output_format}"))

    def _run_ffmpeg(self, ffmpeg_path: str, input_file: str, output_file: str, quality_flags: list[str] | None = None) -> None:
        try:
            cmd = [ffmpeg_path, "-y", "-i", input_file] + (quality_flags or []) + [output_file]
            logging.info("Running command: %s", " ".join(cmd))

            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                universal_newlines=True,
                **get_subprocess_flags(),
            )

            for line in self._current_process.stdout:
                line = line.strip()
                if line:
                    logging.debug(line)
                    if "frame=" in line or "time=" in line:
                        self._status_callback(f"FFmpeg: {line[:80]}")

            self._current_process.wait()

            rc = self._current_process.returncode
            if rc != 0:
                logging.error("FFmpeg exited with code %d", rc)
            else:
                logging.info("FFmpeg finished successfully for %s", input_file)

        except OSError as e:
            logging.exception("Exception during FFmpeg run: %s", e)
        finally:
            self._current_process = None
