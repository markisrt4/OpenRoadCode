# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-aware app-first launcher with desktop web fallbacks."""

from __future__ import annotations

import os
import re
from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf

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
    ) -> None:
        self._browser = browser or DesktopBrowserLauncher()
        self._native = native
        self._waydroid = waydroid or WaydroidLauncher()
        self._app_view = app_view

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
