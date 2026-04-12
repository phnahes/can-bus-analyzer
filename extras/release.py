#!/usr/bin/env python3
"""
Release helper:
  - bumps version/build in src/__init__.py
  - updates common version markers in README.md
  - creates a release commit and an annotated git tag (vX.Y.Z) pointing to that commit

Usage:
  python3 extras/release.py 1.1.1
  python3 extras/release.py 1.1.1 --build 2026.02
  python3 extras/release.py 1.1.1 --dry-run

After merging a PR (version already correct in tree), tag only:
  python3 extras/release.py 1.2.3 --tag-only
  python3 extras/release.py 1.2.3 --tag-only --force   # replace local tag v1.2.3 if it exists

Pushing tag v*.*.* triggers GitHub Actions: Release Build (macOS + Linux), which creates the GitHub Release.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_INIT = PROJECT_ROOT / "src" / "__init__.py"
README = PROJECT_ROOT / "README.md"


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _run(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), check=check, text=True, capture_output=True)


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["git", *args], cwd=PROJECT_ROOT, check=check)


def _require_clean_worktree() -> None:
    st = _git("status", "--porcelain=v1").stdout.strip()
    if st:
        raise SystemExit(
            "Working tree is not clean. Please commit/stash changes first.\n\n"
            f"git status --porcelain:\n{st}\n"
        )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _replace_once(content: str, pattern: re.Pattern[str], repl: str, *, path: Path) -> str:
    new, n = pattern.subn(repl, content, count=1)
    if n != 1:
        raise SystemExit(f"Expected 1 match for {pattern.pattern} in {path}, got {n}")
    return new


def _read_src_version() -> str:
    content = _read_text(SRC_INIT)
    m = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', content, re.M)
    if not m:
        raise SystemExit(f"Could not parse __version__ in {SRC_INIT}")
    return m.group(1).strip()


def _bump_src_init(version: str, build: str) -> None:
    content = _read_text(SRC_INIT)

    version_pat = re.compile(r'^__version__\s*=\s*"[^\"]+"\s*$', re.M)
    build_pat = re.compile(r'^__build__\s*=\s*"[^\"]+"\s*$', re.M)

    content = _replace_once(content, version_pat, f'__version__ = "{version}"', path=SRC_INIT)
    content = _replace_once(content, build_pat, f'__build__ = "{build}"', path=SRC_INIT)
    _write_text(SRC_INIT, content)


def _bump_readme(version: str) -> None:
    content = _read_text(README)

    # Badge at top: version-1.1.0-blue.svg
    badge_pat = re.compile(r"(https://img\.shields\.io/badge/version-)(\d+\.\d+\.\d+)(-blue\.svg)")
    content, n_badge = badge_pat.subn(rf"\g<1>{version}\g<3>", content, count=1)
    if n_badge != 1:
        raise SystemExit(f"Expected 1 version badge occurrence in {README}, got {n_badge}")

    # "Latest Release: v1.1.0"
    latest_pat = re.compile(r"(\*\*Latest Release:\s*v)(\d+\.\d+\.\d+)(\*\*)")
    content, n_latest = latest_pat.subn(rf"\g<1>{version}\g<3>", content, count=1)
    if n_latest != 1:
        raise SystemExit(f"Expected 1 Latest Release occurrence in {README}, got {n_latest}")

    # "Version: 1.1.0"
    version_pat = re.compile(r"(\*\*Version\*\*:\s*)(\d+\.\d+\.\d+)(\s{2,}$)", re.M)
    content, n_ver = version_pat.subn(rf"\g<1>{version}\g<3>", content, count=1)
    if n_ver != 1:
        raise SystemExit(f"Expected 1 Version field occurrence in {README}, got {n_ver}")

    # Optional: "CAN Gateway Enhancements (v1.1.0)" in Recently Added section.
    gw_pat = re.compile(r"(\*\*CAN Gateway Enhancements\*\*\s*\(v)(\d+\.\d+\.\d+)(\)\s*:)")
    content, n_gw = gw_pat.subn(rf"\g<1>{version}\g<3>", content, count=1)
    # Do not hard fail if section changes; just keep best-effort.
    _ = n_gw

    _write_text(README, content)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Bump version + create git tag for release.")
    parser.add_argument("version", help="New version (SemVer X.Y.Z)")
    parser.add_argument(
        "--build",
        default=None,
        help="Build identifier (YYYY.MM). Default: current year/month.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show actions without changing anything.")
    parser.add_argument("--no-readme", action="store_true", help="Do not update README.md markers.")
    parser.add_argument("--no-tag", action="store_true", help="Do not create git tag.")
    parser.add_argument(
        "--tag-only",
        action="store_true",
        help="Do not bump files or commit; create annotated tag on HEAD. "
        "Verifies src/__init__.py __version__ matches the given version.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="If the tag already exists locally, delete it before creating the new one.",
    )
    args = parser.parse_args(argv)

    version = args.version.strip()
    if not SEMVER_RE.match(version):
        raise SystemExit(f"Invalid version '{version}'. Expected SemVer like 1.2.3")

    build = args.build
    if not build:
        now = _dt.datetime.now()
        build = f"{now.year:04d}.{now.month:02d}"
    build = str(build).strip()
    if not re.match(r"^\d{4}\.\d{2}$", build):
        raise SystemExit(f"Invalid build '{build}'. Expected YYYY.MM like 2026.02")

    tag = f"v{version}"

    # Ensure we're in a git repo and on a branch.
    _git("rev-parse", "--is-inside-work-tree")

    if args.dry_run:
        print("DRY RUN")
    else:
        _require_clean_worktree()

    if args.tag_only:
        if args.no_tag:
            raise SystemExit("--tag-only conflicts with --no-tag.")
        src_ver = _read_src_version()
        if src_ver != version:
            raise SystemExit(
                f"src/__init__.py __version__ is {src_ver!r}, expected {version!r}. "
                "Bump the code or pass the matching version."
            )
        tag_exists = _git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False).returncode == 0
        if tag_exists:
            if not args.force:
                raise SystemExit(
                    f"Tag {tag} already exists. Use --force to replace it locally, "
                    f"then: git push origin {tag} --force"
                )
            if args.dry_run:
                print(f"Would run: git tag -d {tag}")
            else:
                _git("tag", "-d", tag)
        if args.dry_run:
            print(f"Would run: git tag -a {tag} -m {tag}  (on current HEAD, no new commit)")
            print("Next (after merging to main if needed):")
            print("  git push origin main          # or your default branch")
            print(f"  git push origin {tag}         # first release")
            print(f"  git push origin {tag} --force # if replacing remote tag")
            return 0
        _git("tag", "-a", tag, "-m", tag)
        print(f"Annotated tag created: {tag} (points to current HEAD)")
        print("Next:")
        print("  git push origin <default-branch>")
        print(f"  git push origin {tag}")
        print(
            f"  # Re-tagging remote: git push origin :refs/tags/{tag}  OR  git push origin {tag} --force"
        )
        print("Pushing v*.*.* triggers the Release Build workflow (GitHub Release + zip assets).")
        return 0

    if args.no_tag and args.force:
        raise SystemExit("--force applies to tagging; it is unnecessary with --no-tag.")

    # Tag must not exist (unless --force)
    tag_exists = _git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False).returncode == 0
    if tag_exists:
        if not args.force:
            raise SystemExit(
                f"Tag {tag} already exists. Delete it (git tag -d {tag}) or pass --force."
            )
        if not args.dry_run:
            _git("tag", "-d", tag)

    # Apply bumps
    if args.dry_run:
        print(f"Would bump src/__init__.py to version={version} build={build}")
        if not args.no_readme:
            print(f"Would update README.md markers to version={version}")
    else:
        _bump_src_init(version, build)
        if not args.no_readme:
            _bump_readme(version)

    commit_msg = f"chore(release): {tag}"

    if args.dry_run:
        print(f"Would run: git add {SRC_INIT.relative_to(PROJECT_ROOT)}" + ("" if args.no_readme else f" {README.relative_to(PROJECT_ROOT)}"))
        print(f"Would run: git commit -m {commit_msg!r}")
        if not args.no_tag:
            print(f"Would run: git tag -a {tag} -m {tag}")
        print(f"Next: git push origin <branch> && git push origin {tag}")
        return 0

    # Stage and commit
    paths = [str(SRC_INIT.relative_to(PROJECT_ROOT))]
    if not args.no_readme:
        paths.append(str(README.relative_to(PROJECT_ROOT)))
    _git("add", *paths)

    # Refuse empty commits
    if _git("diff", "--cached", "--quiet", check=False).returncode == 0:
        raise SystemExit(
            "No changes staged for commit (version markers already match?). "
            "If the tree is already released, use: python3 extras/release.py "
            f"{version} --tag-only [--force]"
        )

    _git("commit", "-m", commit_msg)

    if not args.no_tag:
        _git("tag", "-a", tag, "-m", tag)

    print(f"Release commit created and tagged: {tag}")
    print("Next:")
    print("  git push origin <default-branch>")
    print(f"  git push origin {tag}")
    print("  (optional local smoke build: ./extras/build.sh)")
    print("Pushing the tag triggers CI: Release Build → GitHub Release with zips.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

