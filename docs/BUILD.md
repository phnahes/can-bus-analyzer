# Packaging (Build standalone executable)

You can build a standalone package so users don't need Python installed.

### Requirements

- **py2app** for macOS (included in `requirements-dev.txt`)
- **PyInstaller** for Linux (included in `requirements-dev.txt`)
- Same OS as the target: build on macOS for macOS, on Linux for Linux

### Development Dependencies (only for building/packaging)
- **py2app** >= 0.28.8 (macOS)
- **PyInstaller** >= 6.0.0 (Linux)
- **Pillow** >= 10.0.0 (for icon generation)

### System Requirements
- **macOS**: 10.14+ (for running from source) or any recent version (for .app bundle)
- **Linux**: Modern distribution with Python 3.9+ and Qt/GUI support

### Quick build

**macOS / Linux:** (run from project root)
```bash
./extras/build.sh
```
The script creates/activates a venv and installs dependencies if needed.

**Note:** Use `requirements-dev.txt` for building (includes py2app/PyInstaller). Use `requirements.txt` only for running from source.

### Output

| OS      | Build tool | Output                           |
|---------|------------|----------------------------------|
| **macOS**  | py2app     | `dist/CAN Analyzer.app`          |
| **Linux**  | PyInstaller| `dist/CAN Analyzer/CAN Analyzer` |

### Files

- **`setup.py`** – py2app configuration for macOS
- **`can_analyzer.spec`** – PyInstaller spec for Linux
- **`extras/build.sh`** – Build script (auto-detects platform; run from project root)
- **`extras/create_icon.sh`** – Icon generation script (run from project root)
- **`requirements.txt`** – Runtime dependencies (included in app)
- **`requirements-dev.txt`** – Build tools (NOT included in app)



### Changing the App Icon

To use a custom icon:

1. **Create or download a PNG** (recommended: 1024x1024 or larger)
   - Example: `my_custom_icon.png`

2. **Generate icon files** (from project root):
   ```bash
   ./extras/create_icon.sh my_custom_icon.png
   ```
   This creates:
   - `icon.icns` (macOS)
   - `icon.ico` (Linux)

3. **Rebuild the app**:
   ```bash
   ./extras/build.sh
   ```

The build script automatically detects and uses `icon.icns` (macOS) or `icon.ico` (Linux) if present.

**See `ICONS.md` for detailed instructions on creating icons, recommended tools, and design tips.**

### macOS: Single .app (not folder + .app)

The build script now generates **only** `CAN Analyzer.app` on macOS (the intermediate folder is automatically cleaned up). You'll get:
- ✅ `dist/CAN Analyzer.app` (ready to use)
- ❌ No extra `dist/CAN Analyzer/` folder

To run: `open "dist/CAN Analyzer.app"`


### Config and logs when packaged

- **config.json** and **logs/** are created in the **current working directory** when you run the app.
- For a fixed location (e.g. user config dir), you can adapt the app to use a path based on `sys.executable` when running frozen.