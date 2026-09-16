# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Integrated OpenRoadCode automotive application shell."""

from __future__ import annotations
import os
import signal
import tkinter as tk
from collections.abc import Callable
from .context_rail import ContextRail
from apps.orcUi.core_runtime import MapRuntimeIf
from .home_map_panel import HomeMapPanel
from .home_screen import build_home_screen
from .navigation_panel import NavigationPanel
from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from .offroad_panel import OffRoadPanel
from apps.orcUi.orc_theme import ThemeMode, toggle
from .power_dialog import PowerDialog
from .presentation_state import OrcUiPresentationState
from .settings_panel import SettingsPanel
from .screen_builders import (
    build_navigation_screen,
    build_offroad_screen,
    build_placeholder,
    build_settings_screen,
    build_vehicle_screen,
)
from .shell_metrics import TARGET_GEOMETRY, TARGET_HEIGHT, TARGET_WIDTH
from .shell_view import OrcUiShellView
from apps.orcUi.theme_runtime import theme_bundle
from apps.orcUi.trip_presenter import TripPresentationState
from .vehicle_panel import VehiclePanel
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from common.host_config import installed_target, orcui_fullscreen_default
from messaging.contracts.route_guidance import RouteGuidanceStateMessage
from controllers.automotive import AutomotiveTelemetryProfile, EngineAnalysis, VehicleConfiguration
from ui.navigation import (
    MapRequestHandlerIf,
    RouteRequestHandlerIf,
    RouteSimulationRequestHandlerIf,
)
from ui.screen_ui_if import ScreenUiIf
from ui.system import SystemLifecycleRequestHandlerIf, VolumeRequestHandlerIf, VolumeUiIf


