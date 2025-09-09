import wx
import os
import subprocess
import pathlib

# פורמטים נתמכים
VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"]

class CobaltConverter(wx.Frame):
    def __init__(self):
        super().__init__(None, title="CobaltConverter", size=(500, 250))
        panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # בחירת קובץ
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl1 = wx.StaticText(panel, label="בחר קובץ:")
        hbox1.Add(lbl1, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)

        self.file_picker = wx.FilePickerCtrl(panel, message="בחר קובץ להמרה")
        self.file_picker.Bind(wx.EVT_FILEPICKER_CHANGED, self.on_file_selected)
        hbox1.Add(self.file_picker, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND | wx.ALL, border=10)

        # בחירת פורמט יעד
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        lbl2 = wx.StaticText(panel, label="פורמט יעד:")
        hbox2.Add(lbl2, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)

        self.format_choice = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        hbox2.Add(self.format_choice, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND | wx.ALL, border=10)

        # כפתור המרה
        self.convert_btn = wx.Button(panel, label="המר")
        self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
        vbox.Add(self.convert_btn, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        # הודעות
        self.log = wx.StaticText(panel, label="")
        vbox.Add(self.log, flag=wx.EXPAND | wx.ALL, border=10)

        panel.SetSizer(vbox)
        self.Centre()
        self.Show()

    def on_file_selected(self, event):
        file_path = self.file_picker.GetPath()
        suffix = pathlib.Path(file_path).suffix.lower().lstrip(".")

        if suffix in VIDEO_FORMATS:
            self.format_choice.SetItems(VIDEO_FORMATS + AUDIO_FORMATS)
        elif suffix in AUDIO_FORMATS:
            self.format_choice.SetItems(AUDIO_FORMATS)
        elif suffix in IMAGE_FORMATS:
            self.format_choice.SetItems(IMAGE_FORMATS)
        else:
            self.format_choice.SetItems([])
        if self.format_choice.GetItems():
            self.format_choice.SetSelection(0)

    def on_convert(self, event):
        input_file = self.file_picker.GetPath()
        if not input_file or not os.path.exists(input_file):
            self.log.SetLabel("לא נבחר קובץ תקין.")
            return

        output_format = self.format_choice.GetValue()
        if not output_format:
            self.log.SetLabel("בחר פורמט יעד.")
            return

        output_file = str(pathlib.Path(input_file).with_suffix(f".{output_format}"))
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg")

        if os.name == "nt":
            ffmpeg_path += ".exe"

        try:
            cmd = [ffmpeg_path, "-i", input_file, output_file, "-y"]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log.SetLabel(f"המרה הושלמה: {output_file}")
        except subprocess.CalledProcessError as e:
            self.log.SetLabel("שגיאה בהמרה. בדוק שה־ffmpeg תקין.")
        except Exception as e:
            self.log.SetLabel(str(e))

if __name__ == "__main__":
    app = wx.App(False)
    CobaltConverter()
    app.MainLoop()
