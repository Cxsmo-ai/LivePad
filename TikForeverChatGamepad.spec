# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import PyQt6

a = Analysis(
    ["chat_gamepad_app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("build/bridge/TikForever.HIDMaestro.zip", "bridge"),
        ("bridge/vendor/LICENSE", "licenses/HIDMaestro"),
        ("bridge/vendor/THIRD-PARTY-NOTICES.txt", "licenses/HIDMaestro"),
        ("profiles/cod.json", "profiles"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["vgamepad", "flask", "obswebsocket"],
    noarchive=False,
    optimize=1,
)

# Python 3.10 ships an older VC runtime than Qt 6.11. Keep the newer,
# backward-compatible Qt runtime at the DLL search root for both stacks.
qt_bin = Path(PyQt6.__file__).parent / "Qt6" / "bin"
vc_runtime_names = {"vcruntime140.dll", "vcruntime140_1.dll"}
a.binaries = [
    (destination, str(qt_bin / Path(destination).name), kind)
    if destination.casefold() in vc_runtime_names
    else (destination, source, kind)
    for destination, source, kind in a.binaries
    if not destination.casefold().startswith("api-ms-win-")
    and destination.casefold() != "ucrtbase.dll"
    and not Path(destination).name.casefold().startswith("icu")
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TikForeverChatGamepad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TikForeverChatGamepad",
)
