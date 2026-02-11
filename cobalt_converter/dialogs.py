from __future__ import annotations

import os
from typing import TYPE_CHECKING

import wx

if TYPE_CHECKING:
    from cobalt_converter.translator import Translator


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__()
        self.parent = parent

    def OnDropFiles(self, x: int, y: int, filenames: list[str]) -> bool:
        if not self.parent.is_converting:
            self.parent.add_files(filenames)
            return True
        return False


class IncompatibleFileDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, filename: str, formats: list[str], translator: Translator) -> None:
        title = translator.get("incompatible_file_dialog_title")
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.translator = translator
        self._build_ui(filename, formats)

    def _build_ui(self, filename: str, formats: list[str]) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        base_name = os.path.basename(filename)
        msg = self.translator.get("incompatible_file_message", filename=base_name)
        label = wx.StaticText(self, label=msg)
        sizer.Add(label, 0, wx.ALL | wx.EXPAND, 8)

        self.combo = wx.ComboBox(self, choices=formats, style=wx.CB_READONLY)
        if formats:
            self.combo.SetSelection(0)
        sizer.Add(self.combo, 0, wx.ALL | wx.EXPAND, 8)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)

        self.SetSizerAndFit(sizer)

    def get_selected_format(self) -> str:
        return self.combo.GetValue()
