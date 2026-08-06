# Release Process

Step-by-step guide from feature branch to GitHub Release.

---

## 1. Finish the feature branch

During development, keep `## [Unreleased]` in `CHANGELOG.md` up to date with what was added / changed / fixed. Commit everything and make sure the working tree is clean.

```bash
git status   # must be clean
git push -u origin feature/<name>
```

Open a **Pull Request** on GitHub:
- **Base:** `main`  **Head:** `feature/<name>`
- Title and description always in English (see PR template below).

---

## 2. Merge the PR into `main`

Review, approve, and merge via the GitHub UI.

---

## 3. Run the release script

Switch to `main`, pull, and run one command:

```bash
git checkout main && git pull

python3 extras/release.py <X.Y.Z>
# e.g.: python3 extras/release.py 1.2.4
```

The script does **all of the following automatically**:

| Action | File |
|--------|------|
| Bump `__version__` and `__build__` | `src/__init__.py` |
| Update version badge and "Latest Release" line | `README.md` |
| Rename `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD` and insert a fresh empty `[Unreleased]` block | `CHANGELOG.md` |
| Create commit `chore(release): vX.Y.Z` | — |
| Create annotated tag `vX.Y.Z` | — |

Optional flags:
```bash
--dry-run          # preview without changing anything
--build 2026.08    # set __build__ explicitly (default: current YYYY.MM)
--no-changelog     # skip CHANGELOG rename
--no-readme        # skip README markers
--no-tag           # commit only, no tag
--tag-only         # tag HEAD without bumping files (use after manual bump)
--force            # replace existing local tag
```

---

## 4. Push `main` and the tag

```bash
git push origin main
git push origin v<X.Y.Z>
```

Pushing a `v*.*.*` tag automatically triggers **Release Build (macOS + Linux)** in GitHub Actions, which:

1. Builds `CAN-Analyzer-*.zip` on macOS (py2app) and Linux (PyInstaller)
2. Generates release notes from `README.md` + the `[X.Y.Z]` section of `CHANGELOG.md`
3. Creates (or updates) the **GitHub Release** and attaches the zip files

---

## PR title and description template

Always write PR titles and descriptions **in English**.

**Title format:**
```
<type>: <short imperative summary>
```
Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `perf`

**Description template:**
```markdown
## Summary

One paragraph describing what and why.

### Added
- **`path/to/file.py`** — what it does

### Changed
- **`path/to/file.py`** — what changed and why

### Fixed
- **`path/to/file.py`** — what was broken and how it was fixed

### CHANGELOG
`[Unreleased]` section already updated in `CHANGELOG.md`.
```

---

## Quick reference

```
feature branch  ──►  PR (English title + body)  ──►  merge main
                                                          │
                                              python3 extras/release.py X.Y.Z
                                                          │
                                              git push origin main
                                              git push origin vX.Y.Z
                                                          │
                                                   GitHub Actions
                                              build + Release + assets
```

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `release.yml` | Push `v*.*.*` tag | Build macOS + Linux, create GitHub Release |
| `ci-build.yml` | Manual (`workflow_dispatch`) | On-demand build without release |
| `release-notes.yml` | Manual (`workflow_dispatch`) | Rewrite release body only (no rebuild) |
