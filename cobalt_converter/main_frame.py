import logging
import os
import pathlib
import threading

import wx

from cobalt_converter.constants import (
    AUDIO_FORMATS,
    IMAGE_FORMATS,
    VIDEO_FORMATS,
    get_file_type,
)
from cobalt_converter.converter import ConversionEngine
from cobalt_converter.dialogs import FileDropTarget, IncompatibleFileDialog
from cobalt_converter.exceptions.ffmpeg_exceptions import (
    FFmpegDownloadError,
    FFmpegExtractionError,
    UnsupportedPlatformError,
)
from cobalt_converter.ffmpeg.resolver import FFmpegResolver
from cobalt_converter.translator import Translator
from cobalt_converter.utils import (
    detect_system_language,
    get_base_path,
    get_ffmpeg_version,
    setup_logging,
)

LOG_PATH = setup_logging()


class CobaltConverterFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="CobaltConverter", size=(700, 520))
        self.SetMinSize((650, 450))

        self.files: list[str] = []
        self.is_converting = False
        self.stop_requested = False
        self.output_folder: str | None = None
        self.translator = Translator()

        self.dialog_event = threading.Event()
        self.dialog_result: str | None = None

        self.engine = ConversionEngine(
            progress_callback=lambda cur, total: wx.CallAfter(self._set_file_progress, cur, total),
            status_callback=lambda msg: wx.CallAfter(self._set_status, msg),
            incompatible_callback=self._request_format_from_user,
            finished_callback=lambda: wx.CallAfter(self._conversion_finished),
        )

        self._build_ui()
        self.SetDropTarget(FileDropTarget(self))

        detected = detect_system_language()
        display = "עברית" if detected == "he" else "English"
        self.language_choice.SetStringSelection(display)
        self.change_language(display)

        self.Centre()
        self.Show()

    # --- UI Construction ---
    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(main_sizer)
        main_sizer.SetMinSize((600, 400))

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.select_btn = wx.Button(panel)
        self.select_btn.Bind(wx.EVT_BUTTON, lambda e: self.select_files())
        top_sizer.Add(self.select_btn, 0, wx.RIGHT, 6)

        self.clear_btn = wx.Button(panel)
        self.clear_btn.Bind(wx.EVT_BUTTON, lambda e: self.clear_files())
        top_sizer.Add(self.clear_btn, 0, wx.RIGHT, 6)

        top_sizer.AddStretchSpacer(1)

        self.language_label = wx.StaticText(panel)
        top_sizer.Add(self.language_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.language_choice = wx.ComboBox(panel, choices=["English", "עברית"], style=wx.CB_READONLY)
        self.language_choice.Bind(wx.EVT_COMBOBOX, lambda e: self.change_language(self.language_choice.GetValue()))
        top_sizer.Add(self.language_choice, 0)

        main_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        self.scroll.SetScrollRate(5, 5)
        self.list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.list_sizer)
        self.list_sizer.AddStretchSpacer(1)
        main_sizer.Add(self.scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.drag_hint = wx.StaticText(panel)
        self.drag_hint.Wrap(600)
        self.drag_hint.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(self.drag_hint, 0, wx.EXPAND | wx.ALL, 6)

        out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.use_custom_output = wx.CheckBox(panel)
        self.use_custom_output.Bind(wx.EVT_CHECKBOX, self._toggle_output_folder)
        out_sizer.Add(self.use_custom_output, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.output_folder_edit = wx.TextCtrl(panel)
        self.output_folder_edit.Enable(False)
        out_sizer.Add(self.output_folder_edit, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.browse_output_btn = wx.Button(panel)
        self.browse_output_btn.Bind(wx.EVT_BUTTON, lambda e: self._select_output_folder())
        self.browse_output_btn.Enable(False)
        out_sizer.Add(self.browse_output_btn, 0)

        main_sizer.Add(out_sizer, 0, wx.EXPAND | wx.ALL, 8)

        format_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.format_label = wx.StaticText(panel)
        format_sizer.Add(self.format_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.format_combo = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        self.format_combo.SetMinSize((150, -1))
        format_sizer.Add(self.format_combo, 0, wx.RIGHT, 6)
        format_sizer.AddStretchSpacer(1)
        main_sizer.Add(format_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.progress_bar = wx.Gauge(panel, range=100)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 8)
        self.status_label = wx.StaticText(panel, label="")
        main_sizer.Add(self.status_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.convert_btn = wx.Button(panel)
        self.convert_btn.Bind(wx.EVT_BUTTON, lambda e: self.start_conversion())
        self.convert_btn.SetMinSize((-1, 35))
        btn_sizer.Add(self.convert_btn, 0, wx.RIGHT, 6)

        self.stop_btn = wx.Button(panel)
        self.stop_btn.Bind(wx.EVT_BUTTON, lambda e: self._stop_conversion())
        self.stop_btn.Enable(False)
        self.stop_btn.SetMinSize((-1, 35))
        btn_sizer.Add(self.stop_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_LEFT | wx.ALL, 8)

        footer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.footer_label = wx.StaticText(panel)
        self.footer_label.SetForegroundColour(wx.Colour(128, 128, 128))
        footer_sizer.AddStretchSpacer(1)
        footer_sizer.Add(self.footer_label, 0, wx.ALIGN_CENTER_VERTICAL)
        footer_sizer.AddStretchSpacer(1)
        main_sizer.Add(footer_sizer, 0, wx.EXPAND | wx.ALL, 4)

        self._retranslate_ui()

    # --- Language ---
    def change_language(self, lang_name: str) -> None:
        lang_code = "he" if lang_name == "עברית" else "en"
        self.translator.set_language(lang_code)
        try:
            if lang_code == "he":
                self.SetLayoutDirection(wx.Layout_RightToLeft)
            else:
                self.SetLayoutDirection(wx.Layout_LeftToRight)
        except AttributeError:
            pass
        self._retranslate_ui()
        self.Layout()

    def _retranslate_ui(self) -> None:
        t = self.translator
        self.SetTitle(t.get("window_title"))
        self.select_btn.SetLabel(t.get("select_files_btn"))
        self.clear_btn.SetLabel(t.get("clear_btn"))
        self.drag_hint.SetLabel(t.get("drag_drop_hint"))
        self.use_custom_output.SetLabel(t.get("custom_output_checkbox"))
        self.output_folder_edit.SetHint(t.get("output_folder_placeholder"))
        self.browse_output_btn.SetLabel(t.get("browse_btn"))
        self.format_label.SetLabel(t.get("convert_to_label"))
        self.convert_btn.SetLabel(t.get("convert_now_btn"))
        self.stop_btn.SetLabel(t.get("stop_btn"))
        self.language_label.SetLabel(t.get("language_label"))

        ffmpeg_path = self.engine.get_ffmpeg_path()
        ffmpeg_version = get_ffmpeg_version(ffmpeg_path)
        footer_text = t.get("footer")
        if ffmpeg_version:
            footer_text += f"  |  FFmpeg {ffmpeg_version}"
        else:
            footer_text += f"  |  FFmpeg: {t.get('ffmpeg_not_installed')}"
        self.footer_label.SetLabel(footer_text)

        if not self.is_converting:
            current_status = self.status_label.GetLabel()
            if current_status in ["", t.get("status_ready")]:
                self.status_label.SetLabel(t.get("status_ready"))

    # --- File Handling ---
    def select_files(self) -> None:
        title = self.translator.get("select_files_dialog_title")
        with wx.FileDialog(self, message=title, wildcard="All files (*.*)|*.*",
                           style=wx.FD_OPEN | wx.FD_MULTIPLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.add_files(dlg.GetPaths())

    def add_files(self, files_to_add: list[str]) -> None:
        if self.is_converting:
            return
        added = False
        for file in files_to_add:
            if file not in self.files and os.path.isfile(file):
                self.files.append(file)
                self._add_file_item(file)
                added = True
        if self.files:
            self._update_format_options()
            self.status_label.SetLabel(
                self.translator.get("files_selected_status", count=len(self.files))
            )
        if added:
            self.list_sizer.Layout()
            self.scroll.FitInside()

    def _add_file_item(self, file_path: str) -> None:
        panel = wx.Panel(self.scroll)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, label=os.path.basename(file_path))
        label.SetToolTip(file_path)
        sizer.Add(label, 1, wx.ALL | wx.EXPAND, 4)

        remove_btn = wx.Button(panel, label="X", size=(28, 24))
        remove_btn.SetForegroundColour(wx.Colour(255, 0, 0))
        remove_btn.Bind(wx.EVT_BUTTON, lambda ev, f=file_path, p=panel: self._remove_file(f, p))
        sizer.Add(remove_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        panel.SetSizer(sizer)

        panel.file_path = file_path
        self.list_sizer.Insert(self.list_sizer.GetItemCount() - 1, panel, 0, wx.EXPAND | wx.ALL, 2)

    def _remove_file(self, file_to_remove: str, panel: wx.Panel | None = None) -> None:
        if self.is_converting:
            wx.MessageBox(
                self.translator.get("cannot_remove_file_message"),
                self.translator.get("cannot_remove_file_title"),
                wx.ICON_WARNING,
            )
            return
        try:
            self.files.remove(file_to_remove)
            if panel is not None:
                self.list_sizer.Hide(panel)
                panel.Destroy()
            else:
                for child in self.scroll.GetChildren():
                    if getattr(child, "file_path", None) == file_to_remove:
                        child.Destroy()
                        break
            if self.files:
                self.status_label.SetLabel(
                    self.translator.get("files_selected_status", count=len(self.files))
                )
            else:
                self.status_label.SetLabel(self.translator.get("status_ready"))
            self._update_format_options()
            self.list_sizer.Layout()
            self.scroll.FitInside()
        except ValueError:
            pass

    def clear_files(self) -> None:
        if self.is_converting:
            return
        self.files.clear()
        for child in list(self.scroll.GetChildren()):
            if hasattr(child, "file_path"):
                child.Destroy()
        self.format_combo.Clear()
        self.status_label.SetLabel(self.translator.get("status_ready"))
        self.progress_bar.SetValue(0)
        self.list_sizer.Layout()
        self.scroll.FitInside()

    def _update_format_options(self) -> None:
        if not self.files:
            self.format_combo.Clear()
            return
        current_selection = self.format_combo.GetValue()
        file_type = get_file_type(self.files[0])
        formats: list[str] = []
        if file_type == "video":
            formats = VIDEO_FORMATS + AUDIO_FORMATS
        elif file_type == "audio":
            formats = AUDIO_FORMATS
        elif file_type == "image":
            formats = IMAGE_FORMATS
        self.format_combo.Clear()
        for f in formats:
            self.format_combo.Append(f)
        if current_selection and current_selection in formats:
            self.format_combo.SetValue(current_selection)

    def _toggle_output_folder(self, _event: wx.CommandEvent) -> None:
        enabled = self.use_custom_output.GetValue()
        self.output_folder_edit.Enable(enabled)
        self.browse_output_btn.Enable(enabled)
        if not enabled:
            self.output_folder = None
            self.output_folder_edit.SetValue("")

    def _select_output_folder(self) -> None:
        title = self.translator.get("select_output_folder_dialog_title")
        with wx.DirDialog(self, message=title) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.output_folder = dlg.GetPath()
                self.output_folder_edit.SetValue(self.output_folder)

    # --- Conversion ---
    def start_conversion(self) -> None:
        if not self.files:
            wx.MessageBox(self.translator.get("no_files_message"), self.translator.get("no_files_title"), wx.ICON_WARNING)
            return
        if not self.format_combo.GetValue():
            wx.MessageBox(self.translator.get("no_format_message"), self.translator.get("no_format_title"), wx.ICON_WARNING)
            return
        if not self.engine.get_ffmpeg_path():
            self._offer_ffmpeg_download()
            if not self.engine.get_ffmpeg_path():
                return

        self.is_converting = True
        self.stop_requested = False
        self.convert_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.select_btn.Enable(False)
        self.clear_btn.Enable(False)
        self.progress_bar.SetValue(0)

        self.engine.start(
            files=self.files.copy(),
            output_format=self.format_combo.GetValue(),
            output_folder=self.output_folder,
        )

    def _stop_conversion(self) -> None:
        title = self.translator.get("stop_conversion_title")
        message = self.translator.get("stop_conversion_message")
        if wx.MessageBox(message, title, wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.stop_requested = True
            self.engine.stop()
            if not self.dialog_event.is_set():
                self.dialog_event.set()
            wx.CallAfter(self._set_status, self.translator.get("conversion_stopped_status"))

    def _request_format_from_user(self, file_path: str, valid_formats: list[str]) -> str | None:
        self.dialog_result = None
        self.dialog_event.clear()
        wx.CallAfter(self._show_incompatible_dialog, file_path, valid_formats)
        self.dialog_event.wait()
        return self.dialog_result

    # --- GUI Helpers ---
    def _set_progress(self, value: int) -> None:
        self.progress_bar.SetValue(value)

    def _set_status(self, message: str) -> None:
        self.status_label.SetLabel(message)

    def _set_file_progress(self, current: int, total: int) -> None:
        if total > 0:
            self.progress_bar.SetValue(int((current / total) * 100))

    def _conversion_finished(self) -> None:
        self.is_converting = False
        self.convert_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.select_btn.Enable(True)
        self.clear_btn.Enable(True)
        if not self.engine.stop_requested and self.files:
            self.progress_bar.SetValue(100)
            self._set_status(self.translator.get("all_conversions_complete_status"))
        self._retranslate_ui()

    # --- Dialogs ---
    def _show_incompatible_dialog(self, file_path: str, valid_formats: list[str]) -> None:
        dlg = IncompatibleFileDialog(self, file_path, valid_formats, self.translator)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            self.dialog_result = dlg.get_selected_format()
        else:
            self.dialog_result = None
        dlg.Destroy()
        self.dialog_event.set()

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

    # --- FFmpeg Auto-Download ---
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
            self._run_ffmpeg_download()
        elif result == wx.ID_NO:
            self._prompt_for_ffmpeg_path()

    def _run_ffmpeg_download(self) -> None:
        self.is_converting = True
        self.convert_btn.Enable(False)
        self.select_btn.Enable(False)
        self.clear_btn.Enable(False)
        self.progress_bar.SetValue(0)
        self._set_status(self.translator.get("ffmpeg_downloading_status"))

        self.dialog_event.clear()
        threading.Thread(target=self._download_ffmpeg_thread, daemon=True).start()
        self.dialog_event.wait()

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
        self.dialog_event.set()

    # --- Close ---
    def on_close(self, event: wx.CloseEvent) -> None:
        if self.is_converting:
            title = self.translator.get("conversion_in_progress_title")
            message = self.translator.get("conversion_in_progress_message")
            if wx.MessageBox(message, title, wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
                self.engine.stop()
                if not self.dialog_event.is_set():
                    self.dialog_event.set()
                self.Destroy()
            else:
                event.Veto()
        else:
            self.Destroy()


def main() -> None:
    app = wx.App(False)
    frame = CobaltConverterFrame()
    frame.Bind(wx.EVT_CLOSE, frame.on_close)
    app.MainLoop()
