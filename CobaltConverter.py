import sys
import os
import subprocess
import pathlib
import threading
import re
import locale
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QProgressBar, QFileDialog, QListWidget, QMessageBox,
                               QCheckBox, QLineEdit, QDialog, QDialogButtonBox, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent

# --- LOCALIZATION ---
LANGUAGES = {
    "en": {
        # Window & Footer
        "window_title": "CobaltConverter",
        "footer": "CobaltConverter v0.5.2 by Ashi Vered",
        "language_label": "Language:",
        # Main UI
        "select_files_btn": "Select Files",
        "clear_btn": "Clear",
        "drag_drop_hint": "💡 Drag and drop files here",
        "custom_output_checkbox": "Custom output folder:",
        "output_folder_placeholder": "Same as source file",
        "browse_btn": "Browse",
        "convert_to_label": "Convert to:",
        "status_ready": "Ready",
        "convert_now_btn": "Convert Now",
        "stop_btn": "Stop",
        # File Handling & Status Messages
        "files_selected_status": "{count} file(s) selected",
        "conversion_stopped_status": "Conversion stopped by user",
        "skipping_exists_status": "Skipping {filename} - file exists",
        "converting_status": "Converting ({current}/{total}): {filename}...",
        "all_conversions_complete_status": "All conversions completed!",
        "error_converting_status": "Error converting {filename}: {error}",
        # Dialogs & Messages
        "select_files_dialog_title": "Select Files",
        "select_output_folder_dialog_title": "Select Output Folder",
        "cannot_remove_file_title": "Cannot Remove File",
        "cannot_remove_file_message": "Cannot remove files while a conversion is in progress.",
        "no_files_title": "No Files",
        "no_files_message": "Please select files to convert.",
        "no_format_title": "No Format",
        "no_format_message": "Please select an output format.",
        "stop_conversion_title": "Stop Conversion",
        "stop_conversion_message": "Are you sure you want to stop the conversion?",
        "ffmpeg_not_found_title": "FFmpeg Not Found",
        "ffmpeg_not_found_message": "FFmpeg was not found. Would you like to locate it manually?",
        "locate_ffmpeg_dialog_title": "Locate FFmpeg Executable",
        "conversion_in_progress_title": "Conversion in Progress",
        "conversion_in_progress_message": "A conversion is currently running. Do you want to stop it and close?",
        # Incompatible File Dialog
        "incompatible_file_dialog_title": "Incompatible File",
        "incompatible_file_message": "The file '{filename}' does not support the selected format.\nPlease select a new format to convert to:",
        "skipping_incompatible_status": "Skipping {filename} (Cancelled by user)",
    },
    "he": {
        # Window & Footer
        "window_title": "CobaltConverter",
        "footer": "CobaltConverter v0.5.2 מאת אשי ורד",
        "language_label": "שפה:",
        # Main UI
        "select_files_btn": "בחר קבצים",
        "clear_btn": "נקה",
        "drag_drop_hint": "💡 גרור ושחרר קבצים לכאן",
        "custom_output_checkbox": "תיקיית פלט מותאמת אישית:",
        "output_folder_placeholder": "זהה לקובץ המקור",
        "browse_btn": "עיון",
        "convert_to_label": "המר ל:",
        "status_ready": "מוכן",
        "convert_now_btn": "המר עכשיו",
        "stop_btn": "עצור",
        # File Handling & Status Messages
        "files_selected_status": "{count} קבצים נבחרו",
        "conversion_stopped_status": "ההמרה הופסקה על ידי המשתמש",
        "skipping_exists_status": "מדלג על {filename} - הקובץ קיים",
        "converting_status": "ממיר ({current}/{total}): {filename}...",
        "all_conversions_complete_status": "כל ההמרות הושלמו!",
        "error_converting_status": "שגיאה בהמרת {filename}: {error}",
        # Dialogs & Messages
        "select_files_dialog_title": "בחר קבצים",
        "select_output_folder_dialog_title": "בחר תיקיית פלט",
        "cannot_remove_file_title": "לא ניתן להסיר קובץ",
        "cannot_remove_file_message": "לא ניתן להסיר קבצים בזמן שהמרה מתבצעת.",
        "no_files_title": "לא נבחרו קבצים",
        "no_files_message": "אנא בחר קבצים להמרה.",
        "no_format_title": "לא נבחר פורמט",
        "no_format_message": "אנא בחר פורמט פלט.",
        "stop_conversion_title": "עצירת המרה",
        "stop_conversion_message": "האם אתה בטוח שברצונך לעצור את ההמרה?",
        "ffmpeg_not_found_title": "FFmpeg לא נמצא",
        "ffmpeg_not_found_message": "FFmpeg לא נמצא. האם תרצה לאתר אותו ידנית?",
        "locate_ffmpeg_dialog_title": "אתר את קובץ ההפעלה של FFmpeg",
        "conversion_in_progress_title": "המרה בתהליך",
        "conversion_in_progress_message": "המרה מתבצעת כעת. האם ברצונך לעצור אותה ולסגור?",
        # Incompatible File Dialog
        "incompatible_file_dialog_title": "קובץ לא תואם",
        "incompatible_file_message": "הקובץ '{filename}' אינו תומך בפורמט שנבחר.\nאנא בחר פורמט חדש להמרה:",
        "skipping_incompatible_status": "מדלג על {filename} (בוטל על ידי המשתמש)",
    }
}

