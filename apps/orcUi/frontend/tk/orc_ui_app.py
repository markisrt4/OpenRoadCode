# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Integrated OpenRoadCode automotive application shell."""

from __future__ import annotations

import os
import signal
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import PositionPresentationState
from apps.orcUi.notification_dispatcher import NotificationDispatcher
from apps.orcUi.orc_theme import toggle
from apps.orcUi.performance_status import PerformanceStatus
from apps.orcUi.theme_runtime import theme_bundle
from common.host_config import installed_target, orcui_borderless_default, orcui_fullscreen_default
from common.resource_cleanup import ResourceCleanup, close_resources
from frontends.common.ui_callback_queue import UiCallbackQueue
from ui.notification_if import Notification
from ui.radio import AircraftMenuRequestHandlerIf, AircraftMenuUiState
from ui.screen_ui_if import ScreenUiIf
from ui.system import SystemLifecycleRequestHandlerIf, VolumeRequestHandlerIf, VolumeUiIf
from ui.system.online_mode_if import OnlineModeIf
from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeMode
from ui.ui_widget import UiWidget
from ui.weather import WeatherAlertUiEvent

from .error_dialog import ErrorDialog
from .performance_overlay import PerformanceOverlay
from .power_dialog import PowerDialog
from .screen_builders import build_placeholder
from .shell_construction import build_shell, format_volume, toggle_shell_theme
from .shell_metrics import TARGET_GEOMETRY, TARGET_HEIGHT, TARGET_WIDTH
from .shell_view import OrcUiShellView
from .software_update_dialog import SoftwareUpdateDialog
from .ui_callback_mixin import UiCallbackMixin


