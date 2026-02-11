# -*- mode: python ; coding: utf-8 -*-
# CobaltConverter.spec
#
# Build commands:
#   Lite (no FFmpeg):   pyinstaller CobaltConverter.spec
#   Full (with FFmpeg): INCLUDE_FFMPEG=1 pyinstaller CobaltConverter.spec
#
# Windows (cmd):       set INCLUDE_FFMPEG=1 && pyinstaller CobaltConverter.spec
# Windows (PowerShell): $env:INCLUDE_FFMPEG="1"; pyinstaller CobaltConverter.spec

import os
import platform

include_ffmpeg = os.environ.get("INCLUDE_FFMPEG", "0") == "1"
current_os = platform.system()

ffmpeg_binary_name = "ffmpeg.exe" if current_os == "Windows" else "ffmpeg"
ffmpeg_source_path = os.path.join("bin", ffmpeg_binary_name)

datas = [
    ("cobalt_converter/config/*.json", "cobalt_converter/config"),
    ("cobalt_converter/Languages/*.json", "cobalt_converter/Languages"),
]

binaries = []
if include_ffmpeg and os.path.isfile(ffmpeg_source_path):
    binaries.append((ffmpeg_source_path, "bin"))
    print(f"[BUILD] Including FFmpeg: {ffmpeg_source_path}")
elif include_ffmpeg:
    print(f"[BUILD] WARNING: INCLUDE_FFMPEG=1 but {ffmpeg_source_path} not found!")
else:
    print("[BUILD] Building WITHOUT FFmpeg")

app_name = "CobaltConverter"

a = Analysis(
    ["CobaltConverter.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

if current_os == "Darwin":
    app = BUNDLE(
        exe,
        name=f"{app_name}.app",
        bundle_identifier="com.cobaltconverter.app",
        version="0.7",
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "NSAppleScriptEnabled": False,
            "CFBundleDisplayName": "CobaltConverter",
            "CFBundleShortVersionString": "0.7",
            "NSHighResolutionCapable": True,
        },
    )
