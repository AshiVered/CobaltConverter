import sys
import os
import subprocess
import pathlib
import threading
import re
import locale
import wx
import json
import logging

class Translator:
    def __init__(self, initial_language='en'):
        self.language = initial_language
        self.translations = {}
        self._load_languages()

    def _load_languages(self):
        """Loads all JSON language files from the 'Languages' directory."""
        base_path = os.path.join(get_base_path(), "Languages")
        if not os.path.exists(base_path):
            print("Languages directory not found:", base_path)
            return

        for filename in os.listdir(base_path):
            if filename.endswith(".json"):
                lang_code = os.path.splitext(filename)[0].lower()
                file_path = os.path.join(base_path, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.language = lang_code

    def get(self, key, **kwargs):
        try:
            template = self.translations[self.language][key]
            return template.format(**kwargs) if kwargs else template
        except KeyError:
            try:
                template = self.translations.get('en', {}).get(key, key)
                return template.format(**kwargs) if kwargs else template
            except Exception:
                return key

# --- FORMATS ---
VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "gif"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

# --- UTILITY FUNCTIONS ---
def detect_system_language():
    """
    Detects the system language without changing the application's locale.
    """
    # For Windows
    if sys.platform == 'win32':
        try:
            import ctypes
            windll = ctypes.windll.kernel32
            lcid = windll.GetUserDefaultUILanguage()
            lang_name = locale.windows_locale.get(lcid)
            if lang_name:
                primary_lang = lang_name.split('_')[0].lower()
                if primary_lang in LANGUAGES:
                    return primary_lang
        except Exception:
            pass
    else:
        try:
            lang_code = os.environ.get('LANG')
            if lang_code:
                primary_lang = lang_code.split('_')[0].lower()
                if primary_lang in LANGUAGES:
                    return primary_lang
        except Exception:
            pass
    return 'en'

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    else: return os.path.dirname(os.path.abspath(__file__))

# --- LOGGING CONFIGURATION (set up after get_base_path is available) ---
def setup_logging():
    base_path = get_base_path()
    log_path = os.path.join(base_path, "CobaltConverter.log")
    try:
        # אם קיים קובץ לוג ישן — נחליף אותו
        if os.path.exists(log_path):
            os.remove(log_path)
    except Exception:
        pass

    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8"
    )
    logging.info(f"Logging initialized. Log file: {log_path}")
    return log_path

LOG_PATH = setup_logging()
print("Log file:", LOG_PATH)   # עד שתוודא שהלוג נוצר, ניתן להשאיר את הפקודה הזו


def get_subprocess_flags():
    if sys.platform == 'win32': return {'creationflags': 0x08000000}
    return {}

def get_file_type(file_path):
    ext = pathlib.Path(file_path).suffix.lower().lstrip(".")
    if ext in VIDEO_FORMATS: return 'video'
    if ext in AUDIO_FORMATS: return 'audio'
    if ext in IMAGE_FORMATS: return 'image'
    return 'unknown'

