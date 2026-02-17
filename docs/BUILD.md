# Packaging (Build standalone executable)

You can build a standalone package so users don't need Python installed.

### Quick build

**macOS / Linux:** (run from project root)
```bash
./extras/build.sh
```
The script creates/activates a venv and installs dependencies if needed.

**Note:** Use `requirements-dev.txt` for building (includes py2app/PyInstaller). Use `requirements.txt` only for running from source.

### GitHub Actions (macOS + Linux builds)

If you are on macOS and want Linux builds (or vice-versa), use GitHub Actions:

- `CI Build (macOS + Linux)` workflow: manual build via `workflow_dispatch`
- `Release Build (macOS + Linux)` workflow: automatic build when you push a tag `vX.Y.Z`

#### Artifacts vs Release assets (about "zip inside zip")

GitHub Actions always delivers workflow artifacts as a downloaded `.zip` file.

- The artifact `.zip` is created by GitHub to bundle uploaded files.
- Our build script also creates the distributable `CAN-Analyzer-<version>-<os>.zip`.

So, when you download an artifact and unzip it, you will typically see:
- `CAN-Analyzer-*.zip` (this is the real distributable you should share)

For GitHub Releases, we upload only `CAN-Analyzer-*.zip` as the release asset, so users do not need to deal with an extra artifact wrapper.

#### Run CI build without bumping version

1. Go to GitHub -> Actions -> `CI Build (macOS + Linux)`
2. Click `Run workflow`
3. Download the artifact for your OS
4. Use the `CAN-Analyzer-*.zip` file inside it

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

### Output

| OS      | Build tool | Output                           |
|---------|------------|----------------------------------|
| **macOS**  | py2app     | `dist/CAN Analyzer.app`          |
| **Linux**  | PyInstaller| `dist/CAN Analyzer/CAN Analyzer` |

The build script also generates a distributable zip in the project root:
- `CAN-Analyzer-<version>-macos.zip`
- `CAN-Analyzer-<version>-linux.zip`

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
