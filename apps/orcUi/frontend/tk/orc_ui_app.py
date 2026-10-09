# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Integrated OpenRoadCode automotive application shell."""
from __future__ import annotations
import os
import signal
import tkinter as tk
from common.resource_cleanup import ResourceCleanup, close_resources
from frontends.common.ui_callback_queue import UiCallbackQueue
from ui.system.online_mode_if import OnlineModeIf
from collections.abc import Callable
from apps.orcUi.performance_status import PerformanceStatus
from apps.orcUi.orc_theme import toggle
from ui.theme import ThemeMode
from .power_dialog import PowerDialog
from .screen_builders import (
    build_placeholder,
)
from .shell_metrics import TARGET_GEOMETRY, TARGET_HEIGHT, TARGET_WIDTH
from .shell_view import OrcUiShellView
from apps.orcUi.theme_runtime import theme_bundle
from common.host_config import installed_target, orcui_fullscreen_default
from ui.screen_ui_if import ScreenUiIf
from ui.system import SystemLifecycleRequestHandlerIf, VolumeRequestHandlerIf, VolumeUiIf
from ui.weather import WeatherAlertUiEvent
from ui.ui_widget import UiWidget

class OrcUiApp(VolumeUiIf, UiWidget):
    """Own the integrated Tk application shell."""
    def __init__(
        self,
        *,
        lifecycle_handler: SystemLifecycleRequestHandlerIf,
        online_mode: OnlineModeIf | None = None,
    ) -> None:
        self._lifecycle_handler = lifecycle_handler
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
        with ResourceCleanup() as cleanup:
            cleanup.callback(self.shutdown)
            self._root.title("OpenRoadCode")
            target = installed_target()
            fullscreen = orcui_fullscreen_default()
            default_geometry = "1024x600" if target == "termux" else TARGET_GEOMETRY
            geometry = os.environ.get("ORCUI_GEOMETRY", default_geometry)
            if fullscreen:
                self._root.attributes("-fullscreen", True)
            else:
                self._root.geometry(geometry)
                self._root.resizable(True, True)
                if target != "termux":
                    self._root.minsize(TARGET_WIDTH, TARGET_HEIGHT)
            self._root.configure(bg=ui.background)
            self._adsb_enabled = False
            self._aircraft_count = 0
            self._adsb_toggle_handler: Callable[[bool], bool] | None = None
            self._adsb_view_handler: Callable[[], None] | None = None
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
            None
            if volume_percent is None
            else max(0.0, min(100.0, volume_percent))
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

    def register_screen(self, label: str, screen: ScreenUiIf, *, before: str | None = None, show_in_navigation: bool = True) -> None:
        nav_label = label.strip().upper()
        if not nav_label:
            raise ValueError("Screen navigation label must not be empty")
        self._screen_registry[nav_label] = screen
        if show_in_navigation:
            self.register_navigation_destination(nav_label, before=before)
    def navigate_to(self, name: str) -> None:
        """Show a registered screen or built-in shell destination."""
        nav_name = name.strip().upper()
        if not nav_name:
            raise ValueError("Navigation destination must not be empty")
        if nav_name == "DIAGNOSTICS" and self._active_nav != "DIAGNOSTICS":
            self._diagnostics_return = self._active_nav or "HOME"
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

    def set_performance_status(self, status: PerformanceStatus) -> None:
        """Present computing-unit health in persistent shell chrome."""
        if self._shell is not None:
            self._shell.set_performance_status(status)

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
        self._root.title("OpenRoadCode" if not title else f"OpenRoadCode | {title}")
        if self._shell is not None:
            leaf = title.upper()
            if not leaf or leaf == self._active_nav:
                self._shell.set_breadcrumb(self._active_nav)
            else:
                self._shell.set_breadcrumb(self._active_nav, leaf)
    def set_screen_back_action(self, action: Callable[[], None]) -> None:
        """Show the active screen's semantic back action in persistent chrome."""
        if self._shell is not None:
            self._shell.set_back_action(action)
    def set_screen_status(self, message: str) -> None:
        if self._shell is not None:
            self._shell.set_status(message)
    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Queue work from any thread without calling Tk; discard it after shutdown."""
        self._callback_queue.dispatch_ui(callback)

    def _drain_ui_callbacks(self) -> None:
        try:
            self._callback_queue.dispatch_pending()
        finally:
            if not self._closing:
                self.schedule_ui_callback(16, self._drain_ui_callbacks)

    def schedule_ui_callback(self, delay_ms: int, callback: Callable[[], None]) -> object:
        """Schedule a timer from the frontend thread only; closed timers are inert."""
        if self._closing:
            return None

        def invoke() -> None:
            self._ui_callbacks.discard(token)
            if not self._closing:
                callback()

        token = self._root.after(delay_ms, invoke)
        self._ui_callbacks.add(token)
        return token

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel a timer on the frontend thread, tolerating destroyed Tk resources."""
        if not isinstance(callback_id, str):
            return
        self._ui_callbacks.discard(callback_id)
        try:
            self._root.after_cancel(callback_id)
        except tk.TclError:
            pass

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
            self._destroy_root,
        )

    def _destroy_root(self) -> None:
        try:
            self._root.destroy()
        except tk.TclError:
            pass

    def _build_shell(self) -> None:
        if self._power_dialog is None:
            raise RuntimeError("Power dialog must be initialized before shell construction")
        self._shell = OrcUiShellView(
            self._root,
            theme=self._theme,
            theme_mode=self._theme_mode,
            nav_items=self._nav_items,
            active_nav=self._active_nav,
            on_navigate=self.navigate_to,
            on_power=self._power_dialog.show,
            on_online_toggle=self._toggle_online_mode,
            on_theme_toggle=self._toggle_theme,
            on_settings=self._open_settings,
            on_volume_down=self._request_volume_down,
            on_volume_up=self._request_volume_up,
            volume_text=self._volume_text(),
        )
        self._content = self._shell.content
        if self.online_mode is not None:
            self.set_online_status(self.online_mode.online, self._internet_status)

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

    def set_adsb_handlers(
        self,
        *,
        on_toggle: Callable[[bool], bool],
        on_view: Callable[[], None],
    ) -> None:
        self._adsb_toggle_handler = on_toggle
        self._adsb_view_handler = on_view
        if self._shell is not None:
            self._shell.set_adsb_handlers(on_toggle=on_toggle, on_view=on_view)

    def set_adsb_state(self, *, enabled: bool, aircraft_count: int = 0) -> None:
        self._adsb_enabled = bool(enabled)
        self._aircraft_count = max(0, int(aircraft_count))
        if self._shell is not None:
            self._shell.set_adsb_state(
                enabled=self._adsb_enabled,
                aircraft_count=self._aircraft_count,
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
        icon = "🔇" if self._volume_muted else "🔊"
        if self._volume_percent is None:
            return f"{icon} --"
        return f"{icon} {round(self._volume_percent)}%"
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
        self._theme_mode = toggle(self._theme_mode)
        self._theme = theme_bundle(self._theme_mode)
        active_screen = self._active_screen
        set_theme_mode = getattr(active_screen, "set_theme_mode", None)
        if active_screen is not None and not callable(set_theme_mode):
            # Stop embedded renderers before their native host widgets are destroyed.
            self._deactivate_active_screen()
        theme_change_handler = self._theme_change_handler
        if theme_change_handler is not None:
            theme_change_handler(self._theme_mode)
        if self._power_dialog is not None:
            self._power_dialog.close()
        self._rebuild_shell_theme()
        if callable(set_theme_mode):
            set_theme_mode(self._theme_mode)
        elif active_screen is not None:
            self.navigate_to(self._active_nav)
    def _deactivate_active_screen(self) -> None:
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        if self._shell is not None:
            self._shell.set_back_action(None)
            self._shell.set_status("")
        self._root.title("OpenRoadCode")
    def _paint_nav(self) -> None:
        if self._shell is not None:
            self._shell.set_active_navigation(self._active_nav)
    def _clear_content(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()
    def _on_close(self) -> None:
        self._shutdown()
    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        build_placeholder(self._content, name, theme=self._theme)
