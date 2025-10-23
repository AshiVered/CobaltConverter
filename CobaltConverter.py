import sys
import os
import subprocess
import pathlib
import threading
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QProgressBar, QFileDialog, QListWidget, QMessageBox,
                               QCheckBox, QLineEdit, QDialog, QDialogButtonBox, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent

# --- FORMATS ---
VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "gif"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

# --- UTILITY FUNCTIONS ---
def get_base_path():
    """Get the base path for the application, handling frozen executables."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_subprocess_flags():
    """Returns subprocess flags appropriate for the current platform to hide the console."""
    if sys.platform == 'win32':
        return {'creationflags': 0x08000000}  # CREATE_NO_WINDOW
    return {}

def get_file_type(file_path):
    """Determine file type based on extension."""
    ext = pathlib.Path(file_path).suffix.lower().lstrip(".")
    if ext in VIDEO_FORMATS:
        return 'video'
    if ext in AUDIO_FORMATS:
        return 'audio'
    if ext in IMAGE_FORMATS:
        return 'image'
    return 'unknown'

# --- WORKER SIGNALS ---
class WorkerSignals(QObject):
    """Signals for worker thread communication."""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal()
    file_progress = Signal(int, int)
    request_user_choice = Signal(str, list)

# --- INCOMPATIBLE FILE DIALOG ---
class IncompatibleFileDialog(QDialog):
    """Dialog to handle files incompatible with the selected format."""
    def __init__(self, filename, formats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incompatible File")

        layout = QVBoxLayout(self)
        base_name = os.path.basename(filename)
        message = QLabel(f"The file '{base_name}' does not support the selected format.\n"
                         f"Please select a new format to convert to:")
        layout.addWidget(message)

        self.format_combo = QComboBox()
        self.format_combo.addItems(formats)
        layout.addWidget(self.format_combo)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_selected_format(self):
        """Returns the format chosen by the user."""
        return self.format_combo.currentText()

# --- MAIN APPLICATION ---
class CobaltConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CobaltConverter")
        self.setMinimumSize(650, 450)

        # State variables
        self.files = []
        self.is_converting = False
        self.stop_requested = False
        self.current_process = None
        self.output_folder = None
        self.custom_ffmpeg_path = None

        # Threading synchronization
        self.dialog_event = threading.Event()
        self.dialog_result = None

        self.init_ui()
        self.setAcceptDrops(True)

    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- File Selection Area ---
        file_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select Files")
        self.select_btn.clicked.connect(self.select_files)
        file_layout.addWidget(self.select_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_files)
        file_layout.addWidget(self.clear_btn)

        file_layout.addStretch()
        layout.addLayout(file_layout)

        # --- File List ---
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)

        drag_hint = QLabel("💡 Drag and drop files here")
        drag_hint.setAlignment(Qt.AlignCenter)
        drag_hint.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(drag_hint)

        # --- Output Folder Selection ---
        output_layout = QHBoxLayout()
        self.use_custom_output = QCheckBox("Custom output folder:")
        self.use_custom_output.stateChanged.connect(self.toggle_output_folder)
        output_layout.addWidget(self.use_custom_output)

        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Same as source file")
        self.output_folder_edit.setEnabled(False)
        output_layout.addWidget(self.output_folder_edit)

        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.select_output_folder)
        self.browse_output_btn.setEnabled(False)
        output_layout.addWidget(self.browse_output_btn)

        layout.addLayout(output_layout)

        # --- Format Selection ---
        format_layout = QHBoxLayout()
        format_label = QLabel("Convert to:")
        format_layout.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(150)
        format_layout.addWidget(self.format_combo)

        format_layout.addStretch()
        layout.addLayout(format_layout)

        # --- Progress & Status ---
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Convert Now")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setMinimumHeight(35)
        button_layout.addWidget(self.convert_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(35)
        button_layout.addWidget(self.stop_btn)

        layout.addLayout(button_layout)

        # --- Footer ---
        footer = QLabel("CobaltConverter v0.5.1 by Ashi Vered")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(footer)

        # --- Signals ---
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.finished.connect(self.conversion_finished)
        self.signals.file_progress.connect(self.update_file_progress)
        self.signals.request_user_choice.connect(self.prompt_for_new_format)

    # --- UI & FILE HANDLING METHODS ---
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*.*)")
        if files: self.add_files(files)

    def add_files(self, files_to_add):
        if self.is_converting: return
        
        for file in files_to_add:
            if file not in self.files and os.path.isfile(file):
                self.files.append(file)
                
                # Create a custom widget for the list item
                item_widget = QWidget()
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(5, 2, 5, 2)
                item_layout.setSpacing(10)
                
                # Filename label
                filename_label = QLabel(os.path.basename(file))
                filename_label.setToolTip(file) # Show full path on hover
                item_layout.addWidget(filename_label, 1) # The '1' makes it stretch

                # Remove button
                remove_btn = QPushButton("X")
                remove_btn.setFixedSize(24, 24)
                remove_btn.setStyleSheet("font-weight: bold; color: red;")
                # Use a lambda to pass the specific file to the remove function
                # The f=file part is crucial to capture the current file in the loop
                remove_btn.clicked.connect(lambda checked, f=file: self.remove_file(f))
                item_layout.addWidget(remove_btn)
                
                # Create QListWidgetItem and set the custom widget
                list_item = QListWidgetItem(self.file_list)
                list_item.setSizeHint(item_widget.sizeHint())
                self.file_list.addItem(list_item)
                self.file_list.setItemWidget(list_item, item_widget)
                
        if self.files:
            self.update_format_options()
            self.status_label.setText(f"{len(self.files)} file(s) selected")

    def remove_file(self, file_to_remove):
        """Removes a single file from the list."""
        if self.is_converting:
            QMessageBox.warning(self, "Cannot Remove File", "Cannot remove files while a conversion is in progress.")
            return

        try:
            # Find the index of the file to remove it from both data and view
            index = self.files.index(file_to_remove)
            self.files.pop(index)
            self.file_list.takeItem(index) # takeItem removes and returns the item

            # Update UI
            if self.files:
                self.status_label.setText(f"{len(self.files)} file(s) selected")
            else:
                self.status_label.setText("Ready")
            
            self.update_format_options() # Crucial to update formats if the first file was removed
        except ValueError:
            # This should not happen in normal operation, but it's good practice
            print(f"Error: Could not find {file_to_remove} in the list.")

    def clear_files(self):
        if self.is_converting: return
        self.files.clear()
        self.file_list.clear()
        self.format_combo.clear()
        self.status_label.setText("Ready")
        self.progress_bar.setValue(0)

    def update_format_options(self):
        """Update format options based ONLY on the first file in the list."""
        if not self.files: 
            self.format_combo.clear()
            return

        current_selection = self.format_combo.currentText()
        file_type = get_file_type(self.files[0])

        formats = []
        if file_type == 'video':
            formats = VIDEO_FORMATS + AUDIO_FORMATS
        elif file_type == 'audio':
            formats = AUDIO_FORMATS
        elif file_type == 'image':
            formats = IMAGE_FORMATS

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
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_folder_edit.setText(folder)

    # --- DRAG & DROP ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and not self.is_converting:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.is_converting:
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_files(files)

    # --- CONVERSION LOGIC ---
    def get_ffmpeg_path(self):
        """Finds a usable FFmpeg executable."""
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
            QMessageBox.warning(self, "No Files", "Please select files to convert.")
            return
        if not self.format_combo.currentText():
            QMessageBox.warning(self, "No Format", "Please select an output format.")
            return

        if not self.get_ffmpeg_path():
            self.prompt_for_ffmpeg_path()
            if not self.get_ffmpeg_path(): return

        # UI lock
        self.is_converting = True
        self.stop_requested = False
        self.convert_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.select_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start worker thread
        output_format = self.format_combo.currentText()
        thread = threading.Thread(target=self.convert_all, args=(output_format,), daemon=True)
        thread.start()

    def stop_conversion(self):
        if QMessageBox.question(self, "Stop Conversion",
                                     "Are you sure you want to stop the conversion?",
                                     QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.stop_requested = True
            if self.current_process: self.current_process.terminate()
            if not self.dialog_event.is_set(): self.dialog_event.set() 
            self.signals.status.emit("Conversion stopped by user")

    def convert_all(self, initial_output_format):
        """Conversion logic that runs in a background thread."""
        ffmpeg_path = self.get_ffmpeg_path()
        files_snapshot = self.files.copy()
        total_files = len(files_snapshot)

        compatible_files, incompatible_files = [], []
        for file in files_snapshot:
            file_type = get_file_type(file)
            valid_formats = []
            if file_type == 'video': valid_formats = VIDEO_FORMATS + AUDIO_FORMATS
            elif file_type == 'audio': valid_formats = AUDIO_FORMATS
            elif file_type == 'image': valid_formats = IMAGE_FORMATS

            if initial_output_format in valid_formats:
                compatible_files.append(file)
            else:
                incompatible_files.append(file)

        files_to_process = compatible_files + incompatible_files
        processed_count = 0

        for file in files_to_process:
            if self.stop_requested: break

            current_output_format = initial_output_format
            file_type = get_file_type(file)
            valid_formats = []
            if file_type == 'video': valid_formats = VIDEO_FORMATS + AUDIO_FORMATS
            elif file_type == 'audio': valid_formats = AUDIO_FORMATS
            elif file_type == 'image': valid_formats = IMAGE_FORMATS

            if current_output_format not in valid_formats:
                self.dialog_result = None
                self.dialog_event.clear()
                self.signals.request_user_choice.emit(file, valid_formats)
                self.dialog_event.wait() 

                if self.dialog_result:
                    current_output_format = self.dialog_result
                else:
                    self.signals.status.emit(f"Skipping {os.path.basename(file)} (Cancelled by user)")
                    processed_count += 1
                    self.signals.file_progress.emit(processed_count, total_files)
                    continue

            if self.output_folder:
                output_filename = pathlib.Path(file).stem + f".{current_output_format}"
                output_file = os.path.join(self.output_folder, output_filename)
            else:
                output_file = str(pathlib.Path(file).with_suffix(f".{current_output_format}"))

            if os.path.exists(output_file):
                self.signals.status.emit(f"Skipping {os.path.basename(file)} - file exists")
                processed_count += 1
                self.signals.file_progress.emit(processed_count, total_files)
                continue

            self.signals.status.emit(f"Converting ({processed_count + 1}/{total_files}): {os.path.basename(file)}...")
            self.run_ffmpeg_conversion(ffmpeg_path, file, output_file)

            if not self.stop_requested:
                processed_count += 1
                self.signals.file_progress.emit(processed_count, total_files)

        if not self.stop_requested:
            self.signals.status.emit("All conversions completed!")
            if total_files > 0: self.signals.progress.emit(100)

        self.signals.finished.emit()

    def run_ffmpeg_conversion(self, ffmpeg_path, input_file, output_file):
        """Executes a single FFmpeg conversion process."""
        try:
            cmd = [ffmpeg_path, "-i", input_file, output_file, "-y"]
            self.current_process = subprocess.Popen(
                cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                text=True, encoding="utf-8", errors="ignore",
                universal_newlines=True, **get_subprocess_flags()
            )
            self.current_process.wait()
        except Exception as e:
            self.signals.status.emit(f"Error converting {os.path.basename(input_file)}: {e}")
        finally:
            self.current_process = None

    # --- SLOTS & EVENT HANDLERS ---
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)

    def update_file_progress(self, current, total):
        """Update overall progress based on number of files completed."""
        if total > 0:
            overall_progress = int((current / total) * 100)
            self.progress_bar.setValue(overall_progress)

    def conversion_finished(self):
        """Called when the conversion thread finishes."""
        self.is_converting = False
        self.convert_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.select_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.current_process = None
        if not self.stop_requested and self.files:
             self.progress_bar.setValue(100)

    def prompt_for_new_format(self, file_path, valid_formats):
        """Slot to handle the request for user choice (runs in main thread)."""
        dialog = IncompatibleFileDialog(file_path, valid_formats, self)
        if dialog.exec() == QDialog.Accepted:
            self.dialog_result = dialog.get_selected_format()
        else:
            self.dialog_result = None
        self.dialog_event.set()

    def prompt_for_ffmpeg_path(self):
        if QMessageBox.question(self, "FFmpeg Not Found",
                                "FFmpeg was not found. Would you like to locate it manually?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            file, _ = QFileDialog.getOpenFileName(self, "Locate FFmpeg Executable")
            if file and os.path.isfile(file):
                self.custom_ffmpeg_path = file

    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_converting:
            if QMessageBox.question(self, "Conversion in Progress",
                                    "A conversion is currently running. Do you want to stop it and close?",
                                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
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