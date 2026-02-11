import logging
import os
import pathlib
import threading

import wx

from cobalt_converter.exceptions.ffmpeg_exceptions import (
    FFmpegDownloadError,
    FFmpegExtractionError,
    UnsupportedPlatformError,
)
from cobalt_converter.ffmpeg.resolver import FFmpegResolver
from cobalt_converter.utils import get_base_path


class FFmpegDownloadMixin:
    def _offer_ffmpeg_download(self) -> None:
        title = self.translator.get("ffmpeg_not_found_title")
        message = self.translator.get("ffmpeg_auto_download_offer")
        dialog = wx.MessageDialog(self, message, title, wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
        dialog.SetYesNoCancelLabels(
            self.translator.get("ffmpeg_download_btn"),
            self.translator.get("ffmpeg_locate_btn"),
            self.translator.get("cancel_btn"),
        )
        result = dialog.ShowModal()
        dialog.Destroy()

        if result == wx.ID_YES:
            self._pending_conversion_after_download = True
            self._run_ffmpeg_download()
        elif result == wx.ID_NO:
            self._prompt_for_ffmpeg_path()

    def _prompt_for_ffmpeg_path(self) -> None:
        title = self.translator.get("ffmpeg_not_found_title")
        message = self.translator.get("ffmpeg_not_found_message")
        if wx.MessageBox(message, title, wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            dialog_title = self.translator.get("locate_ffmpeg_dialog_title")
            with wx.FileDialog(self, message=dialog_title, style=wx.FD_OPEN) as filed:
                if filed.ShowModal() == wx.ID_OK:
                    path = filed.GetPath()
                    if path and os.path.isfile(path):
                        self.engine.custom_ffmpeg_path = path

    def _run_ffmpeg_download(self) -> None:
        self.is_converting = True
        self.convert_btn.Enable(False)
        self.select_btn.Enable(False)
        self.clear_btn.Enable(False)
        self.progress_bar.SetValue(0)
        self._set_status(self.translator.get("ffmpeg_downloading_status"))

        threading.Thread(target=self._download_ffmpeg_thread, daemon=True).start()

    def _download_ffmpeg_thread(self) -> None:
        try:
            resolver = FFmpegResolver(
                bin_dir=pathlib.Path(get_base_path()) / "bin",
                config_path=pathlib.Path(get_base_path()) / "cobalt_converter" / "config" / "ffmpeg_sources.json",
                progress_callback=lambda downloaded, total: wx.CallAfter(
                    self._set_download_progress, downloaded, total
                ),
                status_callback=lambda msg: wx.CallAfter(self._set_status, msg),
            )
            path = resolver.resolve()
            logging.info("FFmpeg downloaded and cached at: %s", path)
            wx.CallAfter(self._set_status, self.translator.get("ffmpeg_download_complete"))
        except UnsupportedPlatformError:
            logging.error("Unsupported platform for FFmpeg auto-download")
            wx.CallAfter(self._set_status, self.translator.get("ffmpeg_unsupported_platform"))
        except FFmpegDownloadError as e:
            logging.error("FFmpeg download failed: %s", e)
            wx.CallAfter(self._set_status, self.translator.get("ffmpeg_download_failed", error=str(e)))
        except FFmpegExtractionError as e:
            logging.error("FFmpeg extraction failed: %s", e)
            wx.CallAfter(self._set_status, self.translator.get("ffmpeg_extraction_failed", error=str(e)))
        finally:
            wx.CallAfter(self._download_finished)

    def _set_download_progress(self, bytes_downloaded: int, total_bytes: int) -> None:
        if total_bytes > 0:
            percentage = int((bytes_downloaded / total_bytes) * 100)
            self.progress_bar.SetValue(percentage)
            mb_downloaded = bytes_downloaded / (1024 * 1024)
            mb_total = total_bytes / (1024 * 1024)
            self.status_label.SetLabel(
                self.translator.get(
                    "ffmpeg_download_progress",
                    downloaded=f"{mb_downloaded:.1f}",
                    total=f"{mb_total:.1f}",
                )
            )
        else:
            self.progress_bar.Pulse()

    def _download_finished(self) -> None:
        self.is_converting = False
        self.convert_btn.Enable(True)
        self.select_btn.Enable(True)
        self.clear_btn.Enable(True)
        self._retranslate_ui()

        if self._pending_conversion_after_download and self.engine.get_ffmpeg_path():
            self._pending_conversion_after_download = False
            self.start_conversion()
        self._pending_conversion_after_download = False