class Translator:
    def __init__(self, initial_language='en'):
        self.language = initial_language
        self.translations = LANGUAGES

    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.language = lang_code

    def get(self, key, **kwargs):
        try:
            template = self.translations[self.language][key]
            return template.format(**kwargs) if kwargs else template
        except KeyError:
            try:
                template = self.translations['en'][key]
                return template.format(**kwargs) if kwargs else template
            except KeyError:
                return key

# --- FORMATS ---
VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "gif"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

# --- UTILITY FUNCTIONS ---
def detect_system_language():
    """
    Detects the system language without changing the application's locale,
    making it safe for use with GUI toolkits like Qt.
    """
    # For Windows
    if sys.platform == 'win32':
        try:
            import ctypes
            windll = ctypes.windll.kernel32
            # Get language ID and map it to a language name
            lcid = windll.GetUserDefaultUILanguage()
            lang_name = locale.windows_locale.get(lcid)
            if lang_name:
                primary_lang = lang_name.split('_')[0].lower()
                if primary_lang in LANGUAGES:
                    return primary_lang
        except (ImportError, AttributeError, KeyError):
            pass
    # For macOS and Linux
    else:
        try:
            # Check standard environment variables
            lang_code = os.environ.get('LANG')
            if lang_code:
                primary_lang = lang_code.split('_')[0].lower()
                if primary_lang in LANGUAGES:
                    return primary_lang
        except Exception:
            pass

    # Default to English if detection fails
    return 'en'

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    else: return os.path.dirname(os.path.abspath(__file__))

def get_subprocess_flags():
    if sys.platform == 'win32': return {'creationflags': 0x08000000}
    return {}

def get_file_type(file_path):
    ext = pathlib.Path(file_path).suffix.lower().lstrip(".")
    if ext in VIDEO_FORMATS: return 'video'
    if ext in AUDIO_FORMATS: return 'audio'
    if ext in IMAGE_FORMATS: return 'image'
    return 'unknown'

