"""
Module for handling GitHub repository cloning and cleanup.
"""

import os
import subprocess
import tempfile
import shutil
from typing import Tuple


def is_github_url(path: str) -> bool:
    """Returns True if the input looks like a GitHub URL."""
    return (
        path.startswith("https://github.com")
        or path.startswith("http://github.com")
        or path.startswith("github.com")
        or path.endswith(".git")
    )


def clone_repo(url: str, shallow: bool = True) -> Tuple[str, str]:
    """
    Clones a GitHub repo to a temp directory.
    Returns a tuple of (temp_directory_path, normalized_url).
    Uses shallow clone (depth=1) by default to save time and bandwidth.
    Raises RuntimeError if clone fails.
    """
    # Normalize URL
    original_url = url
    if not url.startswith("http"):
        url = "https://" + url
    if not url.endswith(".git"):
        url = url.rstrip("/") + ".git"

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="codescope_")

    try:
        cmd = ["git", "clone"]
        if shallow:
            cmd.extend(["--depth", "1"])
        cmd.extend([url, temp_dir])

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Git clone failed: {result.stderr}")
        return temp_dir, original_url
    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(
            "Clone timed out after 120 seconds. Try a smaller repository."
        )


def cleanup_repo(temp_dir: str) -> None:
    """Removes the temp directory after analysis."""
    shutil.rmtree(temp_dir, ignore_errors=True)
