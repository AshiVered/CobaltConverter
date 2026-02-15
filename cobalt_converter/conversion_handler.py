import logging

import wx

from cobalt_converter.dialogs import IncompatibleFileDialog


class ConversionMixin:
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
                return  # async download will auto-start conversion when done

        self.is_converting = True
        self.stop_requested = False
        self.convert_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.select_btn.Enable(False)
        self.clear_btn.Enable(False)
        self.progress_bar.SetValue(0)

        quality_flags = self._build_quality_flags()
        output_format = self.format_combo.GetValue()

        logging.info(
            "Starting conversion: %d files, format=%s, quality_flags=%s",
            len(self.files), output_format, quality_flags,
        )

        self.engine.start(
            files=self.files.copy(),
            output_format=output_format,
            output_folder=self.output_folder,
            quality_flags=quality_flags,
        )

    def _build_quality_flags(self) -> list[str]:
        output_format = self.format_combo.GetValue()
        selected = self.quality_combo.GetValue()
        t = self.translator

        if selected == t.get("quality_default"):
            return []

        if selected == t.get("quality_custom"):
            values: dict[str, str | int] = {}
            params = self.quality_manager.get_custom_params(output_format)
            for param in params:
                name = param["name"]
                control = self.custom_controls.get(name)
                if control is None:
                    continue
                if param["type"] == "slider":
                    values[name] = control.GetValue()
                elif param["type"] == "choice":
                    values[name] = control.GetValue()
            return self.quality_manager.build_custom_flags(output_format, values)

        preset_map = {
            t.get("quality_low"): "low",
            t.get("quality_medium"): "medium",
            t.get("quality_high"): "high",
            t.get("quality_maximum"): "maximum",
        }
        preset_key = preset_map.get(selected, "")
        return self.quality_manager.build_preset_flags(output_format, preset_key)

    def _stop_conversion(self) -> None:
        title = self.translator.get("stop_conversion_title")
        message = self.translator.get("stop_conversion_message")
        if wx.MessageBox(message, title, wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            logging.info("User requested conversion stop")
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
            logging.info("Conversion batch finished successfully")
        self._retranslate_ui()

    def _show_incompatible_dialog(self, file_path: str, valid_formats: list[str]) -> None:
        dlg = IncompatibleFileDialog(self, file_path, valid_formats, self.translator)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            self.dialog_result = dlg.get_selected_format()
        else:
            self.dialog_result = None
        dlg.Destroy()
        self.dialog_event.set()
