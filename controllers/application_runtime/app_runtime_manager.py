# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate lifecycle policy for user-facing external applications."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, RLock, Thread
from typing import TypeVar
import logging

from common.logging.lifecycle import logged_action
from common.logging.structured import current_operation, event, operation

from ui.system.app_launcher_if import (AppLauncherIf, BrowserDashboardLauncherIf, HideableAppLauncherIf, PreloadableAppLauncherIf, StatusCallback, WindowedAppLauncherIf)
from config.application_config import ApplicationConfig, ApplicationsConfig, StartupPolicy

LauncherT = TypeVar("LauncherT", bound=AppLauncherIf)
LOGGER = logging.getLogger("runtime.apps")


def _app_context(manager, key, *args, **kwargs):
    if isinstance(key, ManagedApplication):
        key = key.config.key
    with manager._lock:
        return {"app": key if key in manager._apps else None}


def app_action(action: str):
    return logged_action("runtime.apps", "app.action", action, context=_app_context)


@dataclass(frozen=True, slots=True)
class ManagedApplication:
    config: ApplicationConfig
    launcher: AppLauncherIf


class AppRuntimeManager:
    """Apply lifecycle, visibility, target routing, and exclusivity policy."""

    def __init__(self, config: ApplicationsConfig, *, remote_display: str) -> None:
        self._config = config
        self._fallback_display = remote_display
        self._apps: dict[str, ManagedApplication] = {}
        self._visible: set[str] = set()
        self._lock = Lock()
        self._lifecycle_locks: dict[str, RLock] = {}
        self._preload_thread: Thread | None = None
        self._observed_running: dict[str, bool] = {}

    @property
    def remote_display(self) -> str:
        return self._fallback_display

    def display_for(self, key: str) -> str:
        managed = self._managed(key)
        target = self._config.target_for_app(managed.config)
        if target is None:
            return self._fallback_display
        return target.display

    def register(self, key: str, launcher: AppLauncherIf) -> None:
        app = self._config.app(key)
        if not app.enabled:
            raise ValueError(f"Application {key!r} is disabled")
        with self._lock:
            if key in self._apps:
                raise ValueError(f"Application {key!r} is already registered")
            self._apps[key] = ManagedApplication(config=app, launcher=launcher)
            self._lifecycle_locks[key] = RLock()
        event(
            LOGGER,
            logging.DEBUG,
            "app.registered",
            "Application registered",
            app=key,
            startup_policy=app.startup.value,
        )

    def launcher(
        self, key: str, launcher_type: type[LauncherT] | None = None
    ) -> AppLauncherIf | LauncherT:
        launcher = self._managed(key).launcher
        if launcher_type is not None and not isinstance(launcher, launcher_type):
            raise TypeError(
                f"Application {key!r} launcher is {type(launcher).__name__}, not {launcher_type.__name__}"
            )
        return launcher

    def start_background_apps(self, set_status: StatusCallback = None) -> None:
        with self._lock:
            if self._preload_thread is not None and self._preload_thread.is_alive():
                return
            with operation(current_operation()) as operation_id:
                event(
                    LOGGER,
                    logging.INFO,
                    "preload.requested",
                    "Background application startup requested",
                )
            self._preload_thread = Thread(
                target=self._start_background_apps,
                args=(set_status, operation_id),
                name="openroadcode-app-preload",
                daemon=True,
            )
            with operation(operation_id):
                try:
                    self._preload_thread.start()
                except Exception as error:
                    event(
                        LOGGER,
                        logging.ERROR,
                        "preload.start_failed",
                        "Background startup worker failed to start",
                        exception_type=type(error).__name__,
                    )
                    raise

    def launch(self, key: str, set_status: StatusCallback = None) -> None:
        self.show(key, set_status)

    @app_action("show")
    def show(self, key: str, set_status: StatusCallback = None) -> None:
        managed = self._managed(key)
        self._close_exclusive_peers(managed, set_status)
        with self._lifecycle_lock(key):
            display = self.display_for(key)
            launcher = managed.launcher
            shown = False
            if launcher.is_running() and isinstance(launcher, WindowedAppLauncherIf):
                shown = launcher.show(display, set_status)
            if not shown:
                launcher.launch(display, set_status)
            with self._lock:
                self._visible.add(key)

    @app_action("stop")
    def stop(self, key: str, set_status: StatusCallback = None) -> None:
        """Stop a managed application regardless of preload/persistent policy."""
        with self._lifecycle_lock(key):
            managed = self._managed(key)
            display = self.display_for(key)
            managed.launcher.stop(display, set_status)
            with self._lock:
                self._visible.discard(key)

    @app_action("restart")
    def restart(self, key: str, set_status: StatusCallback = None) -> None:
        with self._lifecycle_lock(key):
            managed = self._managed(key)
            display = self.display_for(key)
            if managed.launcher.is_running():
                managed.launcher.stop(display, set_status)
            with self._lock:
                self._visible.discard(key)
            self.show(key, set_status)

    @app_action("hide")
    def hide(self, key: str, set_status: StatusCallback = None) -> bool:
        with self._lifecycle_lock(key):
            managed = self._managed(key)
            launcher = managed.launcher
            if not isinstance(launcher, HideableAppLauncherIf):
                return False
            hidden = launcher.hide(self.display_for(key), set_status)
            if hidden:
                with self._lock:
                    self._visible.discard(key)
            return hidden

    @app_action("close")
    def close(self, key: str, set_status: StatusCallback = None) -> None:
        with self._lifecycle_lock(key):
            managed = self._managed(key)
            display = self.display_for(key)
            if managed.config.startup in (StartupPolicy.PRELOAD, StartupPolicy.PERSISTENT):
                if self.hide(key, set_status):
                    return
                launcher = managed.launcher
                if isinstance(launcher, BrowserDashboardLauncherIf):
                    launcher.close_browser(display, set_status)
                    with self._lock:
                        self._visible.discard(key)
                    return
                if managed.config.startup is StartupPolicy.PERSISTENT:
                    with self._lock:
                        self._visible.discard(key)
                    return
            managed.launcher.stop(display, set_status)
            with self._lock:
                self._visible.discard(key)

    @logged_action("runtime.apps", "app.action", "stop_all")
    def stop_all(self, set_status: StatusCallback = None) -> None:
        with self._lock:
            apps = tuple(self._apps.items())
        failed_count = 0
        for key, managed in apps:
            try:
                with self._lifecycle_lock(key):
                    managed.launcher.stop(self.display_for(key), set_status)
            except Exception as error:
                failed_count += 1
                event(
                    LOGGER,
                    logging.ERROR,
                    "app.cleanup_failed",
                    "Application cleanup failed",
                    app=key,
                    exception_type=type(error).__name__,
                )
                continue
            finally:
                with self._lock:
                    self._visible.discard(key)
        event(
            LOGGER,
            logging.WARNING if failed_count else logging.INFO,
            "app.cleanup_finished",
            "Application cleanup pass finished",
            app_count=len(apps),
            failed_count=failed_count,
        )

    def is_running(self, key: str) -> bool:
        running = self._managed(key).launcher.is_running()
        with self._lock:
            previous = self._observed_running.get(key)
            self._observed_running[key] = running
        if previous is not None and previous != running:
            event(
                LOGGER,
                logging.INFO,
                "app.running_changed",
                "Observed application running state changed",
                app=key,
                running=running,
            )
        return running

    def is_visible(self, key: str) -> bool:
        self._managed(key)
        with self._lock:
            return key in self._visible

    def _close_exclusive_peers(
        self, target: ManagedApplication, set_status: StatusCallback
    ) -> None:
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
            except Exception as error:
                event(
                    LOGGER,
                    logging.WARNING,
                    "app.exclusive_close_failed",
                    "Exclusive peer close failed",
                    app=key,
                    exception_type=type(error).__name__,
                )
                continue

    def _start_background_apps(
        self, set_status: StatusCallback, operation_id: str | None = None
    ) -> None:
        with operation(operation_id or current_operation()):
            try:
                self._preload_apps(set_status)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "preload.worker_failed",
                    "Background startup worker failed",
                    exception_type=type(error).__name__,
                )
                raise

    def _preload_apps(self, set_status: StatusCallback) -> None:
        with self._lock:
            apps = tuple(self._apps.values())
        failed_count = completed_count = 0
        for managed in apps:
            policy = managed.config.startup
            if policy is StartupPolicy.LAZY:
                continue
            try:
                if policy is StartupPolicy.PRELOAD:
                    self._prewarm(managed, set_status)
                else:
                    self.show(managed.config.key, set_status)
                completed_count += 1
            except Exception as exc:
                failed_count += 1
                event(
                    LOGGER,
                    logging.ERROR,
                    "app.preload_failed",
                    "Background application startup failed",
                    app=managed.config.key,
                    exception_type=type(exc).__name__,
                )
                if set_status is not None:
                    set_status(f"Unable to start {managed.config.key}: {exc}")
        event(
            LOGGER,
            logging.WARNING if failed_count else logging.INFO,
            "preload.finished",
            "Background application startup pass finished",
            completed_count=completed_count,
            failed_count=failed_count,
        )

    @app_action("prewarm")
    def _prewarm(self, managed: ManagedApplication, set_status: StatusCallback) -> None:
        key = managed.config.key
        with self._lifecycle_lock(key):
            launcher = managed.launcher
            display = self.display_for(key)
            if isinstance(launcher, PreloadableAppLauncherIf):
                launcher.prepare(display, set_status)
                with self._lock:
                    self._visible.discard(key)
                return
            if isinstance(launcher, WindowedAppLauncherIf):
                launcher.launch(display, set_status)
                if launcher.hide(display, set_status):
                    with self._lock:
                        self._visible.discard(key)
                    return
                launcher.stop(display, set_status)
                return
            launcher.launch(display, set_status)

    def _managed(self, key: str) -> ManagedApplication:
        with self._lock:
            try:
                return self._apps[key]
            except KeyError as exc:
                raise KeyError(f"Application {key!r} is not registered") from exc

    def _lifecycle_lock(self, key: str) -> RLock:
        with self._lock:
            try:
                return self._lifecycle_locks[key]
            except KeyError as exc:
                raise KeyError(f"Application {key!r} is not registered") from exc
