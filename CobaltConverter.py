import sys
import os
import subprocess
import pathlib
import threading
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QComboBox, 
                               QProgressBar, QFileDialog, QListWidget, QMessageBox,
                               QCheckBox, QLineEdit)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent

VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "gif"]
AUDIO_FORMATS = ["mp3", "aac", "wav", "flac", "ogg", "m4a"]
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_subprocess_flags():
    """Returns subprocess flags appropriate for the current platform."""
    if sys.platform == 'win32':
        return {'creationflags': 0x08000000}  # CREATE_NO_WINDOW
    return {}

class WorkerSignals(QObject):
    """Signals for worker thread communication."""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal()
    file_progress = Signal(int, int)  # current file, total files

class CobaltConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CobaltConverter")
        self.setMinimumSize(650, 450)
        
        self.files = []
        self.is_converting = False
        self.stop_requested = False
        self.current_process = None
        self.output_folder = None
        self.custom_ffmpeg_path = None
        
        self.init_ui()
        self.setAcceptDrops(True)
        
    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # File selection area
        file_layout = QHBoxLayout()
        file_label = QLabel("Files:")
        file_layout.addWidget(file_label)
        
        self.select_btn = QPushButton("Select Files")
        self.select_btn.clicked.connect(self.select_files)
        file_layout.addWidget(self.select_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_files)
        file_layout.addWidget(self.clear_btn)
        
        file_layout.addStretch()
        layout.addLayout(file_layout)
        
        # File list with drag-and-drop
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)
        
        # Drag and drop hint
        drag_hint = QLabel("💡 Drag and drop files here")
        drag_hint.setAlignment(Qt.AlignCenter)
        drag_hint.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(drag_hint)
        
        # Output folder selection
        output_layout = QHBoxLayout()
        self.use_custom_output = QCheckBox("Custom output folder:")
        self.use_custom_output.stateChanged.connect(self.toggle_output_folder)
        output_layout.addWidget(self.use_custom_output)
        
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Same as source file")
        self.output_folder_edit.setEnabled(False)
        self.output_folder_edit.setReadOnly(True)
        output_layout.addWidget(self.output_folder_edit)
        
        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.select_output_folder)
        self.browse_output_btn.setEnabled(False)
        output_layout.addWidget(self.browse_output_btn)
        
        layout.addLayout(output_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Convert to:")
        format_layout.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(150)
        format_layout.addWidget(self.format_combo)
        
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Buttons
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
        
        # Footer
        footer = QLabel("CobaltConverter v0.5.0 by Ashi Vered")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(footer)
        
        # Signals
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.finished.connect(self.conversion_finished)
        self.signals.file_progress.connect(self.update_file_progress)
    
    def get_ffmpeg_path(self):
        """Get FFmpeg path, checking multiple locations."""
        # If user has specified a custom path
        if self.custom_ffmpeg_path and os.path.isfile(self.custom_ffmpeg_path):
            return self.custom_ffmpeg_path
        
        # Check in bin folder relative to script
        ffmpeg_name = "ffmpeg.exe" if sys.platform == 'win32' else "ffmpeg"
        local_path = os.path.join(get_base_path(), "bin", ffmpeg_name)
        if os.path.isfile(local_path):
            return local_path
        
        # Check if ffmpeg is in system PATH
        try:
            result = subprocess.run([ffmpeg_name, "-version"], 
                                  capture_output=True, 
                                  **get_subprocess_flags())
            if result.returncode == 0:
                return ffmpeg_name
        except FileNotFoundError:
            pass
        
        return None
    
    def toggle_output_folder(self, state):
        """Enable/disable output folder selection."""
        enabled = state == Qt.Checked
        self.output_folder_edit.setEnabled(enabled)
        self.browse_output_btn.setEnabled(enabled)
        if not enabled:
            self.output_folder = None
            self.output_folder_edit.clear()
    
    def select_output_folder(self):
        """Select custom output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_folder_edit.setText(folder)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files(files)
    
    def select_files(self):
        """Open file dialog to select files."""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*.*)")
        if files:
            self.add_files(files)
    
    def add_files(self, files):
        """Add files to the conversion list."""
        for file in files:
            if file not in self.files and os.path.isfile(file):
                self.files.append(file)
                self.file_list.addItem(os.path.basename(file))
        
        if self.files:
            self.update_format_options()
            self.status_label.setText(f"{len(self.files)} file(s) selected")
    
    def clear_files(self):
        """Clear all selected files."""
        if self.is_converting:
            QMessageBox.warning(self, "Conversion in Progress", 
                              "Cannot clear files while conversion is running.")
            return
        self.files.clear()
        self.file_list.clear()
        self.format_combo.clear()
        self.status_label.setText("Ready")
    
    def update_format_options(self):
        """Update available format options based on selected files."""
        if not self.files:
            return
        
        first_ext = pathlib.Path(self.files[0]).suffix.lower().lstrip(".")
        
        if first_ext in VIDEO_FORMATS:
            formats = VIDEO_FORMATS + AUDIO_FORMATS
        elif first_ext in AUDIO_FORMATS:
            formats = AUDIO_FORMATS
        elif first_ext in IMAGE_FORMATS:
            formats = IMAGE_FORMATS
        else:
            formats = []
        
        self.format_combo.clear()
        self.format_combo.addItems(formats)
    
    def start_conversion(self):
        """Start the conversion process."""
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please select files to convert.")
            return
        
        if not self.format_combo.currentText():
            QMessageBox.warning(self, "No Format", "Please select an output format.")
            return
        
        # Check if FFmpeg exists
        ffmpeg_path = self.get_ffmpeg_path()
        if not ffmpeg_path:
            reply = QMessageBox.question(
                self, "FFmpeg Not Found",
                "FFmpeg was not found. Would you like to locate it manually?\n\n"
                "You can download FFmpeg from: https://ffmpeg.org/download.html",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                file, _ = QFileDialog.getOpenFileName(
                    self, "Locate FFmpeg Executable",
                    "", "Executable Files (*.exe);;All Files (*.*)" if sys.platform == 'win32' else "All Files (*)"
                )
                if file and os.path.isfile(file):
                    self.custom_ffmpeg_path = file
                else:
                    return
            else:
                return
        
        self.is_converting = True
        self.stop_requested = False
        self.convert_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.select_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        output_format = self.format_combo.currentText()
        thread = threading.Thread(target=self.convert_all, args=(output_format,), daemon=True)
        thread.start()
    
    def stop_conversion(self):
        """Stop the current conversion."""
        reply = QMessageBox.question(self, "Stop Conversion",
                                     "Are you sure you want to stop the conversion?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.stop_requested = True
            if self.current_process:
                self.current_process.terminate()
            self.signals.status.emit("Conversion stopped by user")
    
    def convert_all(self, output_format):
        """Convert all files (runs in background thread)."""
        ffmpeg_path = self.get_ffmpeg_path()
        if not ffmpeg_path:
            self.signals.status.emit("FFmpeg not found!")
            self.signals.finished.emit()
            return
        
        unsupported = []
        total = len(self.files)
        
        for idx, file in enumerate(self.files, 1):
            if self.stop_requested:
                break
            
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
            
            self.signals.file_progress.emit(idx, total)
            self.signals.status.emit(f"Converting {os.path.basename(file)} ({idx}/{total})...")
            self.run_ffmpeg(ffmpeg_path, file, output_format)
        
        if not self.stop_requested:
            self.signals.status.emit("All conversions completed!")
            self.signals.progress.emit(100)
        
        self.signals.finished.emit()
    
    def run_ffmpeg(self, ffmpeg_path, input_file, output_format):
        """Run FFmpeg conversion for a single file."""
        if self.stop_requested:
            return
        
        # Determine output file path
        if self.output_folder:
            output_filename = pathlib.Path(input_file).stem + f".{output_format}"
            output_file = os.path.join(self.output_folder, output_filename)
        else:
            output_file = str(pathlib.Path(input_file).with_suffix(f".{output_format}"))
        
        # Get duration
        duration_cmd = [ffmpeg_path, "-i", input_file]
        result = subprocess.run(duration_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                              text=True, encoding="utf-8", errors="ignore", 
                              **get_subprocess_flags())
        
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        total_seconds = None
        if duration_match:
            h, m, s = duration_match.groups()
            total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
        
        # Start conversion
        self.current_process = subprocess.Popen(
            [ffmpeg_path, "-i", input_file, output_file, "-y"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding="utf-8", errors="ignore",
            universal_newlines=True, **get_subprocess_flags()
        )
        
        for line in self.current_process.stderr:
            if self.stop_requested:
                self.current_process.terminate()
                break
            
            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if time_match and total_seconds:
                h, m, s = time_match.groups()
                current = int(h) * 3600 + int(m) * 60 + float(s)
                percent = int((current / total_seconds) * 100)
                self.signals.progress.emit(min(percent, 100))
        
        self.current_process.wait()
        self.current_process = None
    
    def update_progress(self, value):
        """Update progress bar."""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """Update status label."""
        self.status_label.setText(message)
    
    def update_file_progress(self, current, total):
        """Update progress for multiple files."""
        overall_progress = int((current / total) * 100)
        self.progress_bar.setValue(overall_progress)
    
    def conversion_finished(self):
        """Handle conversion completion."""
        self.is_converting = False
        self.convert_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.select_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.current_process = None
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_converting:
            reply = QMessageBox.question(
                self, "Conversion in Progress",
                "A conversion is currently running. Do you want to stop it and close?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_requested = True
                if self.current_process:
                    self.current_process.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CobaltConverter()
    window.show()
    sys.exit(app.exec())
