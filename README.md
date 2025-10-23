# CobaltConverter

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/Powered%20by-FFmpeg-orange.svg)](https://ffmpeg.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)](https://doc.qt.io/qtforpython/)

**CobaltConverter** is a cross-platform file conversion program built on top of **[FFmpeg](https://ffmpeg.org/)**.  
FFmpeg is a powerful multimedia toolkit, but it lacks a graphical interface — so **CobaltConverter** provides one using **[PySide6](https://doc.qt.io/qtforpython/)** for a modern and native GUI experience.

---

## 🚀 Features

- Clean and simple graphical interface for FFmpeg  
- Batch conversion support  
- Cross-platform (Windows, macOS, Linux)  
- Extensible design for future format and feature support  

---

## 🧩 Installation

### Windows
Pre-compiled releases are available for **Windows** under the [Releases](../../releases) section.

### Other Operating Systems
You can run the Python source directly on **Linux** or **macOS**, provided FFmpeg and PySide6 are installed.

#### Requirements
- [Python 3.8+](https://www.python.org/downloads/)
- [FFmpeg](https://ffmpeg.org/download.html)
- [PySide6](https://pypi.org/project/PySide6/)

Install PySide6 using pip:

    pip install PySide6

---

## 📝 To-Do List

| Status | Feature |
|:------:|----------|
| ⏳ | Support multiple languages |
| ✅ | Add batch conversion *(done in v0.4.2)* |
| ⏳ | Add option to use via right-click menu |
| ⏳ | Add document conversion |
| ⏳ | Add support for all FFmpeg-supported formats |
| ✅ | Add option to select save path for converted files *(done in v0.5.0)* |
| ✅ | Treat GIF as video *(done in v0.4.3)* |
| ✅ | Add “Stop” button *(done in v0.5.0)* |

✅ = Completed ⏳ = In progress / Planned

---

## 📜 License

**CobaltConverter** is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
**FFmpeg** is an external dependency developed by the FFmpeg project and is distributed under its own license.

See [LICENSE](LICENSE) for details.

---

## 💬 Credits

- **Developer:** [Ashi Vered](https://github.com/AshiVered)  
- **Powered by:** [FFmpeg](https://ffmpeg.org/) and [PySide6](https://doc.qt.io/qtforpython/)