class OrcUiApp(UiCallbackMixin, VolumeUiIf, UiWidget):
    """Own the integrated Tk application shell."""

    def __init__(
        self,
        *,
        lifecycle_handler: SystemLifecycleRequestHandlerIf,
        online_mode: OnlineModeIf | None = None,
        application_name: str = "OpenRoadCode",
    ) -> None:
        self._lifecycle_handler = lifecycle_handler
        self._application_name = application_name
        self._theme_mode = ThemeMode.DARK
        self._theme = theme_bundle(self._theme_mode)
        ui = self._theme.ui
        self._closing = False
        self._callback_queue = UiCallbackQueue()
        self._ui_callbacks: set[str] = set()
        self._active_screen: ScreenUiIf | None = None
        self._shell: OrcUiShellView | None = None
        self._power_dialog: PowerDialog | None = None
        self._root = tk.Tk()
        self._performance_overlay = PerformanceOverlay(self._root)
        self._error_dialog = ErrorDialog(self._root, lambda: self._theme)
        self._software_update_dialog = SoftwareUpdateDialog(self._root, lambda: self._theme)
        self.notification_sink = NotificationDispatcher(
            self.dispatch_ui,
            self._present_notification,
        )
        self._root.bind_all("<Control-Shift-P>", self._toggle_performance_overlay)
        with ResourceCleanup() as cleanup:
            cleanup.callback(self.shutdown)
            self._root.title(self._application_name)
            target = installed_target()
            fullscreen = orcui_fullscreen_default()
            self._borderless = orcui_borderless_default() and not fullscreen
            default_geometry = "1024x600" if target == "termux" else TARGET_GEOMETRY
            geometry = os.environ.get("ORCUI_GEOMETRY", default_geometry)
            if fullscreen:
                self._root.attributes("-fullscreen", True)
            else:
                self._root.geometry(geometry)
                self._root.resizable(True, True)
                if target != "termux":
                    self._root.minsize(TARGET_WIDTH, TARGET_HEIGHT)
                if self._borderless:
                    self._root.overrideredirect(True)
                    self._root.bind("<Escape>", self._restore_window_decorations)
            self._root.configure(bg=ui.background)
            self._adsb_enabled = False
            self._adsb_simulation = False
            self._aircraft_handler: AircraftMenuRequestHandlerIf | None = None
            self._aircraft_count = 0
            self._active_nav = ""
            self._diagnostics_return = "HOME"
            self._initial_destination: str | None = None
            self._nav_items: list[str] = []
            self._screen_registry: dict[str, ScreenUiIf] = {}
            self._content: tk.Frame
            self._volume_percent: float | None = None
            self._volume_muted: bool | None = None
            self._volume_request_handler: VolumeRequestHandlerIf | None = None
            self._theme_change_handler: Callable[[ThemeMode], None] | None = None
            self._settings_action: Callable[[], None] | None = None
            self._power_dialog = PowerDialog(
                self._root,
                theme=lambda: self._theme,
                on_exit=self._on_close,
                on_restart=self._restart_ui,
                on_shutdown=self._shutdown_system,
            )
            self.online_mode = online_mode
            self._connectivity_toggle: Callable[[], None] | None = None
            self._internet_status: bool | None = None
            self._build_shell()
            self.schedule_ui_callback(16, self._drain_ui_callbacks)
            cleanup.release()

    def set_connectivity_handler(self, handler: Callable[[], None]) -> None:
        """Bind semantic toggle. @param handler Request callback."""
        self._connectivity_toggle = handler

    def _toggle_online_mode(self) -> None:
        if self._connectivity_toggle is not None:
            self._connectivity_toggle()

    def set_online_status(self, online: bool, reachable: bool | None) -> None:
        """Present mode. @param online Effective mode. @param reachable Internet observation."""
        self._internet_status = reachable
        if self._shell is not None:
            self._shell.set_online_status(online, reachable)
            self._shell.set_weather_online(online)

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode

    @property
    def screen_parent(self) -> tk.Misc:
        return self._content

    def set_theme_change_handler(
        self,
        handler: Callable[[ThemeMode], None] | None,
    ) -> None:
        """Connect semantic theme changes to composition-owned consumers."""
        self._theme_change_handler = handler

    def set_settings_action(self, action: Callable[[], None]) -> None:
        """Connect the shell settings control to composition-owned navigation."""
        self._settings_action = action

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        """Connect the shell volume controls to a semantic request handler."""
        self._volume_request_handler = handler

    def set_volume(self, volume_percent: float | None) -> None:
        """Display normalized system volume state in the shell."""
        self._volume_percent = (
            None if volume_percent is None else max(0.0, min(100.0, volume_percent))
        )
        self._paint_volume()

    def set_muted(self, muted: bool | None) -> None:
        """Display system mute state in the shell."""
        self._volume_muted = muted
        self._paint_volume()

    def set_initial_destination(self, label: str) -> None:
        """Select the composition-owned destination shown when the shell starts."""
        destination = label.strip().upper()
        if not destination:
            raise ValueError("Initial destination must not be empty")
        self._initial_destination = destination

    def register_navigation_destination(self, label: str, *, before: str | None = None) -> None:
        """Add a shell navigation destination without requiring a screen."""
        nav_label = label.strip().upper()
        if not nav_label:
            raise ValueError("Navigation label must not be empty")
        if nav_label not in self._nav_items:
            if before is not None and before in self._nav_items:
                self._nav_items.insert(self._nav_items.index(before), nav_label)
            else:
                self._nav_items.append(nav_label)
        self._rebuild_side_nav()

    def register_navigation_action(self, label: str, action: Callable[[], None]) -> None:
        if not hasattr(self, "_navigation_actions"):
            self._navigation_actions = {}
        self._navigation_actions[label.strip().upper()] = action

    def _navigate_from_sidebar(self, label: str) -> None:
        action = getattr(self, "_navigation_actions", {}).get(label)
        if action is not None:
            action()
        else:
            self.navigate_to(label)

    def register_screen(
        self,
        label: str,
        screen: ScreenUiIf,
        *,
        before: str | None = None,
        show_in_navigation: bool = True,
        navigation_label: str | None = None,
    ) -> None:
        nav_label = label.strip().upper()
        if not nav_label:
            raise ValueError("Screen navigation label must not be empty")
        self._screen_registry[nav_label] = screen
        if not hasattr(self, "_screen_navigation_labels"):
            self._screen_navigation_labels = {}
        self._screen_navigation_labels[nav_label] = navigation_label or nav_label
        if show_in_navigation:
            self.register_navigation_destination(navigation_label or nav_label, before=before)

    def navigate_to(self, name: str) -> None:
        """Show a registered screen or built-in shell destination."""
        nav_name = name.strip().upper()
        if not nav_name:
            raise ValueError("Navigation destination must not be empty")
        if nav_name == "DIAGNOSTICS" and self._active_nav != "DIAGNOSTICS":
            self._diagnostics_return = self._active_nav or "HOME"
        self.set_screen_status("")
        if self._shell is not None:
            self._shell.set_back_action(None)
        self._active_nav = nav_name
        self._paint_nav()
        screen = self._screen_registry.get(nav_name)
        if screen is not None:
            screen.show()
            return
        self._deactivate_active_screen()
        self._show_placeholder(nav_name)

    def close_diagnostics(self) -> None:
        """Return to the destination that opened Diagnostics."""
        self.navigate_to(self._diagnostics_return)

    def _toggle_performance_overlay(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._performance_overlay.set_visible(not self._performance_overlay.visible)

    def update_performance_overlay(self, snapshot: SystemDiagnosticsSnapshot) -> None:
        self._performance_overlay.update(snapshot)

    def performance_overlay_enabled(self) -> bool:
        return bool(self._performance_overlay.visible)

    def set_performance_overlay_enabled(self, enabled: bool) -> None:
        self._performance_overlay.set_visible(enabled)

    def toggle_performance_overlay(self) -> None:
        self._toggle_performance_overlay()

    def set_performance_status(self, status: PerformanceStatus) -> None:
        """Present computing-unit health in persistent shell chrome."""
        if self._shell is not None:
            self._shell.set_performance_status(status)

    def set_position_state(self, state: PositionPresentationState) -> None:
        """Present semantic vehicle-position availability in shell chrome."""
        if self._shell is not None:
            self._shell.set_position_state(state)

    def activate_screen(self, screen: ScreenUiIf) -> None:
        previous = self._active_screen
        if previous is screen:
            return
        if previous is not None:
            previous.hide()
        if self._shell is not None:
            self._shell.set_back_action(None)
        self._active_screen = screen

    def clear_screen_content(self) -> None:
        self._clear_content()

    def set_screen_title(self, title: str) -> None:
        title = title.strip()
        base = getattr(self, "_application_name", "OpenRoadCode")
        self._root.title(base if not title else f"{base} | {title}")
        if self._shell is not None:
            leaf = title.upper()
            if not leaf or leaf == self._active_nav:
                self._shell.set_breadcrumb(
                    getattr(self, "_screen_navigation_labels", {}).get(
                        self._active_nav, self._active_nav
                    )
                )
            else:
                self._shell.set_breadcrumb(
                    getattr(self, "_screen_navigation_labels", {}).get(
                        self._active_nav, self._active_nav
                    ),
                    leaf,
                )

    def set_screen_back_action(self, action: Callable[[], None]) -> None:
        """Show the active screen's semantic back action in persistent chrome."""
        if self._shell is not None:
            self._shell.set_back_action(action)

    def _present_notification(self, notification: Notification) -> None:
        """Present on Tk's UI thread; never paint in an embedded viewport."""
        self._error_dialog.show(notification.title, notification.message)

    def show_error(self, title: str, message: str) -> None:
        """Present a shell-level error without painting over native content."""
        self._error_dialog.show(title, message)

    def offer_software_update(self, revision: str, on_accept: Callable[[], None]) -> None:
        """Present an available ORC checkout update for user approval."""
        self._software_update_dialog.show(revision, on_accept)

    def set_screen_status(self, message: str) -> None:
        if self._shell is not None:
            self._shell.set_status(message)

    def run(self) -> None:
        old_signal_handler = signal.getsignal(signal.SIGINT)

        def restore_signal_handler() -> None:
            signal.signal(signal.SIGINT, old_signal_handler)

        with ResourceCleanup() as cleanup:
            cleanup.callback(self.shutdown)
            cleanup.callback(restore_signal_handler)
            try:
                self._root.protocol("WM_DELETE_WINDOW", self._on_close)
                signal.signal(signal.SIGINT, self._on_sigint)
                initial_destination = self._initial_destination
                if initial_destination is None:
                    raise RuntimeError("Initial navigation destination is not configured")
                self.navigate_to(initial_destination)
                self._root.mainloop()
            except KeyboardInterrupt:
                pass

    def _restore_window_decorations(self, _event: object | None = None) -> None:
        """Leave borderless mode without closing the ORC process."""
        if not self._borderless:
            return
        self._borderless = False
        self._root.overrideredirect(False)
        self._root.resizable(True, True)
        self._root.minsize(TARGET_WIDTH, TARGET_HEIGHT)

    def _on_sigint(self, _signum: int, _frame: object) -> None:
        self._root.after_idle(self._shutdown)

    def _shutdown(self) -> None:
        self.shutdown()

    def shutdown(self) -> None:
        """Reject queued work and attempt all frontend cleanup once on its thread."""
        if self._closing:
            return
        self._closing = True
        self._callback_queue.close()
        active_screen, self._active_screen = self._active_screen, None
        callbacks = tuple(self._ui_callbacks)
        close_resources(
            *(lambda token=token: self.cancel_ui_callback(token) for token in callbacks),
            *([active_screen.hide] if active_screen is not None else []),
            *([self._power_dialog.close] if self._power_dialog is not None else []),
            *([self._shell.close] if self._shell is not None else []),
            self._performance_overlay.close,
            self._destroy_root,
        )

    def _destroy_root(self) -> None:
        try:
            self._root.destroy()
        except tk.TclError:
            pass

    def _build_shell(self) -> None:
        build_shell(self, OrcUiShellView)

    def set_weather_status(self, text: str) -> None:
        """Display current Weather summary in persistent shell chrome."""
        if self._shell is not None:
            self._shell.set_weather_status(text)

    def present_weather_alert(self, alert: WeatherAlertUiEvent | None) -> None:
        """Forward shell-level Weather alert state to persistent chrome."""
        if self._shell is not None:
            self._shell.show_weather_alert(alert)

    def set_breadcrumb(self, *parts: str) -> None:
        if self._shell is not None:
            self._shell.set_breadcrumb(*parts)

    def _rebuild_side_nav(self) -> None:
        if self._shell is not None:
            self._shell.rebuild_navigation()

    def set_aircraft_request_handler(self, handler: AircraftMenuRequestHandlerIf | None) -> None:
        self._aircraft_handler = handler
        if self._shell is not None:
            self._shell.set_aircraft_request_handler(handler)

    def set_adsb_state(
        self, *, enabled: bool, aircraft_count: int = 0, simulation: bool = False
    ) -> None:
        self._adsb_enabled = bool(enabled)
        self._adsb_simulation = simulation
        self._aircraft_count = max(0, int(aircraft_count))
        if self._shell is not None:
            self._shell.set_aircraft_state(
                AircraftMenuUiState(
                    self._adsb_enabled,
                    self._aircraft_count,
                    self._adsb_simulation,
                )
            )

    def _rebuild_shell_theme(self) -> None:
        if self._shell is not None:
            self._shell.rebuild(theme=self._theme, theme_mode=self._theme_mode)
            if self.online_mode is not None:
                self.set_online_status(self.online_mode.online, self._internet_status)

    def _open_settings(self) -> None:
        action = self._settings_action
        if action is not None:
            action()

    def _request_volume_up(self) -> None:
        handler = self._volume_request_handler
        if handler is not None:
            handler.request_volume_up()

    def _request_volume_down(self) -> None:
        handler = self._volume_request_handler
        if handler is not None:
            handler.request_volume_down()

    def _volume_text(self) -> str:
        return format_volume(self._volume_percent, self._volume_muted)

    def _paint_volume(self) -> None:
        if self._shell is not None:
            self._shell.set_volume_text(self._volume_text())

    def _restart_ui(self) -> None:
        self._lifecycle_handler.request_restart_ui()
        self._shutdown()

    def _shutdown_system(self) -> None:
        self._lifecycle_handler.request_poweroff()
        self._shutdown()

    def _toggle_theme(self) -> None:
        toggle_shell_theme(self, toggle, theme_bundle)

    def _deactivate_active_screen(self) -> None:
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        if self._shell is not None:
            self._shell.set_back_action(None)
            self._shell.set_status("")
        self._root.title(getattr(self, "_application_name", "OpenRoadCode"))

    def _paint_nav(self) -> None:
        if self._shell is not None:
            self._shell.set_active_navigation(
                getattr(self, "_screen_navigation_labels", {}).get(
                    self._active_nav, self._active_nav
                )
            )

    def _clear_content(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()

    def _on_close(self) -> None:
        self._shutdown()

    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        build_placeholder(self._content, name, theme=self._theme)
