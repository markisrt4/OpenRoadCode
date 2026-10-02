# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform-aware launcher for semantic Android application requests."""

from __future__ import annotations

import os

from apps.launchers.android_bridge_launcher import (
    AndroidBridgeLauncher,
    AndroidBridgeLauncherError,
)
from apps.launchers.waydroid_launcher import WaydroidLauncher, WaydroidLauncherError


class AndroidAppLauncherError(RuntimeError):
    """Raised when neither native Android nor Waydroid can satisfy a request."""


class AndroidAppLauncher:
    """Launch Android destinations from either Android/Termux or Linux/Waydroid."""

    def __init__(
        self,
        *,
        native: AndroidBridgeLauncher | None = None,
        waydroid: WaydroidLauncher | None = None,
    ) -> None:
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
        raise AndroidAppLauncherError(
            "URI fallback is not implemented for Linux/Waydroid yet"
        )

    def open_package_or_uri(self, package: str | None, uri: str) -> str:
        if self._is_native_android():
            try:
                return (self._native or AndroidBridgeLauncher()).open_package_or_uri(
                    package, uri
                )
            except AndroidBridgeLauncherError as exc:
                raise AndroidAppLauncherError(str(exc)) from exc

        if package:
            try:
                self._waydroid.launch_app(package)
                return "waydroid"
            except WaydroidLauncherError as exc:
                raise AndroidAppLauncherError(str(exc)) from exc

        raise AndroidAppLauncherError(
            "No Android package is configured for this POI provider"
        )
