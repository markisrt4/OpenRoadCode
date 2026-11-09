# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Confirm a curated app exists before presenting its own scrcpy display."""
import subprocess
import re

from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf


class ScrcpyBusinessAppLauncher(InstalledAndroidAppLauncherIf):
    def __init__(self, packages: dict[str, str], *, stop_viewer=lambda: None):
        self._packages = dict(packages)
        self._stop_viewer = stop_viewer

    def launch_installed_app(self, package: str, *, uri: str | None = None) -> str | None:
        if (package not in self._packages or uri is not None or not re.fullmatch(
                r'[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+', package)):
            return None  # Specific-store links need separate verification.
        try:
            result = subprocess.run(['adb', 'shell', 'pm', 'path', package],
                check=False, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode or not any(line.startswith('package:') for line in result.stdout.splitlines()):
            return None
        # The view owns scrcpy startup; do not start/move an activity on the
        # phone's primary display while the presentation request is queued.
        return self._packages[package]

    def resume_installed_app(self, package: str) -> None:
        if package not in self._packages:
            raise ValueError('Unknown business app')

    def stop_installed_app(self, package: str) -> None:
        if package not in self._packages:
            raise ValueError('Unknown business app')
        self._stop_viewer()
