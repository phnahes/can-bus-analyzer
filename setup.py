"""
Setup script for py2app (macOS)
Build: python setup.py py2app
"""

from setuptools import setup
import os

APP = ['can_analyzer_qt.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns' if os.path.exists('icon.icns') else None,
    'plist': {
        'CFBundleName': 'CAN Analyzer',
        'CFBundleDisplayName': 'CAN Analyzer',
        'CFBundleIdentifier': 'com.cantools.can-analyzer',
        'CFBundleVersion': '0.3.0',
        'CFBundleShortVersionString': '0.3.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
    'packages': ['PyQt6', 'serial', 'can', 'src'],
    'includes': [
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'serial.tools.list_ports',
        'can.interface',
    ],
    'excludes': ['PyQt5', 'PySide2', 'PySide6'],
}

setup(
    name='CAN Analyzer',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
