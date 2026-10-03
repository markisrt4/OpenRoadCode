# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full navigation panel for the integrated ORC cockpit UI."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from ui.weather.radar_ui_if import RadarPalette
from ui.navigation.poi_models import PoiCategory, TransitMode
from ui.navigation import (
    MapRequestHandlerIf,
    RouteRequestHandlerIf,
    RouteRequestHandlerStub,
    RouteSimulationRequestHandlerIf,
)
from ui.theme import ThemeBundle, ThemeMode
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesRequestHandlerIf
from .navigation_radar_controls import NavigationRadarControls
from .navigation_panel_layout import build_navigation_panel
from .navigation_places_controls import NavigationPlacesControls



class NavigationPanel(NavigationPlacesControls, NavigationRadarControls, tk.Frame):
    """Map host, navigation controls, and nearby POI discovery."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        map_request_handler: MapRequestHandlerIf,
        route_request_handler: RouteRequestHandlerIf | None = None,
        route_simulation_handler: RouteSimulationRequestHandlerIf | None = None,
        places_handler: NavigationPlacesRequestHandlerIf,
        on_back: Callable[[], None] | None = None,
        theme_bundle: ThemeBundle | None = None,
        radar_enabled: bool = False,
        radar_frame_time: int | None = None,
        radar_palette: RadarPalette = RadarPalette.UNIVERSAL,
        on_radar_palette_changed: Callable[[RadarPalette], None] | None = None,
        on_radar_toggle: Callable[[bool], None] | None = None,
        on_radar_previous: Callable[[], None] | None = None,
        on_radar_next: Callable[[], None] | None = None,
        on_radar_live: Callable[[], None] | None = None,
        on_radar_play: Callable[[], None] | None = None,
        on_radar_seek: Callable[[int], None] | None = None,
        on_radar_speed: Callable[[float], None] | None = None,
        on_radar_source: Callable[[bool], None] | None = None,
    ) -> None:
        if not isinstance(places_handler, NavigationPlacesRequestHandlerIf):
            raise TypeError("Navigation places require NavigationPlacesRequestHandlerIf")
        self._theme_bundle = theme_bundle or packaged_theme_bundle(ThemeMode.DARK)
        super().__init__(parent, bg=self._theme_bundle.ui.background)
        del on_back
        self._request_handler = map_request_handler
        self._radar_enabled = radar_enabled
        self._radar_frame_time = radar_frame_time
        self._radar_palette = radar_palette
        self._on_radar_palette_changed = on_radar_palette_changed
        self._on_radar_toggle = on_radar_toggle
        self._on_radar_previous = on_radar_previous
        self._on_radar_next = on_radar_next
        self._on_radar_live = on_radar_live
        self._on_radar_play = on_radar_play
        self._on_radar_seek = on_radar_seek
        self._on_radar_speed = on_radar_speed
        self._radar_times = ()
        self._radar_index = None
        self._radar_playing = False
        self._radar_speed = 1.0
        self._radar_forecast = False
        self._on_radar_source = on_radar_source
        self._route_request_handler = route_request_handler or RouteRequestHandlerStub()
        self._route_simulation_handler = route_simulation_handler
        self._places_handler = places_handler
        self._closed = False
        self._places_closed = False
        self._poi_poll_after_id: str | None = None
        self._poi_card: tk.Toplevel | None = None
        self._poi_search_after_id: str | None = None
        self._zoom_level = float(getattr(self._request_handler, "zoom_level", 16.5))
        self._zoom_text = tk.StringVar(value=f"{self._zoom_level:.1f}")
        self._pitch_rad = float(getattr(self._request_handler, "pitch_rad", math.radians(45.0)))
        self._follow_enabled = bool(getattr(self._request_handler, "follow_enabled", True))
        self._shortcut_status = tk.StringVar(value="")
        self._guidance_instruction = tk.StringVar(value="")
        self._guidance_detail = tk.StringVar(value="")
        self._active_poi_render_category = ""
        self._active_poi_search: tuple[PoiCategory, TransitMode] | None = None
        self._route_active = False
        self._simulation_active = False
        self._map_host: tk.Frame
        self._follow_button: tk.Button
        self._radar_button: tk.Button | None = None
        self._simulate_button: tk.Button
        self._cancel_route_button: tk.Button
        self._build()
        self._schedule_renderer_refresh()
        self._poi_poll_after_id = self.after(100, self._poll_poi_events)

    @property
    def map_host_window_id(self) -> int:
        self.update_idletasks()
        return self._map_host.winfo_id()

    def set_theme_bundle(self, theme_bundle: ThemeBundle) -> None:
        self.close_radar_menu()
        self._theme_bundle = theme_bundle
        self.configure(bg=theme_bundle.ui.background)
        for child in self.winfo_children():
            child.destroy()
        self._poi_card = None
        self._build()

    def set_map_request_handler(self, handler: MapRequestHandlerIf | None) -> None:
        if handler is not None:
            self._request_handler = handler

    def set_follow_enabled(self, enabled: bool) -> None:
        self._follow_enabled = enabled
        ui = self._theme_bundle.ui
        self._follow_button.configure(
            text="F" if enabled else "F̸", fg=ui.accent_success if enabled else ui.text
        )

    def close_places(self) -> None:
        """Cancel pending view callbacks and close its places session once."""
        if self._places_closed:
            return
        self._places_closed = True
        for name in ("_poi_poll_after_id", "_poi_search_after_id"):
            callback_id = getattr(self, name)
            if callback_id is not None:
                try:
                    self.after_cancel(callback_id)
                except tk.TclError:
                    pass
                setattr(self, name, None)
        self._places_handler.close()

    def destroy(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.close_radar_menu()
            self.close_places()
        finally:
            super().destroy()

    def _build(self) -> None:
        build_navigation_panel(self)

    def _control(
        self, parent: tk.Misc, text: str, command: Callable[[], None], foreground: str
    ) -> tk.Button:
        ui = self._theme_bundle.ui
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ui.control_background,
            fg=foreground,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", 11, "bold"),
            height=1,
        )

    def _schedule_renderer_refresh(self) -> None:
        for delay_ms in (300, 700, 1200):
            self.after(delay_ms, self._refresh_renderer_state)

    def _refresh_renderer_state(self) -> None:
        refresh = getattr(self._request_handler, "refresh_renderer_state", None)
        if refresh is not None:
            refresh()

    def _update_simulation_button(self) -> None:
        if hasattr(self, "_cancel_route_button"):
            self._cancel_route_button.configure(
                state=tk.NORMAL if self._route_active else tk.DISABLED
            )
        if not hasattr(self, "_simulate_button"):
            return
        if self._route_simulation_handler is None or not self._route_active:
            self._simulate_button.configure(text="Simulate", state=tk.DISABLED)
            return
        self._simulate_button.configure(
            text="Stop simulation" if self._simulation_active else "Simulate",
            state=tk.NORMAL,
        )

    def _cancel_route(self) -> None:
        try:
            if self._simulation_active and self._route_simulation_handler is not None:
                self._route_simulation_handler.request_stop_route_simulation()
            self._route_request_handler.request_cancel_route()
        except Exception as error:
            self._shortcut_status.set(f"Cancel route failed: {error}")
            return
        self._route_active = False
        self._simulation_active = False
        self._guidance_instruction.set("")
        self._guidance_detail.set("")
        self._shortcut_status.set("Route cancelled")
        self._update_simulation_button()

    def _toggle_route_simulation(self) -> None:
        handler = self._route_simulation_handler
        if handler is None or not self._route_active:
            self._shortcut_status.set("No active route to simulate")
            return
        try:
            if self._simulation_active:
                handler.request_stop_route_simulation()
                self._simulation_active = False
                self._shortcut_status.set("Route simulation stopped")
            else:
                handler.request_start_route_simulation(time_scale=60.0)
                self._simulation_active = True
                self._shortcut_status.set("Simulating route at 60×")
        except Exception as error:
            self._shortcut_status.set(f"Simulation failed: {error}")
            self._simulation_active = False
        self._update_simulation_button()

    def set_route_guidance(
        self,
        *,
        instruction: str | None,
        distance_to_maneuver_m: float | None,
        distance_remaining_m: float | None,
        off_route: bool,
        route_complete: bool,
    ) -> None:
        if route_complete:
            self._route_active = False
            self._simulation_active = False
            self._update_simulation_button()
            self._guidance_instruction.set("Arrived")
            self._guidance_detail.set("")
            return
        self._route_active = True
        self._update_simulation_button()
        self._guidance_instruction.set(instruction or "Route active")
        details: list[str] = []
        if distance_to_maneuver_m is not None:
            details.append(_format_distance(distance_to_maneuver_m))
        if distance_remaining_m is not None:
            details.append(f"{_format_distance(distance_remaining_m)} remaining")
        if off_route:
            details.append("OFF ROUTE")
        self._guidance_detail.set("  •  ".join(details))

    def _toggle_follow(self) -> None:
        enabled = not self._follow_enabled
        self.set_follow_enabled(enabled)
        self._request_handler.request_follow(enabled)

    def _pan(self, up: float, right: float) -> None:
        self._map_host.update_idletasks()
        self.set_follow_enabled(False)
        self._request_handler.request_pan_screen(
            right_px=right * max(48, self._map_host.winfo_width() * 0.25),
            up_px=up * max(48, self._map_host.winfo_height() * 0.25),
        )
        self._schedule_active_poi_refresh()

    def _change_zoom(self, delta: float) -> None:
        self._zoom_level = max(1, min(22, self._zoom_level + delta))
        self._zoom_text.set(f"{self._zoom_level:.1f}")
        self._request_handler.request_zoom(self._zoom_level)
        self._schedule_active_poi_refresh()

    def _change_pitch(self, delta_deg: float) -> None:
        pitch_deg = max(0, min(60, math.degrees(self._pitch_rad) + delta_deg))
        self._pitch_rad = math.radians(pitch_deg)
        self.set_follow_enabled(False)
        self._request_handler.request_pitch(self._pitch_rad)

    def _show_3d_view(self) -> None:
        """Tilt and zoom the current viewport around its existing center."""
        self._zoom_level = 17.0
        self._zoom_text.set(f"{self._zoom_level:.1f}")
        self._pitch_rad = math.radians(60.0)
        self.set_follow_enabled(False)
        self._request_handler.request_zoom(self._zoom_level)
        self._request_handler.request_pitch(self._pitch_rad)
        self._schedule_active_poi_refresh()

    def _north_up(self) -> None:
        self.set_follow_enabled(False)
        self._request_handler.request_bearing(0.0)

    def _recenter(self) -> None:
        self.set_follow_enabled(True)
        self._request_handler.request_recenter()


def _format_distance(distance_m: float) -> str:
    if distance_m < 1609.344:
        feet = max(0, round(distance_m * 3.28084 / 50.0) * 50)
        return f"{feet:.0f} ft"
    return f"{distance_m / 1609.344:.1f} mi"
