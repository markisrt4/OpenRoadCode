# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-aware app-first launcher with desktop web fallbacks."""

from __future__ import annotations

import os
import re
import subprocess
from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf
from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf

from apps.launchers.android_bridge_launcher import (
    AndroidBridgeLauncher,
    AndroidBridgeLauncherError,
)
from apps.launchers.desktop_browser_launcher import DesktopBrowserLauncher, DesktopBrowserLauncherError
from tools.map_builder.builder.web_urls import valid_website
from apps.launchers.waydroid_launcher import WaydroidLauncher, WaydroidLauncherError


class AndroidAppLauncherError(RuntimeError):
    """Raised when an app or web destination cannot be requested."""


class AndroidAppLauncher:
    """Use Android Bridge on Termux, or Waydroid and the browser on Linux."""

    def __init__(
        self,
        *,
        native: AndroidBridgeLauncher | None = None,
        waydroid: WaydroidLauncher | None = None,
        browser: DesktopBrowserLauncher | None = None,
        app_view: AndroidAppViewRequestHandlerIf | None = None,
        installed_apps: InstalledAndroidAppLauncherIf | None = None,
    ) -> None:
        self._browser = browser or DesktopBrowserLauncher()
        self._native = native
        self._waydroid = waydroid or WaydroidLauncher()
        self._app_view = app_view
        self._installed_apps = installed_apps

    def _open_embedded_native_app(self, package: str | None) -> str | None:
        if package and self._installed_apps is not None and self._app_view is not None:
            name = self._installed_apps.launch_installed_app(package)
            if name is not None:
                self._app_view.request_show_android_app(name, package)
                return 'embedded Android app'
        return None

    def package_installed(self, package: str) -> bool | None:
        """Read availability without opening an app; None means unverifiable."""
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+', package):
            return None
        if not self._is_native_android():
            try:
                return any(app.package == package for app in self._waydroid.list_apps())
            except WaydroidLauncherError:
                return None
        # A positive local PackageManager answer needs no wireless ADB session.
        # Android may filter results for the Termux UID: a local negative is
        # inconclusive, so only the existing shell/ADB query can prove absence.
        try:
            local = subprocess.run(['/system/bin/pm', 'path', package],
                capture_output=True, text=True, timeout=2, check=False)
            if local.returncode == 0 and any(line.startswith('package:') for line in local.stdout.splitlines()):
                return True
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            result = subprocess.run(['adb', 'shell', 'pm', 'path', package],
                capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode == 0 and any(line.startswith('package:') for line in result.stdout.splitlines()):
            return True
        if result.returncode in (0, 1) and not result.stdout.strip() and not result.stderr.strip():
            return False
        return None

    @staticmethod
    def _is_native_android() -> bool:
        return os.path.exists("/system/bin/am")

    def open_uri(self, uri: str) -> None:
        if self._is_native_android():
            try:
                (self._native or AndroidBridgeLauncher()).open_uri(uri)
            except AndroidBridgeLauncherError as exc:
                raise AndroidAppLauncherError(str(exc)) from exc
            return
        try:
            self._browser.open_uri(uri)
        except DesktopBrowserLauncherError as exc:
            raise AndroidAppLauncherError(str(exc)) from exc

    def open_package_or_uri(self, package: str | None, uri: str) -> str:
        uri = valid_website(uri)
        if uri is None:
            raise ValueError("POI destination must be a valid HTTP or HTTPS URL")
        if self._is_native_android():
            embedded = self._open_embedded_native_app(package)
            if embedded:
                return embedded
            try:
                return (self._native or AndroidBridgeLauncher()).open_package_or_uri(
                    package, uri
                )
            except AndroidBridgeLauncherError as exc:
                raise AndroidAppLauncherError(str(exc)) from exc

        if package:
            try:
                app = next((app for app in self._waydroid.list_apps() if app.package == package), None)
                if app is not None:
                    self._waydroid.launch_app(package)
                    if self._app_view is not None:
                        self._app_view.request_show_android_app(app.name, package)
                    return "Waydroid"
            except WaydroidLauncherError:
                pass

        self.open_uri(uri)
        return "browser"

    def open_android_app(self, package: str) -> str:
        """Open an installed app or its listing in Android; never install silently."""
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+', package):
            raise ValueError('Invalid Android package')
        listing = 'https://play.google.com/store/apps/details?id=' + package
        if self._is_native_android():
            embedded = self._open_embedded_native_app(package)
            if embedded:
                return embedded
            try:
                (self._native or AndroidBridgeLauncher()).open_package_or_uri(package, listing)
            except AndroidBridgeLauncherError as error:
                raise AndroidAppLauncherError(str(error)) from error
            return 'Android app or Google Play listing'
        try:
            apps = self._waydroid.list_apps()
            installed = next((app for app in apps if app.package == package), None)
            if installed is not None:
                self._waydroid.launch_app(package)
                if self._app_view is not None:
                    self._app_view.request_show_android_app(installed.name, package)
                return installed.name
            store = next((app for app in apps if app.package == 'com.android.vending'), None)
            if store is None:
                raise AndroidAppLauncherError('This app is not installed. Enable Google Play in Waydroid, install it, then retry.')
            self._waydroid.launch_uri('market://details?id=' + package)
            if self._app_view is not None:
                self._app_view.request_show_android_app('Google Play — install app', store.package)
            return 'Google Play — review and install the app, then return to this POI'
        except WaydroidLauncherError as error:
            raise AndroidAppLauncherError(str(error)) from error
