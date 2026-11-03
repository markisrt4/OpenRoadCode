# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Check the selected ADB device before the Waze surface starts scrcpy."""
import subprocess

from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf


class ScrcpyWazeLauncher(InstalledAndroidAppLauncherIf):
    def __init__(self, *, prepare_destination=None):
        self._prepare_destination = prepare_destination

    def launch_installed_app(self, package, *, uri=None):
        if package != 'com.waze':
            return None
        try:
            result = subprocess.run(['adb', 'shell', 'pm', 'path', package],
                                    check=False, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or 'package:' not in result.stdout:
            return None
        if uri is not None and self._prepare_destination is None:
            return None
        if self._prepare_destination is not None:
            self._prepare_destination(uri)
        return 'Waze'
