# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate lifecycle policy for user-facing external applications."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread
from typing import TypeVar

from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    BrowserDashboardLauncherIf,
    HideableAppLauncherIf,
    PreloadableAppLauncherIf,
    StatusCallback,
    WindowedAppLauncherIf,
)
from config.application_config import ApplicationConfig, ApplicationsConfig, StartupPolicy


LauncherT = TypeVar("LauncherT", bound=AppLauncherIf)


@dataclass(frozen=True, slots=True)
class ManagedApplication:
    """Pair application lifecycle policy with its concrete launcher."""

    config: ApplicationConfig
    launcher: AppLauncherIf


class AppRuntimeManager:
    """Apply lifecycle, visibility, and mutual-exclusion policy to applications."""

    def __init__(self, config: ApplicationsConfig, *, remote_display: str) -> None:
        self._config = config
        self._remote_display = remote_display
        self._apps: dict[str, ManagedApplication] = {}
        self._visible: set[str] = set()
        self._lock = Lock()
        self._preload_thread: Thread | None = None

    @property
    def remote_display(self) -> str:
        """Return the display used for managed user-facing applications."""
        return self._remote_display

    def register(self, key: str, launcher: AppLauncherIf) -> None:
        app = self._config.app(key)
        if not app.enabled:
            raise ValueError(f"Application {key!r} is disabled")
        with self._lock:
            if key in self._apps:
                raise ValueError(f"Application {key!r} is already registered")
            self._apps[key] = ManagedApplication(config=app, launcher=launcher)

    def launcher(self, key: str, launcher_type: type[LauncherT] | None = None) -> AppLauncherIf | LauncherT:
        """Return a registered launcher, optionally enforcing its concrete capability."""
        launcher = self._managed(key).launcher
        if launcher_type is not None and not isinstance(launcher, launcher_type):
            raise TypeError(
                f"Application {key!r} launcher is {type(launcher).__name__}, "
                f"not {launcher_type.__name__}"
            )
        return launcher

    def start_background_apps(self, set_status: StatusCallback = None) -> None:
        """Warm configured applications sequentially on one background thread."""
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
        self.show(key, set_status)

    def show(self, key: str, set_status: StatusCallback = None) -> None:
        managed = self._managed(key)
        self._close_exclusive_peers(managed, set_status)
        launcher = managed.launcher
        shown = False
        if launcher.is_running() and isinstance(launcher, WindowedAppLauncherIf):
            shown = launcher.show(self._remote_display, set_status)
        if not shown:
            launcher.launch(self._remote_display, set_status)
        with self._lock:
            self._visible.add(key)

    def hide(self, key: str, set_status: StatusCallback = None) -> bool:
        managed = self._managed(key)
        launcher = managed.launcher
        if not isinstance(launcher, HideableAppLauncherIf):
            return False
        hidden = launcher.hide(self._remote_display, set_status)
        if hidden:
            with self._lock:
                self._visible.discard(key)
        return hidden

    def close(self, key: str, set_status: StatusCallback = None) -> None:
        managed = self._managed(key)
        if managed.config.startup in (StartupPolicy.PRELOAD, StartupPolicy.PERSISTENT):
            if self.hide(key, set_status):
                return
            launcher = managed.launcher
            if isinstance(launcher, BrowserDashboardLauncherIf):
                launcher.close_browser(self._remote_display, set_status)
                with self._lock:
                    self._visible.discard(key)
                return
            if managed.config.startup is StartupPolicy.PERSISTENT:
                with self._lock:
                    self._visible.discard(key)
                return
        managed.launcher.stop(self._remote_display, set_status)
        with self._lock:
            self._visible.discard(key)

    def stop_all(self, set_status: StatusCallback = None) -> None:
        with self._lock:
            apps = tuple(self._apps.items())
        for key, managed in apps:
            try:
                managed.launcher.stop(self._remote_display, set_status)
            except Exception:
                continue
            finally:
                with self._lock:
                    self._visible.discard(key)

    def is_running(self, key: str) -> bool:
        return self._managed(key).launcher.is_running()

    def is_visible(self, key: str) -> bool:
        self._managed(key)
        with self._lock:
            return key in self._visible

    def _close_exclusive_peers(self, target: ManagedApplication, set_status: StatusCallback) -> None:
        group = target.config.exclusive_group
        if group is None:
            return
        with self._lock:
            peers = tuple(
                (key, managed)
                for key, managed in self._apps.items()
                if managed is not target and managed.config.exclusive_group == group
            )
        for key, managed in peers:
            try:
                if managed.launcher.is_running():
                    self.close(key, set_status)
            except Exception:
                continue

    def _start_background_apps(self, set_status: StatusCallback) -> None:
        with self._lock:
            apps = tuple(self._apps.values())
        for managed in apps:
            policy = managed.config.startup
            if policy is StartupPolicy.LAZY:
                continue
            try:
                if policy is StartupPolicy.PRELOAD:
                    self._prewarm(managed, set_status)
                else:
                    self.show(managed.config.key, set_status)
            except Exception as exc:
                if set_status is not None:
                    set_status(f"Unable to start {managed.config.key}: {exc}")

    def _prewarm(self, managed: ManagedApplication, set_status: StatusCallback) -> None:
        launcher = managed.launcher
        if isinstance(launcher, PreloadableAppLauncherIf):
            launcher.prepare()
            return
        if isinstance(launcher, WindowedAppLauncherIf):
            launcher.launch(self._remote_display, set_status)
            if launcher.hide(self._remote_display, set_status):
                with self._lock:
                    self._visible.discard(managed.config.key)
                return
            launcher.stop(self._remote_display, set_status)
            return
        launcher.launch(self._remote_display, set_status)

    def _managed(self, key: str) -> ManagedApplication:
        with self._lock:
            try:
                return self._apps[key]
            except KeyError as exc:
                raise KeyError(f"Application {key!r} is not registered") from exc
