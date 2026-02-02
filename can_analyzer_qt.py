#!/usr/bin/env python3
"""
CAN Analyzer - Entry Point
CAN bus analyzer with SLCAN-based real-time analysis. Runs on macOS and Linux.
"""

import sys
import atexit
from PyQt6.QtWidgets import QApplication

from src.main_window import CANAnalyzerWindow
from src.logger import init_logger, shutdown_logger, get_logger


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
        
        exit_code = app.exec()
        logger.info(f"Application terminated with code: {exit_code}")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
