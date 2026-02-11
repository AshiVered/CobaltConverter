import logging
import threading

import wx

from cobalt_converter.conversion_handler import ConversionMixin
from cobalt_converter.converter import ConversionEngine
from cobalt_converter.dialogs import FileDropTarget
from cobalt_converter.ffmpeg_handler import FFmpegDownloadMixin
from cobalt_converter.file_handling import FileHandlingMixin
from cobalt_converter.quality_manager import QualityManager
from cobalt_converter.settings_manager import SettingsManager
from cobalt_converter.translator import Translator
from cobalt_converter.ui_builder import UIBuilderMixin
from cobalt_converter.utils import detect_system_language, set_debug_mode, setup_logging


class CobaltConverterFrame(
    UIBuilderMixin,
    FileHandlingMixin,
    ConversionMixin,
    FFmpegDownloadMixin,
    wx.Frame,
):
    def __init__(self, settings: SettingsManager) -> None:
        super().__init__(None, title="CobaltConverter", size=(700, 520))
        self.SetMinSize((650, 450))

        self.settings = settings
        self.files: list[str] = []
        self.is_converting = False
        self.stop_requested = False
        self.output_folder: str | None = None
        self.translator = Translator()
        self.quality_manager = QualityManager()

        self.dialog_event = threading.Event()
        self.dialog_result: str | None = None
        self._pending_conversion_after_download = False

        self.engine = ConversionEngine(
            progress_callback=lambda cur, total: wx.CallAfter(self._set_file_progress, cur, total),
            status_callback=lambda msg: wx.CallAfter(self._set_status, msg),
            incompatible_callback=self._request_format_from_user,
            finished_callback=lambda: wx.CallAfter(self._conversion_finished),
        )

        self._build_menu_bar()
        self._build_ui()
        self.SetDropTarget(FileDropTarget(self))
        self.refresh_ffmpeg_cache()

        detected = detect_system_language()
        display = "עברית" if detected == "he" else "English"
        self.language_choice.SetStringSelection(display)
        self.change_language(display)

        self.Centre()
        self.Show()

    def _build_menu_bar(self) -> None:
        self._menu_bar = wx.MenuBar()

        self._settings_menu = wx.Menu()
        self._debug_menu_item = self._settings_menu.AppendCheckItem(wx.ID_ANY, "Debug Mode")
        self._debug_menu_item.Check(self.settings.debug)
        self.Bind(wx.EVT_MENU, self._on_toggle_debug, self._debug_menu_item)

        self._menu_bar.Append(self._settings_menu, "&Settings")
        self.SetMenuBar(self._menu_bar)

    def _on_toggle_debug(self, _event: wx.CommandEvent) -> None:
        enabled = self._debug_menu_item.IsChecked()
        self.settings.debug = enabled
        set_debug_mode(enabled)
        self._retranslate_ui()
        logging.info("Debug mode toggled to %s via UI", enabled)

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


def main(debug: bool = False) -> None:
    settings = SettingsManager()
    effective_debug = debug or settings.debug

    log_path = setup_logging(debug=effective_debug)
    logging.info("Starting CobaltConverter (debug=%s, log=%s)", effective_debug, log_path)

    app = wx.App(False)
    frame = CobaltConverterFrame(settings)
    frame.Bind(wx.EVT_CLOSE, frame.on_close)
    app.MainLoop()
