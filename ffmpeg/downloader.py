import logging
import pathlib
import urllib.request
import urllib.error
from collections.abc import Callable

from exceptions.ffmpeg_exceptions import FFmpegDownloadError

CHUNK_SIZE = 8192


def download_file(
    url: str,
    destination: pathlib.Path,
    progress_callback: Callable[[int, int], None] | None = None,
    timeout: int = 30,
) -> pathlib.Path:
    part_path = destination.with_suffix(destination.suffix + ".part")
    logging.info("Downloading %s to %s", url, destination)

    try:
        response = urllib.request.urlopen(url, timeout=timeout)
    except urllib.error.URLError as e:
        raise FFmpegDownloadError(f"Failed to connect: {e}") from e
    except urllib.error.HTTPError as e:
        raise FFmpegDownloadError(f"HTTP error {e.code}: {e.reason}") from e

    total_bytes = int(response.headers.get("Content-Length", 0))
    bytes_downloaded = 0

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        with open(part_path, "wb") as f:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                bytes_downloaded += len(chunk)
                if progress_callback:
                    progress_callback(bytes_downloaded, total_bytes)
                logging.debug("Downloaded %d / %d bytes", bytes_downloaded, total_bytes)

        part_path.rename(destination)
        logging.info("Download complete: %s (%d bytes)", destination, bytes_downloaded)
        return destination

    except OSError as e:
        if part_path.exists():
            part_path.unlink()
        raise FFmpegDownloadError(f"Failed to write file: {e}") from e
    finally:
        response.close()