# --- Drag & Drop Target ---
class FileDropTarget(wx.FileDropTarget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def OnDropFiles(self, x, y, filenames):
        if not self.parent.is_converting:
            self.parent.add_files(filenames)
            return True
        return False

# --- Incompatible File Dialog (wx) ---
class IncompatibleFileDialog(wx.Dialog):
    def __init__(self, parent, filename, formats, translator):
        title = translator.get("incompatible_file_dialog_title")
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.translator = translator
        self.selected = None
        self._build_ui(filename, formats)

    def _build_ui(self, filename, formats):
        s = wx.BoxSizer(wx.VERTICAL)
        base_name = os.path.basename(filename)
        msg = self.translator.get("incompatible_file_message", filename=base_name)
        lbl = wx.StaticText(self, label=msg)
        s.Add(lbl, 0, wx.ALL|wx.EXPAND, 8)

        self.combo = wx.ComboBox(self, choices=formats, style=wx.CB_READONLY)
        if formats:
            self.combo.SetSelection(0)
        s.Add(self.combo, 0, wx.ALL|wx.EXPAND, 8)

        btns = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        s.Add(btns, 0, wx.ALL|wx.EXPAND, 8)

        self.SetSizerAndFit(s)

    def get_selected_format(self):
        return self.combo.GetValue()

# --- MAIN APPLICATION FRAME ---
class CobaltConverterFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="CobaltConverter", size=(700, 520))
        self.SetMinSize((650, 450))

        # state
        self.files = []
        self.is_converting = False
        self.stop_requested = False
        self.current_process = None
        self.output_folder = None
        self.custom_ffmpeg_path = None
        self.translator = Translator()

        # dialog synchronization
        self.dialog_event = threading.Event()
        self.dialog_result = None

        self._build_ui()
        self.SetDropTarget(FileDropTarget(self))

        # language initialization
        detected = detect_system_language()
        display = 'עברית' if detected == 'he' else 'English'
        # set combobox
        self.language_choice.SetStringSelection(display)
        self.change_language(display)

        # Center and show
        self.Centre()
        self.Show()

    def _build_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(main_sizer)
        main_sizer.SetMinSize((600, 400))

        # Top bar: select, clear, language
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.select_btn = wx.Button(panel)
        self.select_btn.Bind(wx.EVT_BUTTON, lambda e: self.select_files())
        top_sizer.Add(self.select_btn, 0, wx.RIGHT, 6)

        self.clear_btn = wx.Button(panel)
        self.clear_btn.Bind(wx.EVT_BUTTON, lambda e: self.clear_files())
        top_sizer.Add(self.clear_btn, 0, wx.RIGHT, 6)

        top_sizer.AddStretchSpacer(1)

        self.language_label = wx.StaticText(panel)
        top_sizer.Add(self.language_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 6)
        self.language_choice = wx.ComboBox(panel, choices=["English", "עברית"], style=wx.CB_READONLY)
        self.language_choice.Bind(wx.EVT_COMBOBOX, lambda e: self.change_language(self.language_choice.GetValue()))
        top_sizer.Add(self.language_choice, 0)

        main_sizer.Add(top_sizer, 0, wx.EXPAND|wx.ALL, 8)

        # File list area - scrolled window with item panels
        self.scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        self.scroll.SetScrollRate(5, 5)
        self.list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.list_sizer)
        self.list_sizer.AddStretchSpacer(1)
        main_sizer.Add(self.scroll, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 8)

        # drag hint
        self.drag_hint = wx.StaticText(panel)
        self.drag_hint.Wrap(600)
        self.drag_hint.SetForegroundColour(wx.Colour(128,128,128))
        main_sizer.Add(self.drag_hint, 0, wx.EXPAND|wx.ALL, 6)

        # Output folder selection
        out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.use_custom_output = wx.CheckBox(panel)
        self.use_custom_output.Bind(wx.EVT_CHECKBOX, self.toggle_output_folder)
        out_sizer.Add(self.use_custom_output, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 6)

        self.output_folder_edit = wx.TextCtrl(panel)
        self.output_folder_edit.Enable(False)
        out_sizer.Add(self.output_folder_edit, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 6)

        self.browse_output_btn = wx.Button(panel)
        self.browse_output_btn.Bind(wx.EVT_BUTTON, lambda e: self.select_output_folder())
        self.browse_output_btn.Enable(False)
        out_sizer.Add(self.browse_output_btn, 0)

        main_sizer.Add(out_sizer, 0, wx.EXPAND|wx.ALL, 8)

        # Format selection
        format_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.format_label = wx.StaticText(panel)
        format_sizer.Add(self.format_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 6)
        self.format_combo = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        self.format_combo.SetMinSize((150, -1))
        format_sizer.Add(self.format_combo, 0, wx.RIGHT, 6)
        format_sizer.AddStretchSpacer(1)
        main_sizer.Add(format_sizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, 8)

        # Progress and status
        self.progress_bar = wx.Gauge(panel, range=100)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND|wx.ALL, 8)
        self.status_label = wx.StaticText(panel, label="")
        main_sizer.Add(self.status_label, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 8)

        # Action buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.convert_btn = wx.Button(panel)
        self.convert_btn.Bind(wx.EVT_BUTTON, lambda e: self.start_conversion())
        self.convert_btn.SetMinSize((-1, 35))
        btn_sizer.Add(self.convert_btn, 0, wx.RIGHT, 6)

        self.stop_btn = wx.Button(panel)
        self.stop_btn.Bind(wx.EVT_BUTTON, lambda e: self.stop_conversion())
        self.stop_btn.Enable(False)
        self.stop_btn.SetMinSize((-1, 35))
        btn_sizer.Add(self.stop_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_LEFT|wx.ALL, 8)

        # Footer
        footer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.footer_label = wx.StaticText(panel)
        self.footer_label.SetForegroundColour(wx.Colour(128,128,128))
        footer_sizer.AddStretchSpacer(1)
        footer_sizer.Add(self.footer_label, 0, wx.ALIGN_CENTER_VERTICAL)
        footer_sizer.AddStretchSpacer(1)
        main_sizer.Add(footer_sizer, 0, wx.EXPAND|wx.ALL, 4)



        # initial text set via translator
        self.retranslate_ui()

    # --- Language & UI updates ---
    def change_language(self, lang_name):
        lang_code = 'he' if lang_name == 'עברית' else 'en'
        self.translator.set_language(lang_code)
        # layout direction
        try:
            if lang_code == 'he':
                self.SetLayoutDirection(wx.Layout_RightToLeft)
            else:
                self.SetLayoutDirection(wx.Layout_LeftToRight)
        except Exception:
            # not all wx versions support SetLayoutDirection; ignore if not available
            pass
        self.retranslate_ui()
        self.Layout()

    def retranslate_ui(self):
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
        self.footer_label.SetLabel(t.get("footer"))
        self.language_label.SetLabel(t.get("language_label"))

        if not self.is_converting:
            current_status = self.status_label.GetLabel()
            if current_status in ["", self.translator.get("status_ready")]:
                self.status_label.SetLabel(self.translator.get("status_ready"))

    # --- FILE HANDLING ---
    def select_files(self):
        title = self.translator.get("select_files_dialog_title")
        with wx.FileDialog(self, message=title, wildcard="All files (*.*)|*.*", style=wx.FD_OPEN|wx.FD_MULTIPLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                paths = dlg.GetPaths()
                self.add_files(paths)

    def add_files(self, files_to_add):
        if self.is_converting: return
        added = False
        for file in files_to_add:
            if file not in self.files and os.path.isfile(file):
                self.files.append(file)
                self._add_file_item(file)
                added = True
        if self.files:
            self.update_format_options()
            self.status_label.SetLabel(self.translator.get("files_selected_status", count=len(self.files)))
        if added:
            # refresh scrolled window layout
            self.list_sizer.Layout()
            self.scroll.FitInside()

    def _add_file_item(self, file_path):
        # create an item panel with filename and a remove 'X' button
        panel = wx.Panel(self.scroll)
        s = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(panel, label=os.path.basename(file_path))
        lbl.SetToolTip(file_path)
        s.Add(lbl, 1, wx.ALL|wx.EXPAND, 4)

        remove_btn = wx.Button(panel, label="X", size=(28, 24))
        remove_btn.SetForegroundColour(wx.Colour(255,0,0))
        # capture file in closure
        remove_btn.Bind(wx.EVT_BUTTON, lambda ev, f=file_path, p=panel: self.remove_file(f, p))
        s.Add(remove_btn, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 4)
        panel.SetSizer(s)

        # store reference by attaching to panel
        panel.file_path = file_path
        self.list_sizer.Insert(self.list_sizer.GetItemCount()-1, panel, 0, wx.EXPAND|wx.ALL, 2)

    def remove_file(self, file_to_remove, panel=None):
        if self.is_converting:
            wx.MessageBox(self.translator.get("cannot_remove_file_message"), self.translator.get("cannot_remove_file_title"), wx.ICON_WARNING)
            return
        try:
            index = self.files.index(file_to_remove)
            self.files.pop(index)
            # find panel and remove
            if panel is not None:
                self.list_sizer.Hide(panel)
                panel.Destroy()
            else:
                # fallback: search panels
                for child in self.scroll.GetChildren():
                    if getattr(child, 'file_path', None) == file_to_remove:
                        child.Destroy()
                        break
            if self.files:
                self.status_label.SetLabel(self.translator.get("files_selected_status", count=len(self.files)))
            else:
                self.status_label.SetLabel(self.translator.get("status_ready"))
            self.update_format_options()
            self.list_sizer.Layout()
            self.scroll.FitInside()
        except ValueError:
            pass


    def clear_files(self):
        if self.is_converting: return
        self.files.clear()
        # destroy panels
        for child in list(self.scroll.GetChildren()):
            if hasattr(child, 'file_path'):
                child.Destroy()
        self.format_combo.Clear()
        self.status_label.SetLabel(self.translator.get("status_ready"))
        self.progress_bar.SetValue(0)
        self.list_sizer.Layout()
        self.scroll.FitInside()

    def update_format_options(self):
        if not self.files:
            self.format_combo.Clear()
            return
        current_selection = self.format_combo.GetValue()
        file_type = get_file_type(self.files[0])
        formats = []
        if file_type == 'video': formats = VIDEO_FORMATS + AUDIO_FORMATS
        elif file_type == 'audio': formats = AUDIO_FORMATS
        elif file_type == 'image': formats = IMAGE_FORMATS
        self.format_combo.Clear()
        for f in formats:
            self.format_combo.Append(f)
        if current_selection and current_selection in formats:
            self.format_combo.SetValue(current_selection)

    def toggle_output_folder(self, event):
        enabled = self.use_custom_output.GetValue()
        self.output_folder_edit.Enable(enabled)
        self.browse_output_btn.Enable(enabled)
        if not enabled:
            self.output_folder = None
            self.output_folder_edit.SetValue("")

    def select_output_folder(self):
        title = self.translator.get("select_output_folder_dialog_title")
        with wx.DirDialog(self, message=title) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                folder = dlg.GetPath()
                self.output_folder = folder
                self.output_folder_edit.SetValue(folder)

    # --- CONVERSION LOGIC ---
    def get_ffmpeg_path(self):
        if self.custom_ffmpeg_path and os.path.isfile(self.custom_ffmpeg_path):
            return self.custom_ffmpeg_path
        ffmpeg_name = "ffmpeg.exe" if sys.platform == 'win32' else "ffmpeg"
        local_path = os.path.join(get_base_path(), "bin", ffmpeg_name)
        if os.path.isfile(local_path): return local_path
        try:
            subprocess.run([ffmpeg_name, "-version"], capture_output=True, **get_subprocess_flags())
            return ffmpeg_name
        except FileNotFoundError:
            return None

    def start_conversion(self):
        if not self.files:
            wx.MessageBox(self.translator.get("no_files_message"), self.translator.get("no_files_title"), wx.ICON_WARNING)
            return
        if not self.format_combo.GetValue():
            wx.MessageBox(self.translator.get("no_format_message"), self.translator.get("no_format_title"), wx.ICON_WARNING)
            return
        if not self.get_ffmpeg_path():
            self.prompt_for_ffmpeg_path()
            if not self.get_ffmpeg_path(): return

        self.is_converting = True
        self.stop_requested = False
        self.convert_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.select_btn.Enable(False)
        self.clear_btn.Enable(False)
        self.progress_bar.SetValue(0)

        output_format = self.format_combo.GetValue()
        threading.Thread(target=self.convert_all, args=(output_format,), daemon=True).start()

    def stop_conversion(self):
        title = self.translator.get("stop_conversion_title")
        message = self.translator.get("stop_conversion_message")
        dlgres = wx.MessageBox(message, title, wx.YES_NO|wx.ICON_QUESTION)
        if dlgres == wx.YES:
            self.stop_requested = True
            if self.current_process:
                try:
                    self.current_process.terminate()
                except Exception:
                    pass
            if not self.dialog_event.is_set():
                self.dialog_event.set()
            wx.CallAfter(self._set_status, self.translator.get("conversion_stopped_status"))

    def convert_all(self, initial_output_format):
        ffmpeg_path = self.get_ffmpeg_path()
        files_snapshot = self.files.copy()
        total_files = len(files_snapshot)
        processed_count = 0

        for file in files_snapshot:
            if self.stop_requested: break

            file_type = get_file_type(file)
            valid_formats = []
            if file_type == 'video': valid_formats = VIDEO_FORMATS + AUDIO_FORMATS
            elif file_type == 'audio': valid_formats = AUDIO_FORMATS
            elif file_type == 'image': valid_formats = IMAGE_FORMATS

            current_output_format = initial_output_format
            if current_output_format not in valid_formats:
                # prompt user in main thread and wait
                self.dialog_result = None
                self.dialog_event.clear()
                wx.CallAfter(self._show_incompatible_dialog, file, valid_formats)
                self.dialog_event.wait()
                if self.dialog_result:
                    current_output_format = self.dialog_result
                else:
                    wx.CallAfter(self._set_status, self.translator.get("skipping_incompatible_status", filename=os.path.basename(file)))
                    processed_count += 1
                    wx.CallAfter(self._set_file_progress, processed_count, total_files)
                    continue

            if self.output_folder:
                output_filename = pathlib.Path(file).stem + f".{current_output_format}"
                output_file = os.path.join(self.output_folder, output_filename)
            else:
                output_file = str(pathlib.Path(file).with_suffix(f".{current_output_format}"))

            if os.path.exists(output_file):
                wx.CallAfter(self._set_status, self.translator.get("skipping_exists_status", filename=os.path.basename(file)))
                processed_count += 1
                wx.CallAfter(self._set_file_progress, processed_count, total_files)
                continue

            status_msg = self.translator.get("converting_status", current=processed_count + 1, total=total_files, filename=os.path.basename(file))
            wx.CallAfter(self._set_status, status_msg)
            logging.info("Starting conversion for %s", file)
            self.run_ffmpeg_conversion(ffmpeg_path, file, output_file)

            if not self.stop_requested:
                processed_count += 1
                wx.CallAfter(self._set_file_progress, processed_count, total_files)

        if not self.stop_requested:
            wx.CallAfter(self._set_status, self.translator.get("all_conversions_complete_status"))
            if total_files > 0:
                wx.CallAfter(self._set_progress, 100)
        logging.info("All conversions complete.")
        wx.CallAfter(self._conversion_finished)

    def run_ffmpeg_conversion(self, ffmpeg_path, input_file, output_file):
        try:
            cmd = [ffmpeg_path, "-y", "-i", input_file, output_file]
            logging.info(f"Running command: {' '.join(cmd)}")

            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                universal_newlines=True,
                **get_subprocess_flags()
            )

            # קריאה שורה־שורה מפלט FFmpeg (מונעת תקיעה)
            for line in self.current_process.stdout:
                line = line.strip()
                if line:
                    logging.debug(line)
                    # אפשר לזהות גם התקדמות
                    if "frame=" in line or "time=" in line:
                        wx.CallAfter(self._set_status, f"FFmpeg: {line[:80]}")

            self.current_process.wait()

            rc = self.current_process.returncode
            if rc != 0:
                logging.error(f"FFmpeg exited with code {rc}")
                wx.CallAfter(self._set_status, f"שגיאה בהמרת {os.path.basename(input_file)} (קוד {rc})")
            else:
                logging.info(f"FFmpeg finished successfully for {input_file}")

        except Exception as e:
            logging.exception(f"Exception during FFmpeg run: {e}")
            status_msg = self.translator.get("error_converting_status", filename=os.path.basename(input_file), error=e)
            wx.CallAfter(self._set_status, status_msg)
        finally:
            self.current_process = None


    # --- GUI helper callafters (threads -> UI) ---
    def _set_progress(self, value): self.progress_bar.SetValue(value)
    def _set_status(self, message): self.status_label.SetLabel(message)
    def _set_file_progress(self, current, total):
        if total > 0:
            self.progress_bar.SetValue(int((current / total) * 100))

    def _conversion_finished(self):
        self.is_converting = False
        self.convert_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.select_btn.Enable(True)
        self.clear_btn.Enable(True)
        self.current_process = None
        if not self.stop_requested and self.files:
            self.progress_bar.SetValue(100)

    # --- Dialogs invoked from main thread via wx.CallAfter ---
    def _show_incompatible_dialog(self, file_path, valid_formats):
        dlg = IncompatibleFileDialog(self, file_path, valid_formats, self.translator)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            self.dialog_result = dlg.get_selected_format()
        else:
            self.dialog_result = None
        dlg.Destroy()
        # signal the worker thread to continue
        self.dialog_event.set()

    def prompt_for_ffmpeg_path(self):
        title = self.translator.get("ffmpeg_not_found_title")
        message = self.translator.get("ffmpeg_not_found_message")
        res = wx.MessageBox(message, title, wx.YES_NO|wx.ICON_QUESTION)
        if res == wx.YES:
            dialog_title = self.translator.get("locate_ffmpeg_dialog_title")
            with wx.FileDialog(self, message=dialog_title, style=wx.FD_OPEN) as filed:
                if filed.ShowModal() == wx.ID_OK:
                    file = filed.GetPath()
                    if file and os.path.isfile(file):
                        self.custom_ffmpeg_path = file

    def closeEvent(self, event=None):
        # map to wx Close - bind via EVT_CLOSE if needed
        if self.is_converting:
            title = self.translator.get("conversion_in_progress_title")
            message = self.translator.get("conversion_in_progress_message")
            res = wx.MessageBox(message, title, wx.YES_NO|wx.ICON_QUESTION)
            if res == wx.YES:
                self.stop_requested = True
                if self.current_process:
                    try:
                        self.current_process.terminate()
                    except Exception:
                        pass
                if not self.dialog_event.is_set():
                    self.dialog_event.set()
                try:
                    self.Destroy()
                except Exception:
                    pass
            else:
                return False
        else:
            try:
                self.Destroy()
            except Exception:
                pass
        return True

# --- APPLICATION ENTRY POINT ---
def main():
    app = wx.App(False)
    frame = CobaltConverterFrame()

    # bind close event
    def on_close(evt):
        if not frame.closeEvent():
            evt.Veto()
        else:
            evt.Skip()
    frame.Bind(wx.EVT_CLOSE, on_close)

    app.MainLoop()

if __name__ == "__main__":
    main()
