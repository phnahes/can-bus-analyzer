"""
Setup script for py2app (macOS)
Build: python setup.py py2app
"""

from setuptools import setup
import os

# Single source of truth for version (used by About and .app bundle)
import src
_version = src.__version__

APP = ['can_analyzer.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns' if os.path.exists('icon.icns') else None,
    'plist': {
        'CFBundleName': 'CAN Analyzer',
        'CFBundleDisplayName': 'CAN Analyzer',
        'CFBundleIdentifier': 'com.cantools.can-analyzer',
        'CFBundleVersion': _version,
        'CFBundleShortVersionString': _version,
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
