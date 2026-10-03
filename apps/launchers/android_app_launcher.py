# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-aware app-first launcher with desktop web fallbacks."""

from __future__ import annotations

import os

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
    ) -> None:
        self._browser = browser or DesktopBrowserLauncher()
        self._native = native
        self._waydroid = waydroid or WaydroidLauncher()

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
            try:
                return (self._native or AndroidBridgeLauncher()).open_package_or_uri(
                    package, uri
                )
            except AndroidBridgeLauncherError as exc:
                raise AndroidAppLauncherError(str(exc)) from exc

        if package:
            try:
                if any(app.package == package for app in self._waydroid.list_apps()):
                    self._waydroid.launch_app(package)
                    return "Waydroid"
            except WaydroidLauncherError:
                pass

        self.open_uri(uri)
        return "browser"
