"""
Storage path helpers for save/load dialogs.

Default structure:
  ~/CAN Analyzer/saves/<component>/
"""

from pathlib import Path
from typing import Optional
from .config import APP_NAME


SAVES_DIRNAME = "saves"


def get_app_home_dir() -> Path:
    """Return app home directory under the user's home, creating it if needed."""
    app_dir = Path.home() / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_default_saves_root_dir() -> Path:
    """Return the default saves root path (without creating it)."""
    return Path.home() / APP_NAME / SAVES_DIRNAME


def _get_configured_saves_root_dir() -> Optional[Path]:
    """
    Return configured saves root directory if available.

    Reads `saves_base_dir` from config and expands `~`.
    """
    try:
        from .config_manager import get_config_manager
        configured = (get_config_manager().get("saves_base_dir", "") or "").strip()
        if not configured:
            return None
        return Path(configured).expanduser()
    except Exception:
        return None


def get_saves_root_dir() -> Path:
    """Return base saves directory, creating it if needed."""
    saves_root = _get_configured_saves_root_dir() or get_default_saves_root_dir()
    saves_root.mkdir(parents=True, exist_ok=True)
    return saves_root


def get_component_dir(component: str) -> Path:
    """Return component-specific saves directory, creating it if needed."""
    component_name = (component or "misc").strip().lower().replace(" ", "_")
    component_dir = get_saves_root_dir() / component_name
    component_dir.mkdir(parents=True, exist_ok=True)
    return component_dir


def dialog_path(component: str, default_filename: str = "") -> str:
    """
    Return initial path for QFileDialog.

    If default_filename is provided, returns full path including filename.
    Otherwise returns the component directory path.
    """
    component_dir = get_component_dir(component)
    if default_filename:
        return str(component_dir / default_filename)
    return str(component_dir)
