# Changelog

All notable changes to CAN Analyzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-31

###  Initial Release

First public release of CAN Analyzer with comprehensive CAN bus analysis features.

### Added
- **Cross-platform support** - macOS (py2app) and Linux (PyInstaller)
- **Multi-language support** - 5 languages (EN, PT, ES, DE, FR)
- **Modular architecture** - Clean separation of concerns (~6,500 lines)
- **Professional packaging** - Automated build system with custom icons
- **Dependency separation** - Runtime vs build dependencies
- **USB device auto-detection** - Automatic scanning for CAN adapters
- **Comprehensive documentation** - README, DEPENDENCIES, ICONS guides
- **Arduino examples** - CanHacker firmware and test generators
- **Icon generation tool** - `create_icon.sh` for custom icons

### Changed
- **Complete code refactoring** - Moved from monolithic to modular design
- **Improved UI/UX** - Cleaner interface with better feedback
- **Better error handling** - Comprehensive logging system
- **Enhanced file operations** - Support for JSON, CSV, TRC formats
- **Optimized performance** - Faster message processing
- **Updated dependencies** - PyQt6, python-can 4.3+, pyserial 3.5+

### Fixed
- Monitor Mode being editable
- Log loading not updating message colors
- Intrusive popups (replaced with status bar)
- Tracer button text toggling
- Listen Only vs Normal Mode issues
- USB device detection on different platforms

### Removed
- Windows support (temporarily - will be re-added)
- Old monolithic code structure
- Unused backup files and scripts

---

**Legend:**
-  Implemented
- ⏳ Planned
-  Not available
