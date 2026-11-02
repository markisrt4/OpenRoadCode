# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Launch a Waydroid package without starting a desktop-browser fallback."""
from apps.launchers.waydroid_launcher import WaydroidLauncher, WaydroidLauncherError
from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf


class InstalledWaydroidAppLauncher(InstalledAndroidAppLauncherIf):
    def __init__(self, waydroid=None):
        self._waydroid = waydroid if waydroid is not None else WaydroidLauncher()

    def launch_installed_app(self, package):
        try:
            app = next((app for app in self._waydroid.list_apps() if app.package == package), None)
            if app is None:
                return None
            self._waydroid.launch_app(package)
            return app.name
        except WaydroidLauncherError:
            return None
