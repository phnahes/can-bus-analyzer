# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for CAN Analyzer (Linux)
# Build: pyinstaller can_analyzer.spec

import os

block_cipher = None

# Hidden imports for dynamic loading
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtPrintSupport',
    'serial',
    'serial.tools.list_ports',
    'can',
    'can.interface',
    'src.main_window',
    'src.config_manager',
    'src.dialogs_new',
    'src.file_operations',
    'src.logger',
    'src.i18n',
    'src.models',
    'src.can_interface',
    'src.can_bus_manager',
    'src.theme',
    'src.usb_device_monitor',
    'src.utils',
]

# Collect data files (if any)
datas = []

a = Analysis(
    ['can_analyzer.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PySide6'],
    noarchive=False,
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Detect icon
icon_path = 'icon.ico' if os.path.exists('icon.ico') else None

# Linux: Create directory with executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CAN Analyzer',
    icon=icon_path,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CAN Analyzer',
)
