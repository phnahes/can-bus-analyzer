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

    # Tag must not exist
    tag_exists = _git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False).returncode == 0
    if tag_exists:
        raise SystemExit(f"Tag {tag} already exists.")

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
        return 0

    # Stage and commit
    paths = [str(SRC_INIT.relative_to(PROJECT_ROOT))]
    if not args.no_readme:
        paths.append(str(README.relative_to(PROJECT_ROOT)))
    _git("add", *paths)

    # Refuse empty commits
    if _git("diff", "--cached", "--quiet", check=False).returncode == 0:
        raise SystemExit("No changes staged for commit (version markers already set?).")

    _git("commit", "-m", commit_msg)

    if not args.no_tag:
        _git("tag", "-a", tag, "-m", tag)

    print(f"Release commit created and tagged: {tag}")
    print("Next:")
    print("  ./extras/build.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

