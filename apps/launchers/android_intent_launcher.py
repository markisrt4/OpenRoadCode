# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Launch native Android packages and URIs from a Termux-hosted ORC process."""
from __future__ import annotations

import shutil
import subprocess


class AndroidIntentLauncherError(RuntimeError):
    """Raised when a native Android intent cannot be launched."""


class AndroidIntentLauncher:
    """Bridge Linux/Termux UI actions into the host Android Activity Manager."""

    def __init__(self, am_executable: str | None = None) -> None:
        self._am_executable = am_executable or self._find_am()

    @staticmethod
    def _find_am() -> str:
        for candidate in ("/system/bin/am", "am"):
            if candidate.startswith("/"):
                if shutil.which(candidate) or __import__("os").path.exists(candidate):
                    return candidate
            elif shutil.which(candidate):
                return candidate
        return "/system/bin/am"

    def launch_package(self, package: str) -> None:
        package = package.strip()
        if not package:
            raise ValueError("Android package name must not be empty")
        self._run(
            "start",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            "-p",
            package,
        )

    def open_uri(self, uri: str) -> None:
        uri = uri.strip()
        if not uri:
            raise ValueError("Android URI must not be empty")
        self._run("start", "-a", "android.intent.action.VIEW", "-d", uri)

    def _run(self, *arguments: str) -> None:
        try:
            result = subprocess.run(
                [self._am_executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise AndroidIntentLauncherError(
                f"Unable to execute Android Activity Manager: {exc}"
            ) from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise AndroidIntentLauncherError(
                f"Android intent failed ({result.returncode}): {detail}"
            )
