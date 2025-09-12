import wx
import os
import subprocess
import pathlib
import threading
import re
import sys

# Supported formats
VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"]

def get_base_path():
    if getattr(sys, 'frozen', False):
        # if it's exe
        # sys.executable
        return os.path.dirname(sys.executable)
    else:
        # if it's py script
        return os.path.dirname(os.path.abspath(__file__))

class CobaltConverter(wx.Frame):
    def __init__(self):
        super().__init__(None, title="CobaltConverter", size=(500, 300))
        panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # file selector
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        lbl1 = wx.StaticText(panel, label="Select file:")
        hbox1.Add(lbl1, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)

        self.file_picker = wx.FilePickerCtrl(panel, message="Select file")
        self.file_picker.Bind(wx.EVT_FILEPICKER_CHANGED, self.on_file_selected)
        hbox1.Add(self.file_picker, proportion=1)
        vbox.Add(hbox1, flag=wx.EXPAND | wx.ALL, border=10)

        # format selector
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        lbl2 = wx.StaticText(panel, label="Convert to:")
        hbox2.Add(lbl2, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)

        self.format_choice = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        hbox2.Add(self.format_choice, proportion=1)
        vbox.Add(hbox2, flag=wx.EXPAND | wx.ALL, border=10)

        # Progress bar
        self.gauge = wx.Gauge(panel, range=100, size=(-1, 25))
        vbox.Add(self.gauge, flag=wx.EXPAND | wx.ALL, border=10)

        # Convert button
        self.convert_btn = wx.Button(panel, label="Convert now")
        self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
        vbox.Add(self.convert_btn, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        # Messages
        self.log = wx.StaticText(panel, label="")
        vbox.Add(self.log, flag=wx.EXPAND | wx.ALL, border=10)

        # Footer
        self.footer = wx.StaticText(panel, label="CobaltConverter V0.4.1 by Ashi Vered")
        vbox.Add(self.footer, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

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
            # Reset progress bar and log when new file is selected
            self.gauge.SetValue(0)
            self.log.SetLabel("")

    def on_convert(self, event):
        input_file = self.file_picker.GetPath()
        if not input_file or not os.path.exists(input_file):
            self.log.SetLabel("File is invalid")
            return

        output_format = self.format_choice.GetValue()
        if not output_format:
            self.log.SetLabel("Select format")
            return

        output_file = str(pathlib.Path(input_file).with_suffix(f".{output_format}"))
        base_path = get_base_path()
        ffmpeg_path = os.path.join(base_path, "bin", "ffmpeg")


        if os.name == "nt":
            ffmpeg_path += ".exe"

        self.log.SetLabel("Conversion started...")

        thread = threading.Thread(target=self.run_ffmpeg, args=(ffmpeg_path, input_file, output_file))
        thread.start()

    def run_ffmpeg(self, ffmpeg_path, input_file, output_file):
        log_path = os.path.join(os.path.dirname(__file__), "log.txt")
        try:
            CREATE_NO_WINDOW = 0x08000000 

            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"=== Conversion started ===\nInput file: {input_file}\nOutput file: {output_file}\n")

                # Get media duration
                duration_cmd = [ffmpeg_path, "-i", input_file]
                result = subprocess.run(duration_cmd,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            text=True,
                            encoding="utf-8",
                            errors="ignore",
                            creationflags=CREATE_NO_WINDOW)
                log_file.write(result.stderr + "\n")

                duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
                total_seconds = None
                if duration_match:
                    h, m, s = duration_match.groups()
                    total_seconds = int(h) * 3600 + int(m) * 60 + float(s)

                # Run conversion
                cmd = [ffmpeg_path, "-i", input_file, output_file, "-y"]
                process = subprocess.Popen(cmd,
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               text=True,
                               encoding="utf-8",
                               errors="ignore",
                               universal_newlines=True,
                               creationflags=CREATE_NO_WINDOW)

                for line in process.stderr:
                    log_file.write(line)
                    log_file.flush()

                    time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                    if time_match and total_seconds:
                        h, m, s = time_match.groups()
                        current = int(h) * 3600 + int(m) * 60 + float(s)
                        percent = int((current / total_seconds) * 100)
                        wx.CallAfter(self.gauge.SetValue, min(percent, 100))

                process.wait()

                if process.returncode == 0:
                    wx.CallAfter(self.log.SetLabel, f"Conversion completed: {output_file}")
                    wx.CallAfter(self.gauge.SetValue, 100)
                    log_file.write("=== Conversion completed successfully ===\n\n")
                else:
                    wx.CallAfter(self.log.SetLabel, "Conversion failed.")
                    log_file.write("=== Conversion failed ===\n\n")

        except Exception as e:
            wx.CallAfter(self.log.SetLabel, str(e))
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Error: {e}\n")


if __name__ == "__main__":
    app = wx.App(False)
    CobaltConverter()
    app.MainLoop()
