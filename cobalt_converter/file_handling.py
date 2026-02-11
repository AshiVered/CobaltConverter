import os

import wx

from cobalt_converter.constants import (
    AUDIO_FORMATS,
    IMAGE_FORMATS,
    VIDEO_FORMATS,
    get_file_type,
)


class FileHandlingMixin:
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
        self._update_quality_options()

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
