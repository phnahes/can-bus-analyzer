"""
Application identity constants.
"""

APP_NAME = "CAN Analyzer"
GITHUB_REPO = "phnahes/can-bus-analyzer"
REPO_URL = f"https://github.com/{GITHUB_REPO}"
GITHUB_RELEASES_URL = f"{REPO_URL}/releases"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

__all__ = [
    "APP_NAME",
    "REPO_URL",
    "GITHUB_REPO",
    "GITHUB_RELEASES_URL",
    "GITHUB_LATEST_RELEASE_API",
]
