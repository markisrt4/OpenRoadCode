# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Check the selected ADB device before the Waze surface starts scrcpy."""
import subprocess

from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf


class ScrcpyWazeLauncher(InstalledAndroidAppLauncherIf):
    def __init__(self, *, prepare_destination=None, stop_viewer=lambda: None):
        self._prepare_destination = prepare_destination
        self._stop_viewer = stop_viewer

    def resume_installed_app(self, package):
        """The retained viewer owns the existing Android virtual display."""

    def stop_installed_app(self, package):
        try:
            result = subprocess.run(['adb', 'shell', 'am', 'force-stop', package],
                                    capture_output=True, text=True, timeout=5, check=True)
            if 'Exception' in result.stdout + result.stderr or 'Error:' in result.stdout + result.stderr:
                raise RuntimeError('Android refused to close Waze')
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError('Could not close Waze on the selected Android device') from error
        self._stop_viewer()

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
