# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Detectar rutas base automáticamente
PYTHON_HOME = Path(sys.prefix)
TCL_DIR = PYTHON_HOME / "tcl"
SITE_PACKAGES = Path(r"C:\Users\jorge\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages")

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(SITE_PACKAGES / 'customtkinter'), 'customtkinter/'),
        (str(TCL_DIR / 'tcl8.6'), 'tcl'),
        (str(TCL_DIR / 'tk8.6'), 'tk'),
        ('bin/ffmpeg.exe', 'bin'),
        ('bin/ffprobe.exe', 'bin'),
    ],
    hiddenimports=[
        'musicDownloader3',
        'music_csv_auto',
        'restaurar_respaldo',
        'qr_sync',
        'auto_sync',
        'exportify_bot',
        'playlist_generator',
        'duplicate_cleaner',
        'genre_classifier',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'customtkinter',
    ],
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
    [],
    name='MusicDownloaderPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # Cambiado a True para ver errores si falla
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
