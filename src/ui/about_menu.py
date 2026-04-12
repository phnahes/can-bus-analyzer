"""
About menu — application information (version, build, license).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox, QWidget

from .. import __version__, __build__
from ..config import REPO_URL
from ..i18n import t
from ..utils import get_platform_display_name


def show_about(parent: QWidget) -> None:
    """Show the About dialog with version, description, and license."""
    platform_name = get_platform_display_name()
    about_text = f"""
        <h2>{t('about_heading', platform=platform_name)}</h2>
        <p><b>{t('about_version')}:</b> {__version__}</p>
        <p><b>{t('about_build')}:</b> {__build__}</p>

        <h3>{t('about_desc_heading')}:</h3>
        <p>{t('about_desc_text')}</p>

        <h3>{t('about_platforms_heading')}:</h3>
        <ul>
            <li>{t('about_platform_macos')}</li>
            <li>{t('about_platform_linux')}</li>
        </ul>

        <h3>{t('about_dependencies_heading')}:</h3>
        <p>{t('about_dependencies_text')}</p>

        <h3>{t('about_license_heading')}:</h3>
        <p>{t('about_license_text')}</p>

        <p>{t('about_repository', repo_url=REPO_URL)}</p>
        <p>{t('about_copyright')}</p>
        """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(t('dialog_about_title'))
    box.setTextFormat(Qt.TextFormat.RichText)
    box.setText(about_text.strip())
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    if hasattr(box, 'setOpenExternalLinks'):
        box.setOpenExternalLinks(True)
    else:
        for lbl in box.findChildren(QLabel):
            lbl.setOpenExternalLinks(True)
    box.exec()
