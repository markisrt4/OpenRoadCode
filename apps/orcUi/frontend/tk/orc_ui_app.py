# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Integrated OpenRoadCode automotive application shell."""
from __future__ import annotations
import os
import signal
import tkinter as tk
from collections.abc import Callable
from apps.orcUi.core_runtime import MapRuntimeIf
from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from .offroad_panel import OffRoadPanel
from apps.orcUi.orc_theme import ThemeMode, toggle
from .power_dialog import PowerDialog
from .presentation_state import OrcUiPresentationState
from .screen_builders import (
    build_offroad_screen,
    build_placeholder,
)
from .shell_metrics import TARGET_GEOMETRY, TARGET_HEIGHT, TARGET_WIDTH
from .shell_view import OrcUiShellView
from apps.orcUi.theme_runtime import theme_bundle
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from common.host_config import installed_target, orcui_fullscreen_default
from controllers.automotive import AutomotiveTelemetryProfile, EngineAnalysis
from ui.navigation import MapRequestHandlerIf
from ui.screen_ui_if import ScreenUiIf
from ui.system import SystemLifecycleRequestHandlerIf, VolumeRequestHandlerIf, VolumeUiIf

class OrcUiApp(VolumeUiIf):
    """Own the integrated Tk application shell."""
    def __init__(
        self,
        *,
        map_runtime: MapRuntimeIf,
        map_request_handler: MapRequestHandlerIf,
        lifecycle_handler: SystemLifecycleRequestHandlerIf,
        presentation: OrcUiPresentationState,
        telemetry_profile_request: Callable[[AutomotiveTelemetryProfile], None] | None = None,
    ) -> None:
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._lifecycle_handler = lifecycle_handler
        self._telemetry_profile_request = telemetry_profile_request
        self._presentation = presentation
        self._theme_mode = ThemeMode.DARK
        self._theme = theme_bundle(self._theme_mode)
        ui = self._theme.ui
        self._root = tk.Tk()
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
        self._shell: OrcUiShellView | None = None
        self._adsb_enabled = False
        self._aircraft_count = 0
        self._adsb_toggle_handler: Callable[[bool], bool] | None = None
        self._adsb_view_handler: Callable[[], None] | None = None
        self._active_nav = "HOME"
        self._nav_items = ["HOME", "NAVIGATION", "RADIO", "VEHICLE", "VISION", "LIGHTING"]
        self._screen_registry: dict[str, ScreenUiIf] = {}
        self._active_screen: ScreenUiIf | None = None
        self._screen_back_action: Callable[[], None] | None = None
        self._screen_status = ""
        self._content: tk.Frame
        self._offroad_panel: OffRoadPanel | None = None
        self._volume_percent: float | None = None
        self._volume_muted: bool | None = None
        self._volume_request_handler: VolumeRequestHandlerIf | None = None
        self._closing = False
        self._running = False
        self._power_dialog = PowerDialog(
            self._root,
            theme=lambda: self._theme,
            on_exit=self._on_close,
            on_restart=self._restart_ui,
            on_shutdown=self._shutdown_system,
        )
        self._map_runtime.set_theme(self._theme_mode)
        self._build_shell()
    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode
    @property
    def screen_parent(self) -> tk.Misc:
        return self._content
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
    def register_screen(self, label: str, screen: ScreenUiIf, *, before: str | None = None, show_in_navigation: bool = True) -> None:
        nav_label = label.strip().upper()
        if not nav_label:
            raise ValueError("Screen navigation label must not be empty")
        self._screen_registry[nav_label] = screen
        if show_in_navigation and nav_label not in self._nav_items:
            if before is not None and before in self._nav_items:
                self._nav_items.insert(self._nav_items.index(before), nav_label)
            else:
                self._nav_items.append(nav_label)
        self._rebuild_side_nav()
    def navigate_to(self, name: str) -> None:
        """Show a registered screen or built-in shell destination."""
        nav_name = name.strip().upper()
        if not nav_name:
            raise ValueError("Navigation destination must not be empty")
        self._active_nav = nav_name
        self._paint_nav()
        screen = self._screen_registry.get(nav_name)
        if screen is not None:
            screen.show()
            return
        self._deactivate_active_screen()
        self._show_placeholder(nav_name)
    def navigate_to_context(self, name: str) -> None:
        """Open a Home context destination through semantic shell navigation."""
        context_name = name.strip().upper()
        if not context_name:
            raise ValueError("Context destination must not be empty")
        if context_name in {"VEHICLE", "TRIP"}:
            self.navigate_to("VEHICLE")
            if context_name == "TRIP":
                screen = self._screen_registry.get("VEHICLE")
                show_trip_view = getattr(screen, "show_trip_view", None)
                if callable(show_trip_view):
                    show_trip_view()
        elif context_name == "OFF-ROAD":
            self._deactivate_active_screen()
            self._show_offroad_panel()
        else:
            self._deactivate_active_screen()
            self._show_placeholder(context_name)
    def activate_screen(self, screen: ScreenUiIf) -> None:
        previous = self._active_screen
        if previous is screen:
            return
        if previous is not None:
            previous.hide()
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
        self._screen_back_action = action
    def set_screen_status(self, message: str) -> None:
        self._screen_status = message
    def schedule_ui_callback(self, delay_ms: int, callback: Callable[[], None]) -> object:
        return self._root.after(delay_ms, callback)
    def cancel_ui_callback(self, callback_id: object) -> None:
        self._root.after_cancel(callback_id)
    def apply_vehicle_state(self, state: VehiclePresentationState) -> None:
        if not self._closing:
            self._presentation.apply_vehicle(state, vehicle_panel=None)

    def apply_engine_analysis(self, analysis: EngineAnalysis) -> None:
        if not self._closing:
            self._presentation.apply_engine_analysis(
                analysis,
                vehicle_panel=None,
            )

    def apply_trip_state(self, state: TripPresentationState) -> None:
        if not self._closing:
            self._presentation.apply_trip(state, vehicle_panel=None)

    def apply_position_state(self, state: PositionPresentationState) -> None:
        if not self._closing:
            self._presentation.apply_position(state, offroad_panel=self._offroad_panel)

    def apply_attitude_state(self, state: AttitudePresentationState) -> None:
        if not self._closing:
            self._presentation.apply_attitude(state, offroad_panel=self._offroad_panel)
    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        old_signal_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._on_sigint)
        self._running = True
        self.navigate_to("HOME")
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            self._shutdown()
        finally:
            signal.signal(signal.SIGINT, old_signal_handler)
            self._shutdown()
    def _on_sigint(self, _signum, _frame) -> None:
        self._root.after_idle(self._shutdown)
    def _shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._running = False
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        self._map_runtime.stop()
        if self._shell is not None:
            self._shell.close()
        try:
            self._root.destroy()
        except tk.TclError:
            pass
    def _build_shell(self) -> None:
        self._shell = OrcUiShellView(
            self._root,
            theme=self._theme,
            theme_mode=self._theme_mode,
            nav_items=self._nav_items,
            active_nav=self._active_nav,
            on_navigate=self.navigate_to,
            on_power=self._power_dialog.show,
            on_theme_toggle=self._toggle_theme,
            on_volume_down=self._request_volume_down,
            on_volume_up=self._request_volume_up,
            volume_text=self._volume_text(),
        )
        self._content = self._shell.content

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
        self._map_runtime.set_theme(self._theme_mode)
        self._power_dialog.close()
        self._rebuild_shell_theme()
        if self._active_nav == "HOME":
            self.navigate_to("HOME")
        else:
            self._apply_theme_to_content()
        active_screen = self._active_screen
        set_theme_mode = getattr(active_screen, "set_theme_mode", None)
        if callable(set_theme_mode):
            set_theme_mode(self._theme_mode)
    def _apply_theme_to_content(self) -> None:
        bundle = self._theme
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.set_theme(bundle.ui)
    def _deactivate_active_screen(self) -> None:
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        self._screen_back_action = None
        self._screen_status = ""
        self._root.title("OpenRoadCode")
    def _paint_nav(self) -> None:
        if self._shell is not None:
            self._shell.set_active_navigation(self._active_nav)
    def _clear_content(self) -> None:
        self._map_runtime.stop()
        self._offroad_panel = None
        for child in self._content.winfo_children():
            child.destroy()
    def _show_offroad_panel(self) -> None:
        self._clear_content()
        self._offroad_panel = build_offroad_screen(
            self._content,
            on_back=lambda: self.navigate_to("HOME"),
            position=self._presentation.position,
            attitude=self._presentation.attitude,
            theme=self._theme,
        )
    def _on_close(self) -> None:
        self._shutdown()
    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        build_placeholder(self._content, name, theme=self._theme)