"""
Version checker for GitHub releases.
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Optional, Dict

from .config import GITHUB_LATEST_RELEASE_API, GITHUB_RELEASES_URL, APP_NAME


_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def _parse_semver(version: str) -> Optional[tuple[int, int, int]]:
    """Parse a simple SemVer string (X.Y.Z or vX.Y.Z)."""
    if not version:
        return None
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _fetch_latest_release(timeout_sec: float = 2.5) -> Optional[Dict]:
    """Fetch latest release metadata from GitHub API."""
    req = urllib.request.Request(
        GITHUB_LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": APP_NAME,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict):
            return data
    return None


def check_for_update(current_version: str, timeout_sec: float = 2.5) -> Optional[Dict]:
    """
    Compare the app version to the latest GitHub release tag.

    ``has_update`` is True only when the remote release is *strictly newer*
    than ``current_version`` (tuple compare on major.minor.patch). If the app
    is already ahead of GitHub (e.g. dev build or unpublished bump),
    ``has_update`` is False — no false "update available" in that case.

    Returns:
        dict with keys:
            has_update: bool
            latest_version: str
            release_url: str
        or None if check could not be completed/parsing failed.
    """
    current = _parse_semver(current_version)
    if current is None:
        return None

    data = _fetch_latest_release(timeout_sec=timeout_sec)
    if not data:
        return None

    tag_name = str(data.get("tag_name", "")).strip()
    latest = _parse_semver(tag_name)
    if latest is None:
        return None

    latest_str = ".".join(str(x) for x in latest)
    release_url = str(data.get("html_url") or GITHUB_RELEASES_URL)

    return {
        "has_update": latest > current,
        "latest_version": latest_str,
        "release_url": release_url,
    }