class OrcUiApp(VolumeUiIf):
    """Own the integrated Tk shell and presentation state."""

    def __init__(
        self,
        *,
        map_runtime: MapRuntimeIf,
        map_request_handler: MapRequestHandlerIf,
        route_request_handler: RouteRequestHandlerIf,
        route_simulation_handler: RouteSimulationRequestHandlerIf,
        lifecycle_handler: SystemLifecycleRequestHandlerIf,
        telemetry_profile_request: Callable[[AutomotiveTelemetryProfile], None] | None = None,
        vehicle_configuration: VehicleConfiguration = VehicleConfiguration(),
        save_vehicle_configuration: Callable[[VehicleConfiguration], None] | None = None,
    ) -> None:
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._route_request_handler = route_request_handler
        self._route_simulation_handler = route_simulation_handler
        self._lifecycle_handler = lifecycle_handler
        self._telemetry_profile_request = telemetry_profile_request
        self._vehicle_configuration = vehicle_configuration
        self._save_vehicle_configuration = save_vehicle_configuration
        self._vehicle_configuration_observer: Callable[[VehicleConfiguration], None] | None = None
        self._presentation = OrcUiPresentationState()
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
        self._home_radio_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._home_media_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._content: tk.Frame
        self._context_rail: ContextRail | None = None
        self._home_map_panel: HomeMapPanel | None = None
        self._navigation_panel: NavigationPanel | None = None
        self._vehicle_panel: VehiclePanel | None = None
        self._offroad_panel: OffRoadPanel | None = None
        self._settings_panel: SettingsPanel | None = None
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

    def set_home_radio_factory(self, factory: Callable[[tk.Misc], tk.Widget] | None) -> None:
        """Install a radio-owned Home summary without coupling the shell to radio."""
        self._home_radio_factory = factory
        if self._running and self._active_nav == "HOME":
            self._show_home()

    def set_home_media_factory(self, factory: Callable[[tk.Misc], tk.Widget] | None) -> None:
        """Install a media-owned Home summary without coupling the shell to Spotify."""
        self._home_media_factory = factory
        if self._running and self._active_nav == "HOME":
            self._show_home()

    def set_vehicle_configuration_observer(
        self,
        observer: Callable[[VehicleConfiguration], None] | None,
    ) -> None:
        self._vehicle_configuration_observer = observer

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

    def register_screen(self, label: str, screen: ScreenUiIf, *, before: str | None = None) -> None:
        nav_label = label.strip().upper()
        if not nav_label:
            raise ValueError("Screen navigation label must not be empty")
        self._screen_registry[nav_label] = screen
        if nav_label not in self._nav_items:
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
        handler = {
            "HOME": self._show_home,
            "NAVIGATION": self._show_navigation_panel,
            "VEHICLE": self._show_vehicle_panel,
            "SETTINGS": self._show_settings_panel,
        }.get(nav_name)
        self._show_placeholder(nav_name) if handler is None else handler()

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
            self._presentation.apply_vehicle(
                state,
                context=self._context_rail,
                vehicle_panel=self._vehicle_panel,
            )

    def apply_engine_analysis(self, analysis: EngineAnalysis) -> None:
        if not self._closing:
            self._presentation.apply_engine_analysis(
                analysis,
                vehicle_panel=self._vehicle_panel,
            )

    def apply_trip_state(self, state: TripPresentationState) -> None:
        if not self._closing:
            self._presentation.apply_trip(
                state,
                context=self._context_rail,
                vehicle_panel=self._vehicle_panel,
            )

    def apply_position_state(self, state: PositionPresentationState) -> None:
        if not self._closing:
            self._presentation.apply_position(
                state,
                context=self._context_rail,
                offroad_panel=self._offroad_panel,
            )

    def apply_attitude_state(self, state: AttitudePresentationState) -> None:
        if not self._closing:
            self._presentation.apply_attitude(
                state,
                context=self._context_rail,
                offroad_panel=self._offroad_panel,
            )

    def apply_route_guidance_state(
        self,
        message: RouteGuidanceStateMessage,
    ) -> None:
        if self._closing:
            return

        panel = self._navigation_panel
        if panel is None or not panel.winfo_exists():
            return

        data = message.data
        panel.set_route_guidance(
            instruction=data.instruction,
            distance_to_maneuver_m=data.distance_to_maneuver_m,
            distance_remaining_m=data.distance_remaining_m,
            off_route=data.off_route,
            route_complete=data.route_complete,
        )

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        old_signal_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._on_sigint)
        self._running = True
        self._show_home()
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
            self._show_home()
        elif self._active_nav == "SETTINGS":
            self._show_settings_panel()
        else:
            self._apply_theme_to_content()
        active_screen = self._active_screen
        set_theme_mode = getattr(active_screen, "set_theme_mode", None)
        if callable(set_theme_mode):
            set_theme_mode(self._theme_mode)
        if self._active_nav != "HOME":
            self._reload_active_map()

    def _apply_theme_to_content(self) -> None:
        bundle = self._theme
        if self._home_map_panel is not None and self._home_map_panel.winfo_exists():
            self._home_map_panel.set_theme_bundle(bundle)
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.set_theme_bundle(bundle)
        if self._navigation_panel is not None and self._navigation_panel.winfo_exists():
            self._navigation_panel.set_theme_bundle(bundle)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.set_theme_bundle(bundle)
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.set_theme(bundle.ui)

    def _reload_active_map(self) -> None:
        if self._home_map_panel is not None and self._home_map_panel.winfo_exists():
            parent_window_id = self._home_map_panel.map_host_window_id
        elif self._navigation_panel is not None and self._navigation_panel.winfo_exists():
            parent_window_id = self._navigation_panel.map_host_window_id
        else:
            return
        self._map_runtime.stop()
        self._root.after(100, lambda: self._start_map_renderer(parent_window_id))

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
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.release_telemetry_profile()
        self._context_rail = None
        self._home_map_panel = None
        self._navigation_panel = None
        self._vehicle_panel = None
        self._offroad_panel = None
        self._settings_panel = None
        for child in self._content.winfo_children():
            child.destroy()

    def _show_home(self) -> None:
        self._clear_content()
        self._active_nav = "HOME"
        self._paint_nav()
        self._home_map_panel, self._context_rail = build_home_screen(
            self._content,
            map_request_handler=self._map_request_handler,
            theme=self._theme,
            vehicle_state=self._presentation.vehicle,
            trip_state=self._presentation.trip,
            position_state=self._presentation.position,
            attitude_state=self._presentation.attitude,
            on_expand_context=self._show_context_full_panel,
            radio_factory=self._home_radio_factory,
            media_factory=self._home_media_factory,
        )
        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.HOME)
        self._root.update_idletasks()
        self._start_map_renderer(self._home_map_panel.map_host_window_id)

    def _show_navigation_panel(self) -> None:
        self._clear_content()
        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)
        self._active_nav = "NAVIGATION"
        self._paint_nav()
        self._navigation_panel = build_navigation_screen(
            self._content,
            map_request_handler=self._map_request_handler,
            route_request_handler=self._route_request_handler,
            route_simulation_handler=self._route_simulation_handler,
            on_back=self._show_home,
            theme=self._theme,
        )
        self._root.update_idletasks()
        self._start_map_renderer(self._navigation_panel.map_host_window_id)

    def _start_map_renderer(self, parent_window_id: int) -> None:
        try:
            self._map_runtime.launch(parent_window_id)
        except (OSError, RuntimeError) as error:
            print(f"WARNING: map renderer: {type(error).__name__}: {error}")

    def _show_vehicle_panel(self) -> None:
        self._clear_content()
        self._active_nav = "VEHICLE"
        self._paint_nav()
        self._vehicle_panel = build_vehicle_screen(
            self._content,
            on_back=self._show_home,
            on_view_changed=lambda view: self.set_breadcrumb("VEHICLE", view),
            on_telemetry_profile=self._telemetry_profile_request,
            state=self._presentation.vehicle,
            trip_state=self._presentation.trip,
            theme=self._theme,
            vehicle_configuration=self._vehicle_configuration,
            engine_analysis=self._presentation.engine_analysis,
        )

    def _show_settings_panel(self) -> None:
        self._clear_content()
        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)
        self._active_nav = "SETTINGS"
        self._paint_nav()
        self._settings_panel = build_settings_screen(
            self._content,
            vehicle_configuration=self._vehicle_configuration,
            on_vehicle_configuration_changed=self._apply_vehicle_configuration,
            on_back=self._show_home,
            theme=self._theme,
        )

    def _apply_vehicle_configuration(
        self,
        configuration: VehicleConfiguration,
    ) -> None:
        self._vehicle_configuration = configuration
        if self._save_vehicle_configuration is not None:
            self._save_vehicle_configuration(configuration)
        if self._vehicle_configuration_observer is not None:
            self._vehicle_configuration_observer(configuration)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.set_vehicle_configuration(configuration)

    def _show_offroad_panel(self) -> None:
        self._clear_content()
        self._offroad_panel = build_offroad_screen(
            self._content,
            on_back=self._show_home,
            position=self._presentation.position,
            attitude=self._presentation.attitude,
            theme=self._theme,
        )

    def _on_close(self) -> None:
        self._shutdown()

    def _show_context_full_panel(self, name: str) -> None:
        if name == "VEHICLE" or name == "TRIP":
            self._show_vehicle_panel()
            if name == "TRIP" and self._vehicle_panel is not None:
                self._vehicle_panel.show_trip_view()
        elif name == "OFF-ROAD":
            self._show_offroad_panel()
        else:
            self._show_placeholder(name)

    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        build_placeholder(self._content, name, theme=self._theme)
