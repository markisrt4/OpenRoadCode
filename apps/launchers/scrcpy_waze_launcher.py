# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Check the selected ADB device before the Waze surface starts scrcpy."""
import subprocess

from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf


class ScrcpyWazeLauncher(InstalledAndroidAppLauncherIf):
    def launch_installed_app(self, package):
        if package != 'com.waze':
            return None
        try:
            result = subprocess.run(['adb', 'shell', 'pm', 'path', package],
                                    check=False, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return None
        return 'Waze' if result.returncode == 0 and 'package:' in result.stdout else None