# --- WORKER SIGNALS ---
class WorkerSignals(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal()
    file_progress = Signal(int, int)
    request_user_choice = Signal(str, list)

# --- INCOMPATIBLE FILE DIALOG ---
class IncompatibleFileDialog(QDialog):
    def __init__(self, filename, formats, translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.setWindowTitle(self.translator.get("incompatible_file_dialog_title"))

        layout = QVBoxLayout(self)
        base_name = os.path.basename(filename)
        message_text = self.translator.get("incompatible_file_message", filename=base_name)
        message = QLabel(message_text)
        layout.addWidget(message)

        self.format_combo = QComboBox()
        self.format_combo.addItems(formats)
        layout.addWidget(self.format_combo)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_selected_format(self):
        return self.format_combo.currentText()

# --- MAIN APPLICATION ---
class CobaltConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(650, 450)

        # State and services
        self.files = []
        self.is_converting = False
        self.stop_requested = False
        self.current_process = None
        self.output_folder = None
        self.custom_ffmpeg_path = None
        self.translator = Translator()

        # Threading sync
        self.dialog_event = threading.Event()
        self.dialog_result = None

        self.init_ui()
        self.setAcceptDrops(True)

        # --- Language Detection and Initialization ---
        detected_lang_code = detect_system_language()

        if detected_lang_code == 'he':
            lang_display_name = 'עברית'
        else:
            lang_display_name = 'English'

        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentText(lang_display_name)
        self.language_combo.blockSignals(False)

        self.change_language(lang_display_name)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- Top Bar (File Selection & Language) ---
        top_bar_layout = QHBoxLayout()
        self.select_btn = QPushButton()
        self.select_btn.clicked.connect(self.select_files)
        top_bar_layout.addWidget(self.select_btn)

        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.clear_files)
        top_bar_layout.addWidget(self.clear_btn)

        top_bar_layout.addStretch()

        self.language_label = QLabel()
        top_bar_layout.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "עברית"])
        self.language_combo.currentTextChanged.connect(self.change_language)
        top_bar_layout.addWidget(self.language_combo)

        layout.addLayout(top_bar_layout)

        # --- File List ---
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)

        self.drag_hint = QLabel()
        self.drag_hint.setAlignment(Qt.AlignCenter)
        self.drag_hint.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.drag_hint)

        # --- Output Folder Selection ---
        output_layout = QHBoxLayout()
        self.use_custom_output = QCheckBox()
        self.use_custom_output.stateChanged.connect(self.toggle_output_folder)
        output_layout.addWidget(self.use_custom_output)

        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setEnabled(False)
        output_layout.addWidget(self.output_folder_edit)

        self.browse_output_btn = QPushButton()
        self.browse_output_btn.clicked.connect(self.select_output_folder)
        self.browse_output_btn.setEnabled(False)
        output_layout.addWidget(self.browse_output_btn)
        layout.addLayout(output_layout)

        # --- Format Selection ---
        format_layout = QHBoxLayout()
        self.format_label = QLabel()
        format_layout.addWidget(self.format_label)

        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(150)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        # --- Progress & Status ---
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        self.convert_btn = QPushButton()
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setMinimumHeight(35)
        button_layout.addWidget(self.convert_btn)

        self.stop_btn = QPushButton()
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(35)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)

        # --- Footer ---
        footer_layout = QHBoxLayout()
        self.footer_label = QLabel()
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet("color: gray; font-size: 10px;")
        footer_layout.addWidget(self.footer_label)
        layout.addLayout(footer_layout)

        # --- Signals ---
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.finished.connect(self.conversion_finished)
        self.signals.file_progress.connect(self.update_file_progress)
        self.signals.request_user_choice.connect(self.prompt_for_new_format)

    # --- LANGUAGE & UI ---
    def change_language(self, lang_name):
        lang_code = 'he' if lang_name == 'עברית' else 'en'
        self.translator.set_language(lang_code)

        if lang_code == 'he':
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)
        else:
            QApplication.instance().setLayoutDirection(Qt.LeftToRight)

        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(self.translator.get("window_title"))
        self.select_btn.setText(self.translator.get("select_files_btn"))
        self.clear_btn.setText(self.translator.get("clear_btn"))
        self.drag_hint.setText(self.translator.get("drag_drop_hint"))
        self.use_custom_output.setText(self.translator.get("custom_output_checkbox"))
        self.output_folder_edit.setPlaceholderText(self.translator.get("output_folder_placeholder"))
        self.browse_output_btn.setText(self.translator.get("browse_btn"))
        self.format_label.setText(self.translator.get("convert_to_label"))
        self.convert_btn.setText(self.translator.get("convert_now_btn"))
        self.stop_btn.setText(self.translator.get("stop_btn"))
        self.footer_label.setText(self.translator.get("footer"))
        self.language_label.setText(self.translator.get("language_label"))

        if not self.is_converting and self.status_label.text() in [LANGUAGES['en']['status_ready'], LANGUAGES['he']['status_ready'], ""]:
            self.status_label.setText(self.translator.get("status_ready"))

    # --- FILE HANDLING ---
    def select_files(self):
        title = self.translator.get("select_files_dialog_title")
        files, _ = QFileDialog.getOpenFileNames(self, title, "", "All Files (*.*)")
        if files: self.add_files(files)

    def add_files(self, files_to_add):
        if self.is_converting: return
        for file in files_to_add:
            if file not in self.files and os.path.isfile(file):
                self.files.append(file)
                item_widget = QWidget()
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(5, 2, 5, 2)
                item_layout.setSpacing(10)

                filename_label = QLabel(os.path.basename(file))
                filename_label.setToolTip(file)
                item_layout.addWidget(filename_label, 1)

                remove_btn = QPushButton("X")
                remove_btn.setFixedSize(24, 24)
                remove_btn.setStyleSheet("font-weight: bold; color: red;")
                remove_btn.clicked.connect(lambda checked, f=file: self.remove_file(f))
                item_layout.addWidget(remove_btn)

                list_item = QListWidgetItem(self.file_list)
                list_item.setSizeHint(item_widget.sizeHint())
                self.file_list.addItem(list_item)
                self.file_list.setItemWidget(list_item, item_widget)

        if self.files:
            self.update_format_options()
            self.status_label.setText(self.translator.get("files_selected_status", count=len(self.files)))

    def remove_file(self, file_to_remove):
        if self.is_converting:
            QMessageBox.warning(self, self.translator.get("cannot_remove_file_title"),
                                      self.translator.get("cannot_remove_file_message"))
            return
        try:
            index = self.files.index(file_to_remove)
            self.files.pop(index)
            self.file_list.takeItem(index)
            if self.files:
                self.status_label.setText(self.translator.get("files_selected_status", count=len(self.files)))
            else:
                self.status_label.setText(self.translator.get("status_ready"))
            self.update_format_options()
        except ValueError:
            pass

    def clear_files(self):
        if self.is_converting: return
        self.files.clear()
        self.file_list.clear()
        self.format_combo.clear()
        self.status_label.setText(self.translator.get("status_ready"))
        self.progress_bar.setValue(0)

    def update_format_options(self):
        if not self.files:
            self.format_combo.clear()
            return
        current_selection = self.format_combo.currentText()
        file_type = get_file_type(self.files[0])
        formats = []
        if file_type == 'video': formats = VIDEO_FORMATS + AUDIO_FORMATS
        elif file_type == 'audio': formats = AUDIO_FORMATS
        elif file_type == 'image': formats = IMAGE_FORMATS
        self.format_combo.clear()
        self.format_combo.addItems(formats)
        if current_selection and current_selection in formats:
            self.format_combo.setCurrentText(current_selection)

    def toggle_output_folder(self, state):
        enabled = state == Qt.Checked.value
        self.output_folder_edit.setEnabled(enabled)
        self.browse_output_btn.setEnabled(enabled)
        if not enabled:
            self.output_folder = None
            self.output_folder_edit.clear()

    def select_output_folder(self):
        title = self.translator.get("select_output_folder_dialog_title")
        folder = QFileDialog.getExistingDirectory(self, title)
        if folder:
            self.output_folder = folder
            self.output_folder_edit.setText(folder)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and not self.is_converting:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.is_converting:
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_files(files)

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
            QMessageBox.warning(self, self.translator.get("no_files_title"), self.translator.get("no_files_message"))
            return
        if not self.format_combo.currentText():
            QMessageBox.warning(self, self.translator.get("no_format_title"), self.translator.get("no_format_message"))
            return
        if not self.get_ffmpeg_path():
            self.prompt_for_ffmpeg_path()
            if not self.get_ffmpeg_path(): return

        self.is_converting = True
        self.stop_requested = False
        self.convert_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.select_btn.setEnabled(False); self.clear_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        output_format = self.format_combo.currentText()
        threading.Thread(target=self.convert_all, args=(output_format,), daemon=True).start()

    def stop_conversion(self):
        title = self.translator.get("stop_conversion_title")
        message = self.translator.get("stop_conversion_message")
        if QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.stop_requested = True
            if self.current_process: self.current_process.terminate()
            if not self.dialog_event.is_set(): self.dialog_event.set()
            self.signals.status.emit(self.translator.get("conversion_stopped_status"))

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
                self.dialog_result, self.dialog_event.clear()
                self.signals.request_user_choice.emit(file, valid_formats)
                self.dialog_event.wait()
                if self.dialog_result: current_output_format = self.dialog_result
                else:
                    self.signals.status.emit(self.translator.get("skipping_incompatible_status", filename=os.path.basename(file)))
                    processed_count += 1; self.signals.file_progress.emit(processed_count, total_files)
                    continue

            if self.output_folder:
                output_filename = pathlib.Path(file).stem + f".{current_output_format}"
                output_file = os.path.join(self.output_folder, output_filename)
            else:
                output_file = str(pathlib.Path(file).with_suffix(f".{current_output_format}"))

            if os.path.exists(output_file):
                self.signals.status.emit(self.translator.get("skipping_exists_status", filename=os.path.basename(file)))
                processed_count += 1; self.signals.file_progress.emit(processed_count, total_files)
                continue

            status_msg = self.translator.get("converting_status", current=processed_count + 1, total=total_files, filename=os.path.basename(file))
            self.signals.status.emit(status_msg)
            self.run_ffmpeg_conversion(ffmpeg_path, file, output_file)

            if not self.stop_requested:
                processed_count += 1
                self.signals.file_progress.emit(processed_count, total_files)

        if not self.stop_requested:
            self.signals.status.emit(self.translator.get("all_conversions_complete_status"))
            if total_files > 0: self.signals.progress.emit(100)
        self.signals.finished.emit()

    def run_ffmpeg_conversion(self, ffmpeg_path, input_file, output_file):
        try:
            cmd = [ffmpeg_path, "-i", input_file, output_file, "-y"]
            self.current_process = subprocess.Popen(
                cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                text=True, encoding="utf-8", errors="ignore",
                universal_newlines=True, **get_subprocess_flags()
            )
            self.current_process.wait()
        except Exception as e:
            status_msg = self.translator.get("error_converting_status", filename=os.path.basename(input_file), error=e)
            self.signals.status.emit(status_msg)
        finally:
            self.current_process = None

    # --- SLOTS & EVENT HANDLERS ---
    def update_progress(self, value): self.progress_bar.setValue(value)
    def update_status(self, message): self.status_label.setText(message)
    def update_file_progress(self, current, total):
        if total > 0: self.progress_bar.setValue(int((current / total) * 100))

    def conversion_finished(self):
        self.is_converting = False
        self.convert_btn.setEnabled(True); self.stop_btn.setEnabled(False)
        self.select_btn.setEnabled(True); self.clear_btn.setEnabled(True)
        self.current_process = None
        if not self.stop_requested and self.files: self.progress_bar.setValue(100)

    def prompt_for_new_format(self, file_path, valid_formats):
        dialog = IncompatibleFileDialog(file_path, valid_formats, self.translator, self)
        self.dialog_result = dialog.get_selected_format() if dialog.exec() == QDialog.Accepted else None
        self.dialog_event.set()

    def prompt_for_ffmpeg_path(self):
        title = self.translator.get("ffmpeg_not_found_title")
        message = self.translator.get("ffmpeg_not_found_message")
        if QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            dialog_title = self.translator.get("locate_ffmpeg_dialog_title")
            file, _ = QFileDialog.getOpenFileName(self, dialog_title)
            if file and os.path.isfile(file): self.custom_ffmpeg_path = file

    def closeEvent(self, event):
        if self.is_converting:
            title = self.translator.get("conversion_in_progress_title")
            message = self.translator.get("conversion_in_progress_message")
            if QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.stop_requested = True
                if self.current_process: self.current_process.terminate()
                if not self.dialog_event.is_set(): self.dialog_event.set()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

# --- APPLICATION ENTRY POINT ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CobaltConverter()
    window.show()
    sys.exit(app.exec())
