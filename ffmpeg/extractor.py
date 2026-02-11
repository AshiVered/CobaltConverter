import logging
import os
import pathlib
import stat
import subprocess
import sys
import tarfile
import zipfile

from exceptions.ffmpeg_exceptions import FFmpegExtractionError


def extract_ffmpeg_binary(
    archive_path: pathlib.Path,
    binary_path_in_archive: str,
    destination_dir: pathlib.Path,
    binary_name: str,
    archive_type: str,
) -> pathlib.Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / binary_name

    logging.info("Extracting %s from %s", binary_path_in_archive, archive_path)

    if archive_type == "zip":
        _extract_from_zip(archive_path, binary_path_in_archive, output_path)
    elif archive_type == "tar.xz":
        _extract_from_tar_xz(archive_path, binary_path_in_archive, output_path)
    else:
        raise FFmpegExtractionError(f"Unsupported archive type: {archive_type}")

    if sys.platform != "win32":
        _set_executable(output_path)

    archive_path.unlink()
    logging.info("Archive deleted: %s", archive_path)

    _verify_binary(output_path)
    logging.info("FFmpeg binary verified at %s", output_path)

    return output_path


def _extract_from_zip(
    archive_path: pathlib.Path,
    binary_path_in_archive: str,
    output_path: pathlib.Path,
) -> None:
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            if binary_path_in_archive not in zf.namelist():
                raise FFmpegExtractionError(
                    f"Binary '{binary_path_in_archive}' not found in archive"
                )
            with zf.open(binary_path_in_archive) as src, open(output_path, "wb") as dst:
                dst.write(src.read())
    except zipfile.BadZipFile as e:
        raise FFmpegExtractionError(f"Corrupt zip archive: {e}") from e


def _extract_from_tar_xz(
    archive_path: pathlib.Path,
    binary_path_in_archive: str,
    output_path: pathlib.Path,
) -> None:
    try:
        with tarfile.open(archive_path, "r:xz") as tf:
            member = tf.getmember(binary_path_in_archive)
            extracted = tf.extractfile(member)
            if extracted is None:
                raise FFmpegExtractionError(
                    f"Cannot extract '{binary_path_in_archive}' from archive"
                )
            with open(output_path, "wb") as dst:
                dst.write(extracted.read())
    except tarfile.TarError as e:
        raise FFmpegExtractionError(f"Corrupt tar archive: {e}") from e
    except KeyError:
        raise FFmpegExtractionError(
            f"Binary '{binary_path_in_archive}' not found in archive"
        )


def _set_executable(path: pathlib.Path) -> None:
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    logging.debug("Set executable permission on %s", path)


def _verify_binary(path: pathlib.Path) -> None:
    try:
        result = subprocess.run(
            [str(path), "-version"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            path.unlink(missing_ok=True)
            raise FFmpegExtractionError("FFmpeg binary verification failed (non-zero exit code)")
    except FileNotFoundError:
        raise FFmpegExtractionError("Extracted file is not a valid executable")
    except subprocess.TimeoutExpired:
        path.unlink(missing_ok=True)
        raise FFmpegExtractionError("FFmpeg binary verification timed out")
