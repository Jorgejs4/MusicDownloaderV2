# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import sysconfig
from pathlib import Path

# Detectar rutas base automáticamente
PYTHON_HOME = Path(sys.prefix)
TCL_DIR = PYTHON_HOME / "tcl"
SITE_PACKAGES = Path(sysconfig.get_paths()["purelib"])

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(SITE_PACKAGES / 'customtkinter'), 'customtkinter/'),
        (str(TCL_DIR / 'tcl8.6'), '_tcl_data/tcl8.6'),
        (str(TCL_DIR / 'tk8.6'), '_tk_data/tk8.6'),
        ('bin/ffmpeg.exe', 'bin'),
        ('bin/ffprobe.exe', 'bin'),
    ],
    hiddenimports=[
        # customtkinter importa estos módulos dinámicamente. La instalación
        # de Python los tiene, pero PyInstaller los excluye si su autodetección
        # de Tcl/Tk falla.
        'tkinter',
        '_tkinter',
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

# PyInstaller 6.x puede excluir el paquete puro de tkinter cuando falla su
# comprobación automática de Tcl/Tk, aunque _tkinter.pyd sí esté instalado.
# Incluir explícitamente sus módulos evita el ModuleNotFoundError en el EXE.
TKINTER_DIR = PYTHON_HOME / 'Lib' / 'tkinter'
for tkinter_file in TKINTER_DIR.rglob('*.py'):
    relative_name = tkinter_file.relative_to(TKINTER_DIR)
    module_parts = list(relative_name.with_suffix('').parts)
    if module_parts[-1] == '__init__':
        module_parts.pop()
    module_name = 'tkinter' + ('.' + '.'.join(module_parts) if module_parts else '')
    a.pure.append((module_name, str(tkinter_file), 'PYMODULE'))

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
