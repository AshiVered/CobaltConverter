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
CobaltConverter downloads FFmpeg automatically when needed. If you don't have internet access, you can set it up manually:

1. Download the FFmpeg archive for your platform:

   | Platform         | Download link |
   |:-----------------|:--------------|
   | Windows x64      | [ffmpeg-win64-gpl.zip](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip) |
   | macOS (Universal)| [ffmpeg-mac.zip](https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip) |
   | Linux x64        | [ffmpeg-linux64-gpl.tar.xz](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz) |
   | Linux ARM64      | [ffmpeg-linuxarm64-gpl.tar.xz](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz) |

2. Open the downloaded archive (`.zip` or `.tar.xz`) and find the file named `ffmpeg.exe` (Windows) or `ffmpeg` (macOS/Linux). It may be inside a subfolder called `bin/`.

3. Copy that file into the `bin/` folder inside the CobaltConverter project folder. If the `bin/` folder doesn't exist, create it.

4. **macOS/Linux only:** Open a terminal in the project folder and run:
   ```
   chmod +x bin/ffmpeg
   ```

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
