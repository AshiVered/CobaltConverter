import wx
import os
import subprocess
import pathlib
import threading
import re
import sys

VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"]

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class CobaltConverter(wx.Frame):
    def __init__(self):
        super().__init__(None, title="CobaltConverter", size=(550, 350))
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl1 = wx.StaticText(panel, label="Select files:")
        hbox1.Add(lbl1, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)

        self.file_picker = wx.FilePickerCtrl(panel, message="Select files", style=wx.FLP_OPEN | wx.FLP_FILE_MUST_EXIST)
        self.file_picker.GetPickerCtrl().Bind(wx.EVT_BUTTON, self.on_select_multiple)
        hbox1.Add(self.file_picker, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND | wx.ALL, border=10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        lbl2 = wx.StaticText(panel, label="Convert to:")
        hbox2.Add(lbl2, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)

        self.format_choice = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        hbox2.Add(self.format_choice, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND | wx.ALL, border=10)

        self.gauge = wx.Gauge(panel, range=100, size=(-1, 25))
        vbox.Add(self.gauge, flag=wx.EXPAND | wx.ALL, border=10)

        self.convert_btn = wx.Button(panel, label="Convert now")
        self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
        vbox.Add(self.convert_btn, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        self.log = wx.StaticText(panel, label="")
        vbox.Add(self.log, flag=wx.EXPAND | wx.ALL, border=10)

        self.footer = wx.StaticText(panel, label="CobaltConverter V0.4.2 by Ashi Vered")
        vbox.Add(self.footer, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)
        self.files = []
        self.Centre()
        self.Show()

    def on_select_multiple(self, event):
        dlg = wx.FileDialog(self, "Select files", wildcard="*.*", style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.files = dlg.GetPaths()
            if self.files:
                suffix = pathlib.Path(self.files[0]).suffix.lower().lstrip(".")
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
                self.log.SetLabel(f"{len(self.files)} files selected.")
        dlg.Destroy()

    def on_convert(self, event):
        if not self.files:
            self.log.SetLabel("No files selected.")
            return
        output_format = self.format_choice.GetValue()
        if not output_format:
            self.log.SetLabel("Select format.")
            return
        threading.Thread(target=self.convert_all, args=(output_format,), daemon=True).start()

    def convert_all(self, output_format):
        ffmpeg_path = os.path.join(get_base_path(), "bin", "ffmpeg")
        if os.name == "nt": ffmpeg_path += ".exe"

        unsupported = []
        total = len(self.files)
        for idx, file in enumerate(self.files, 1):
            ext = pathlib.Path(file).suffix.lower().lstrip(".")
            valid_formats = []
            if ext in VIDEO_FORMATS:
                valid_formats = VIDEO_FORMATS + AUDIO_FORMATS
            elif ext in AUDIO_FORMATS:
                valid_formats = AUDIO_FORMATS
            elif ext in IMAGE_FORMATS:
                valid_formats = IMAGE_FORMATS

            if output_format not in valid_formats:
                unsupported.append(file)
                continue

            wx.CallAfter(self.log.SetLabel, f"Converting {os.path.basename(file)}...")
            self.run_ffmpeg(ffmpeg_path, file, output_format)
            wx.CallAfter(self.gauge.SetValue, int((idx / total) * 100))

        for file in unsupported:
            wx.CallAfter(self.handle_unsupported_file, file, output_format, ffmpeg_path)

        wx.CallAfter(self.log.SetLabel, "All conversions done.")
        wx.CallAfter(self.gauge.SetValue, 100)

    def handle_unsupported_file(self, file, old_format, ffmpeg_path):
        basename = os.path.basename(file)
        dlg = wx.SingleChoiceDialog(self,
                                    f"הקובץ {basename} לא תומך בפורמט {old_format}\nבחר פורמט חדש להמרה:",
                                    "Unsupported format",
                                    IMAGE_FORMATS + AUDIO_FORMATS + VIDEO_FORMATS)
        if dlg.ShowModal() == wx.ID_OK:
            new_fmt = dlg.GetStringSelection()
            self.run_ffmpeg(ffmpeg_path, file, new_fmt)
        dlg.Destroy()

    def run_ffmpeg(self, ffmpeg_path, input_file, output_format):
        output_file = str(pathlib.Path(input_file).with_suffix(f".{output_format}"))
        CREATE_NO_WINDOW = 0x08000000
        duration_cmd = [ffmpeg_path, "-i", input_file]
        result = subprocess.run(duration_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="ignore", creationflags=CREATE_NO_WINDOW)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        total_seconds = None
        if duration_match:
            h, m, s = duration_match.groups()
            total_seconds = int(h) * 3600 + int(m) * 60 + float(s)

        process = subprocess.Popen([ffmpeg_path, "-i", input_file, output_file, "-y"],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="ignore",
                                   universal_newlines=True, creationflags=CREATE_NO_WINDOW)
        for line in process.stderr:
            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if time_match and total_seconds:
                h, m, s = time_match.groups()
                current = int(h) * 3600 + int(m) * 60 + float(s)
                percent = int((current / total_seconds) * 100)
                wx.CallAfter(self.gauge.SetValue, min(percent, 100))
        process.wait()

        if process.returncode == 0:
            wx.CallAfter(self.log.SetLabel, f"Conversion completed: {output_file}")
        else:
            wx.CallAfter(self.log.SetLabel, f"Conversion failed for {input_file}")

if __name__ == "__main__":
    app = wx.App(False)
    CobaltConverter()
    app.MainLoop()
