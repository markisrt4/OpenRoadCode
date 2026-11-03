# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compose native Waze navigation without silently opening a website."""
from collections.abc import Callable
from dataclasses import dataclass, field
import logging

from apps.launchers.installed_waydroid_app import InstalledWaydroidAppLauncher
from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from common.logging.structured import event
from common.resource_cleanup import ResourceCleanup, close_resources
from controllers.navigation.waze_app_controller import WazeAppController
from frontends.tk.request_screen import RequestScreen
from ui.navigation import GeoPoint
from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf
from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf
from ui.navigation.waze_request_handler_if import WazeRequestHandlerIf


@dataclass(slots=True)
class WazeComposition(WazeRequestHandlerIf):
    unsubscribe: Callable[[], None]
    native: WazeAppController | None = None
    status: Callable[[str], None] = lambda _message: None
    session_closed: Callable[[], None] = lambda: None
    _closed: bool = field(default=False, init=False)

    def request_open_waze(self) -> None:
        if not self._closed:
            if self.native is not None:
                self.native.request_open_waze()
            else:
                self._unconfigured()

    def request_navigate_waze(self, destination: GeoPoint) -> None:
        if not self._closed:
            if self.native is not None:
                self.native.request_navigate_waze(destination)
            else:
                self._unconfigured()

    def _unconfigured(self):
        self.status('Native Waze is not configured on this device. Set up the Android integration to use Waze.')

    def request_close_waze(self) -> None:
        if self._closed:
            return
        if self.native is not None and (self.native.state.active or self.native.state.launching):
            self.native.request_close_waze()
        else:
            if self.native is not None:
                self.native.cancel()
            self.session_closed()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close_resources(self.native.close if self.native is not None else lambda: None,
                        self.unsubscribe)


def configure_waze(app: OrcUiApp, runtime: OrcUiApplicationRuntime, *,
                   android_app_view: AndroidAppViewRequestHandlerIf | None = None,
                   native_launcher: InstalledAndroidAppLauncherIf | None = None,
                   session_changed=lambda _state: None) -> WazeComposition | None:
    """Retain the existing config enable switch; never construct a Waze browser."""
    if not runtime.waze_url:
        return None
    with ResourceCleanup() as cleanup:
        native = None

        def unavailable():
            event(logging.getLogger('navigation.waze'), logging.WARNING,
                  'app.unavailable', 'Native Waze could not be opened', backend='native')
            app.set_screen_status('Native Waze unavailable. Start the Android session and check that Waze is installed.')

        if android_app_view is not None:
            native = WazeAppController(
                native_launcher if native_launcher is not None else InstalledWaydroidAppLauncher(),
                android_app_view, dispatch_ui=app.dispatch_ui, online=lambda: app.online_mode.online,
                fallback=unavailable, status=app.set_screen_status, session_changed=session_changed,
                session_closed=lambda: app.navigate_to('NAVIGATION'))
            cleanup.callback(native.close)

        def mode_changed(online: bool):
            if not online and native is not None:
                native.cancel()

        unsubscribe = app.online_mode.subscribe(mode_changed)
        cleanup.callback(unsubscribe)
        composition = WazeComposition(unsubscribe, native, app.set_screen_status,
                                      session_closed=lambda: app.navigate_to('NAVIGATION'))
        app.register_screen('WAZE', RequestScreen('waze-entry', composition.request_open_waze), before='RADIO')
        cleanup.release()
        return composition
