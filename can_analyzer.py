#!/usr/bin/env python3
"""
CAN Analyzer - Entry Point
CAN bus analyzer with SLCAN-based real-time analysis. Runs on macOS and Linux.
"""

import sys
import signal
import atexit
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtWidgets import QDialog, QMainWindow

from src.main_window import CANAnalyzerWindow
from src.logger import init_logger, shutdown_logger, get_logger


class _CloseWindowShortcutFilter(QObject):
    """
    Global shortcut handler:
    - Ctrl+W (Win/Linux) / Cmd+W (macOS) closes the active dialog/window
    - Does not close the main window (use Ctrl/Cmd+Q for exit)
    """

    def __init__(self, app: QApplication, main_window: CANAnalyzerWindow):
        super().__init__()
        self._app = app
        self._main_window = main_window

    def eventFilter(self, obj, event):  # type: ignore[override]
        if event.type() != QEvent.Type.KeyPress:
            return False

        try:
            if event.key() != Qt.Key.Key_W:
                return False
            mods = event.modifiers()
            want_mod = bool(mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
            bad_mods = bool(mods & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier))
            if not want_mod or bad_mods:
                return False
        except Exception:
            return False

        # Prefer modal widget (dialogs), else active window.
        w = self._app.activeModalWidget() or self._app.activeWindow()
        if not w:
            return False

        # Never close the main window with Ctrl/Cmd+W.
        if w is self._main_window:
            return False
        if isinstance(w, QMainWindow):
            # If in the future we open other top-level windows, do not close them by default.
            return False

        # Close dialogs cleanly, so callers waiting on exec() return.
        if isinstance(w, QDialog):
            try:
                w.reject()
            except Exception:
                try:
                    w.close()
                except Exception:
                    pass
            return True

        # Fallback for any other top-level window-like widget.
        try:
            top = w.window() if hasattr(w, "window") else w
            if top is not None and top is not self._main_window:
                top.close()
                return True
        except Exception:
            pass

        return False


def main():
    """Application entry point"""
    # Initialize logging system
    logger = init_logger(log_dir="logs", max_bytes=10*1024*1024, backup_count=5)
    from src.utils import get_platform_display_name
    logger.info(f"Starting CAN Analyzer ({get_platform_display_name()})")
    
    # Initialize configuration manager
    from src.config_manager import init_config_manager
    config_mgr = init_config_manager()
    logger.info(f"Configuration loaded from config.json")
    
    # Initialize i18n system with saved language
    from src.i18n import init_i18n
    saved_language = config_mgr.get('language', 'en')
    init_i18n(saved_language)
    logger.info(f"i18n system initialized with language: {saved_language}")
    
    # Register logger shutdown on exit
    atexit.register(shutdown_logger)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        QApplication.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Configurar nome da aplicação ANTES de criar QApplication (para menu macOS)
        QApplication.setApplicationName("CAN Analyzer")
        QApplication.setOrganizationName("CAN Tools")
        
        # Tentar configurar o nome do bundle no macOS (requer PyObjC)
        try:
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info:
                    info['CFBundleName'] = 'CAN Analyzer'
                    info['CFBundleDisplayName'] = 'CAN Analyzer'
        except ImportError:
            # PyObjC não disponível, continuar sem configurar bundle
            pass
        
        app = QApplication(sys.argv)
        
        # Configurar display name para o menu macOS
        app.setApplicationDisplayName("CAN Analyzer")
        
        # Apply theme based on user preference
        from src.theme import apply_theme_to_app
        theme_preference = config_mgr.get('theme', 'system')
        apply_theme_to_app(app, theme_preference)
        logger.info(f"Theme applied: {theme_preference}")
        
        # Prevent app from quitting when last window closes (for macOS)
        app.setQuitOnLastWindowClosed(True)
        
        logger.info("PyQt6 application initialized")
        
        window = CANAnalyzerWindow()
        window.show()
        window.raise_()  # Bring window to front
        window.activateWindow()  # Activate the window

        # Ctrl+W / Cmd+W: close active dialog/window (not main window)
        try:
            close_filter = _CloseWindowShortcutFilter(app, window)
            app.installEventFilter(close_filter)
            # Keep a strong reference so it isn't GC'd
            window._close_window_shortcut_filter = close_filter  # type: ignore[attr-defined]
        except Exception:
            pass
        
        # Force app activation on macOS
        if sys.platform == 'darwin':
            try:
                from PyQt6.QtCore import QTimer
                def activate_app():
                    window.raise_()
                    window.activateWindow()
                    app.setActiveWindow(window)
                QTimer.singleShot(100, activate_app)  # Activate after 100ms
            except:
                pass
        
        logger.info("Main window displayed")
        
        # Install global exception handler
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            # Force quit the application
            QApplication.quit()
            sys.exit(1)
        
        sys.excepthook = handle_exception
        
        exit_code = app.exec()
        logger.info(f"Application terminated with code: {exit_code}")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}", exc_info=True)
        # Try to quit the app if it exists
        try:
            QApplication.quit()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
