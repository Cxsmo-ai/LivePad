
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import PyQt6

a = Analysis(
    ["chat_gamepad_app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("build/bridge/LivePad.HIDMaestro.zip", "bridge"),
        ("bridge/vendor/LICENSE", "licenses/HIDMaestro"),
        ("bridge/vendor/THIRD-PARTY-NOTICES.txt", "licenses/HIDMaestro"),
        ("profiles/cod.json", "profiles"),
        ("QUICK_START.txt", "."),
        ("assets/app_icon.png", "assets"),
        ("assets/app_icon.ico", "assets"),
        ("assets/livepad_mark.png", "assets"),
    ],
    hiddenimports=[
        "gamepad_tester", "stream_icons", "youtube_client", "tiktok_client", "twitch_client",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["vgamepad", "flask", "obswebsocket"],
    noarchive=False,
    optimize=1,
)

qt_bin = Path(PyQt6.__file__).parent / "Qt6" / "bin"
vc_runtime_names = {"vcruntime140.dll", "vcruntime140_1.dll"}
excluded_binaries = {"opengl32sw.dll", "qt6pdf.dll"}
a.binaries = [
    (destination, str(qt_bin / Path(destination).name), kind)
    if destination.casefold() in vc_runtime_names
    else (destination, source, kind)
    for destination, source, kind in a.binaries
    if not destination.casefold().startswith("api-ms-win-")
    and destination.casefold() != "ucrtbase.dll"
    and not Path(destination).name.casefold().startswith("icu")
    and Path(destination).name.casefold() not in excluded_binaries
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LivePad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/app_icon.ico",
    version="version_info.txt",
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LivePad",
)

