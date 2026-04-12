# Packaging (Build standalone executable)

You can build a standalone package so users don't need Python installed.

### Quick build

**macOS / Linux:** (run from project root)
```bash
./extras/build.sh
```
The script creates/activates a venv and installs dependencies if needed.

**Note:** Use `requirements-dev.txt` for building (includes py2app/PyInstaller). Use `requirements.txt` only for running from source.

### Version bump and release

The shipped version lives in `src/__init__.py`:

- **`__version__`** — SemVer string shown in the app and badges (e.g. `1.2.2`).
- **`__build__`** — release/build stamp, convention **`YYYY.MM`** (e.g. `2026.04`).

**Checklist before tagging**

1. **CHANGELOG.md** — Add a dated section for the new version (Keep a Changelog style). Move notes out of `[Unreleased]` as needed. The helper script below does **not** edit this file.
2. **README.md** — The release helper updates the version badge, the “Latest Release” line, and the main “**Version**” field. If you have other lines that embed a version (for example bullets under “Recently Added / Updated”), update those by hand so historical items (e.g. gateway work tied to an older release) keep the correct version label.
3. **Merge / commit** feature work first; tagging steps expect a **clean** `git status` (except `--dry-run`, which skips the clean check).

**Flow A — New version (bump + `chore(release)` commit + tag)**

Use when `__version__` in `src/__init__.py` must change (e.g. **1.2.3 → 1.2.4**).

From the repository root, on the branch that will be released (usually `main`), with a clean tree:

```bash
python3 extras/release.py 1.2.4
```

Optional flags:

- **`--build 2026.04`** — set `__build__` explicitly (default is current calendar year/month).
- **`--dry-run`** — print what would happen without changing files or git.
- **`--no-readme`** — only bump `src/__init__.py`.
- **`--no-tag`** — commit version bump only (no annotated tag).
- **`--force`** — if **`vX.Y.Z`** already exists **locally**, delete it and create it again after the commit (useful when fixing a failed tag).

The script stages `src/__init__.py` and `README.md`, creates a commit `chore(release): vX.Y.Z`, and an annotated tag **`vX.Y.Z`**. If you also changed `CHANGELOG.md`, commit that **before** running the script, or amend the release commit afterward.

**Flow B — Version already set (e.g. after PR merge): tag only**

Use when **`src/__init__.py`** and **README** already show the release version (no extra bump commit).

1. `git checkout main && git pull`
2. Confirm `CHANGELOG.md` has `## [X.Y.Z]` and `__version__` matches.
3. ```bash
   python3 extras/release.py 1.2.3 --tag-only
   ```
   If **`v1.2.3`** already exists locally:  
   `python3 extras/release.py 1.2.3 --tag-only --force`

**Flow C — Replace remote tag `vX.Y.Z` (same version, new commit)**

GitHub UI: delete the release (optional) and remove the tag, **or** force-push the tag.

Locally: after `--tag-only` on the correct commit:

```bash
git push origin vX.Y.Z --force
```

**Publish (all flows)**

```bash
git push origin main
git push origin vX.Y.Z
```

Pushing a **`v*.*.*`** tag triggers the **Release Build (macOS + Linux)** workflow (`.github/workflows/release.yml`), which builds macOS/Linux zips and creates/updates the **GitHub Release** body from `README.md` + `CHANGELOG.md`. Listing the release in the UI is optional; the workflow uses `softprops/action-gh-release` with the tag name you pushed.

**Local build after release**

```bash
./extras/build.sh
```

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
