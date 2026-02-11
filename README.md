# CobaltConverter

**CobaltConverter** is a cross-platform file conversion program built on top of **[FFmpeg](https://ffmpeg.org/)**.  
FFmpeg is a powerful multimedia toolkit, but it lacks a graphical interface — so **CobaltConverter** provides one using **[WxPython](https://github.com/wxWidgets/Phoenix)** for a flexible design that adapts itself to the operating system (Windows, Linux, macOS).

---

## 🚀 Features

- Clean and simple graphical interface for FFmpeg
- Batch conversion support
- Cross-platform (Windows, macOS, Linux)
- Automatic FFmpeg download if not found on system
- Multi-language support (English, Hebrew)

---

## 🧩 Installation

### Windows
Pre-compiled releases are available for **Windows** under the [Releases](../../releases) section.

### Other Operating Systems
You can run the Python source directly on **Linux** or **macOS**.
FFmpeg will be downloaded automatically on first use if not already installed.

#### Requirements
- [Python 3.12+](https://www.python.org/downloads/)
- [wxPython](https://github.com/wxWidgets/Phoenix)

Install wxPython using pip:

    pip install wxPython

### Offline / Manual FFmpeg Setup
If you prefer not to use the automatic download (e.g. for offline use), download the binary for your platform and place it in the `bin/` folder at the project root:

| Platform         | Download link | Expected file |
|:-----------------|:--------------|:--------------|
| Windows x64      | [ffmpeg-win64-gpl.zip](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip) | `bin/ffmpeg.exe` |
| macOS (Universal)| [ffmpeg-mac.zip](https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip) | `bin/ffmpeg` |
| Linux x64        | [ffmpeg-linux64-gpl.tar.xz](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz) | `bin/ffmpeg` |
| Linux ARM64      | [ffmpeg-linuxarm64-gpl.tar.xz](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz) | `bin/ffmpeg` |

Extract the `ffmpeg` binary from the archive and copy it to the `bin/` folder. On macOS/Linux make sure it is executable (`chmod +x bin/ffmpeg`).

---

## To-Do List

| Status | Feature |
|:------:|----------|
| ✅ | Support multiple languages *(done in v0.6)* |
| ✅ | Add batch conversion *(done in v0.4.2)* |
| ✅ | Auto-download FFmpeg if not installed |
| ⏳ | Add option to use via right-click menu |
| ⏳ | Add document conversion |
| ⏳ | Add support for all FFmpeg-supported formats |
| ✅ | Add option to select save path for converted files *(done in v0.5.0)* |
| ✅ | Treat GIF as video *(done in v0.4.3)* |
| ✅ | Add “Stop” button *(done in v0.5.0)* |

---

### License

**CobaltConverter** is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
**FFmpeg** is an external dependency developed by the FFmpeg project and is distributed under its own license.

See [LICENSE](LICENSE) for details.

---

## 💬 Credits

- **Main developer:** [Ashi Vered](https://github.com/AshiVered)  
- **Contributors:** [Yisroel Tech](https://github.com/YisroelTech), [cfopuser](https://github.com/cfopuser)
