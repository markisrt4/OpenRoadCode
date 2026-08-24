# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate lifecycle policy for user-facing external applications."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread

from apps.launchers.app_launcher_if import AppLauncherIf, BrowserDashboardLauncherIf, StatusCallback
from config.application_config import ApplicationConfig, ApplicationsConfig, StartupPolicy


@dataclass(frozen=True, slots=True)
class ManagedApplication:
    """Pair application lifecycle policy with its concrete launcher."""

    config: ApplicationConfig
    launcher: AppLauncherIf


class AppRuntimeManager:
    """Apply lazy, preload, and persistent lifecycle policy to applications."""

    def __init__(self, config: ApplicationsConfig, *, remote_display: str) -> None:
        self._config = config
        self._remote_display = remote_display
        self._apps: dict[str, ManagedApplication] = {}
        self._lock = Lock()
        self._preload_thread: Thread | None = None

    def register(self, key: str, launcher: AppLauncherIf) -> None:
        """Register the launcher for one enabled configured application."""
        app = self._config.app(key)
        if not app.enabled:
            raise ValueError(f"Application {key!r} is disabled")
        with self._lock:
            if key in self._apps:
                raise ValueError(f"Application {key!r} is already registered")
            self._apps[key] = ManagedApplication(config=app, launcher=launcher)

    def start_background_apps(self, set_status: StatusCallback = None) -> None:
        """Start preload and persistent applications without blocking UI startup."""
        with self._lock:
            if self._preload_thread is not None and self._preload_thread.is_alive():
                return
            self._preload_thread = Thread(
                target=self._start_background_apps,
                args=(set_status,),
                name="openroadcode-app-preload",
                daemon=True,
            )
            self._preload_thread.start()

    def launch(self, key: str, set_status: StatusCallback = None) -> None:
        """Present an application to the user."""
        managed = self._managed(key)
        managed.launcher.launch(self._remote_display, set_status)

    def close(self, key: str, set_status: StatusCallback = None) -> None:
        """Close or hide an app according to its configured lifecycle policy."""
        managed = self._managed(key)
        if managed.config.startup in (StartupPolicy.PRELOAD, StartupPolicy.PERSISTENT):
            launcher = managed.launcher
            if isinstance(launcher, BrowserDashboardLauncherIf):
                launcher.close_browser(self._remote_display, set_status)
                return
            if managed.config.startup is StartupPolicy.PERSISTENT:
                return
        managed.launcher.stop(self._remote_display, set_status)

    def stop_all(self, set_status: StatusCallback = None) -> None:
        """Stop all registered applications during OpenRoadCode shutdown."""
        with self._lock:
            apps = tuple(self._apps.values())
        for managed in apps:
            try:
                managed.launcher.stop(self._remote_display, set_status)
            except Exception:
                # Shutdown is best-effort; one external application must not
                # prevent the remaining resources from being released.
                continue

    def is_running(self, key: str) -> bool:
        """Return whether a registered application's launcher is running."""
        return self._managed(key).launcher.is_running()

    def _start_background_apps(self, set_status: StatusCallback) -> None:
        with self._lock:
            apps = tuple(self._apps.values())
        for managed in apps:
            policy = managed.config.startup
            if policy is StartupPolicy.LAZY:
                continue
            try:
                if policy is StartupPolicy.PRELOAD and hasattr(managed.launcher, "prepare"):
                    managed.launcher.prepare()  # type: ignore[attr-defined]
                else:
                    managed.launcher.launch(self._remote_display, set_status)
            except Exception as exc:
                if set_status is not None:
                    set_status(f"Unable to start {managed.config.key}: {exc}")

    def _managed(self, key: str) -> ManagedApplication:
        with self._lock:
            try:
                return self._apps[key]
            except KeyError as exc:
                raise KeyError(f"Application {key!r} is not registered") from exc
