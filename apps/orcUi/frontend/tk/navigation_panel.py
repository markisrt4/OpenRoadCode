# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full navigation panel for the integrated ORC cockpit UI."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.launchers.android_intent_launcher import AndroidIntentLauncherError
from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from controllers.navigation.map_favorites import MapFavorites
from controllers.poi.android_poi_action_executor import AndroidPoiActionExecutor
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from controllers.poi import (
    PoiAction,
    PoiActionKind,
    PoiCategory,
    PoiSearchController,
    PointOfInterest,
    TransitMode,
)
from ui.navigation import (
    MapMarker,
    MapMarkerKind,
    MapRequestHandlerIf,
    RouteRequestHandlerIf,
    RouteRequestHandlerStub,
    RouteSimulationRequestHandlerIf,
)
from ui.navigation.route_types import TravelMode
from ui.theme import ThemeBundle, ThemeMode
from .shell_metrics import FONT_CONTROL, FONT_SMALL, FONT_TINY
from .navigation_panel_layout import build_navigation_panel, show_poi_card

_POI_SEARCH_SETTLE_MS = 750


class NavigationPanel(tk.Frame):
    """Map host, navigation controls, and nearby POI discovery."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        map_request_handler: MapRequestHandlerIf,
        route_request_handler: RouteRequestHandlerIf | None = None,
        route_simulation_handler: RouteSimulationRequestHandlerIf | None = None,
        map_favorites: MapFavorites | None = None,
        on_back: Callable[[], None] | None = None,
        theme_bundle: ThemeBundle | None = None,
        poi_action_executor: PoiActionExecutorIf | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle or packaged_theme_bundle(ThemeMode.DARK)
        super().__init__(parent, bg=self._theme_bundle.ui.background)
        del on_back
        self._request_handler = map_request_handler
        self._route_request_handler = route_request_handler or RouteRequestHandlerStub()
        self._route_simulation_handler = route_simulation_handler
        self._map_favorites = map_favorites or MapFavorites()
        self._poi_action_executor = poi_action_executor or AndroidPoiActionExecutor()
        self._poi_controller = PoiSearchController()
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
        self._simulate_button: tk.Button
        self._cancel_route_button: tk.Button
        self._build()
        self._schedule_renderer_refresh()
        self.after(100, self._poll_poi_events)

    @property
    def map_host_window_id(self) -> int:
        self.update_idletasks()
        return self._map_host.winfo_id()

    def set_theme_bundle(self, theme_bundle: ThemeBundle) -> None:
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

    def destroy(self) -> None:
        if self._poi_search_after_id is not None:
            try:
                self.after_cancel(self._poi_search_after_id)
            except tk.TclError:
                pass
            self._poi_search_after_id = None
        self._poi_controller.close()
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

    def _destination_shortcut(self, shortcut: str) -> None:
        category = {
            "food": PoiCategory.FOOD,
            "gas": PoiCategory.FUEL,
            "grocery": PoiCategory.GROCERY,
        }.get(shortcut)
        if category is not None:
            self._start_poi_search(category)
            return
        self._poi_controller.clear()
        self._request_handler.request_poi_focus(None)
        self._active_poi_render_category = ""
        self._active_poi_search = None
        self._request_handler.request_poi_results((), "")
        favorite = self._map_favorites.home if shortcut == "home" else self._map_favorites.work
        if favorite is None:
            self._shortcut_status.set(f"{shortcut.title()} location not configured")
            self.after(2500, lambda: self._shortcut_status.set(""))
            return
        try:
            self._route_request_handler.request_start_route(
                favorite.position,
                (),
                TravelMode.AUTO,
            )
        except Exception as error:
            self._shortcut_status.set(f"Route failed: {error}")
            self.after(4000, lambda: self._shortcut_status.set(""))
            return
        self._route_active = True
        self._simulation_active = False
        self._update_simulation_button()
        self._shortcut_status.set(f"Routing to {favorite.name}")

    def _clear_poi_search(self) -> None:
        """Clear the active POI search and remove its rendered markers."""
        if self._poi_search_after_id is not None:
            try:
                self.after_cancel(self._poi_search_after_id)
            except tk.TclError:
                pass
            self._poi_search_after_id = None

        self._poi_controller.clear()
        self._request_handler.request_poi_focus(None)
        self._active_poi_render_category = ""
        self._active_poi_search = None
        self._request_handler.request_poi_results((), "")
        self._shortcut_status.set("")

        if self._poi_card is not None and self._poi_card.winfo_exists():
            self._poi_card.destroy()
        self._poi_card = None

    def _start_poi_search(
        self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL
    ) -> None:
        if not bool(getattr(self._request_handler, "camera_initialized", False)):
            self._shortcut_status.set("Position unavailable — nearby search needs a GPS fix")
            return
        if self._poi_search_after_id is not None:
            try:
                self.after_cancel(self._poi_search_after_id)
            except tk.TclError:
                pass
            self._poi_search_after_id = None
        category_name = category.name.casefold()
        self._poi_controller.clear()
        self._request_handler.request_poi_focus(None)
        self._active_poi_render_category = _poi_render_category(category, transit_mode)
        self._active_poi_search = (category, transit_mode)
        self._request_handler.request_poi_results((), self._active_poi_render_category)
        detail = (
            transit_mode.name.replace("_", " ").casefold()
            if category is PoiCategory.TRANSIT and transit_mode is not TransitMode.ALL
            else category_name
        )
        self._shortcut_status.set(f"Loading nearby {detail}…")
        self._poi_search_after_id = self.after(
            _POI_SEARCH_SETTLE_MS, lambda: self._issue_poi_search(category, transit_mode)
        )

    def _schedule_active_poi_refresh(self) -> None:
        """Debounce a viewport refresh while a POI category remains active."""
        if self._active_poi_search is None:
            return
        if self._poi_search_after_id is not None:
            try:
                self.after_cancel(self._poi_search_after_id)
            except tk.TclError:
                pass
        category, transit_mode = self._active_poi_search
        self._poi_search_after_id = self.after(
            _POI_SEARCH_SETTLE_MS, lambda: self._issue_poi_search(category, transit_mode)
        )

    def _issue_poi_search(
        self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL
    ) -> None:
        self._poi_search_after_id = None
        detail = (
            transit_mode.name.replace("_", " ").casefold()
            if category is PoiCategory.TRANSIT and transit_mode is not TransitMode.ALL
            else category.name.casefold()
        )
        self._shortcut_status.set(f"Searching nearby {detail}…")
        self._poi_controller.search(category, transit_mode)

    def _poll_poi_events(self) -> None:
        if self._poi_controller.poll_camera_interaction():
            # Native mouse/touch gestures happen inside MapLibre, bypassing the
            # Python request handler. Suspend GPS follow so it cannot immediately
            # overwrite the user's manually chosen viewport before the debounced
            # POI refresh asks the renderer for its new bounds.
            self.set_follow_enabled(False)
            self._request_handler.request_follow(False)
            self._schedule_active_poi_refresh()
        result = self._poi_controller.poll_search_result()
        if result is not None:
            markers = tuple(
                MapMarker(
                    marker_id=poi.poi_id,
                    position=poi.position,
                    kind=MapMarkerKind.SEARCH_RESULT,
                    label=poi.name,
                )
                for poi in result.pois
            )
            self._request_handler.request_poi_results(markers, self._active_poi_render_category)
            if result.count > 0:
                noun = result.category.name.casefold()
                suffix = "s" if result.count != 1 else ""
                self._shortcut_status.set(f"{result.count} {noun} result{suffix}")
            else:
                self._shortcut_status.set(f"No {result.category.name.casefold()} results nearby")
        poi = self._poi_controller.poll_selected()
        if poi is not None:
            print(f"[orcUi] showing POI business popup for {poi.name!r}")
            self._show_poi_card(poi)
        if self.winfo_exists():
            self.after(100, self._poll_poi_events)

    def _show_poi_card(self, poi: PointOfInterest) -> None:
        show_poi_card(self, poi)

    def _navigate_to_poi(self, poi: PointOfInterest) -> None:
        try:
            self._route_request_handler.request_start_route(
                poi.position,
                (),
                TravelMode.AUTO,
            )
            self._route_active = True
            self._simulation_active = False
            self._update_simulation_button()
            self._shortcut_status.set(f"Routing to {poi.name}")
        except Exception as exc:
            self._shortcut_status.set(f"Route failed: {exc}")
        if self._poi_card is not None and self._poi_card.winfo_exists():
            self._poi_card.destroy()

    def _execute_poi_action(self, poi: PointOfInterest, action: PoiAction) -> None:
        try:
            status = self._poi_action_executor.execute(poi, action)
            self._shortcut_status.set(status)
        except (AndroidIntentLauncherError, ValueError) as exc:
            self._shortcut_status.set(f"Launch failed: {exc}")
        if self._poi_card is not None and self._poi_card.winfo_exists():
            self._poi_card.destroy()
        self.after(3500, lambda: self._shortcut_status.set(""))

    def _update_simulation_button(self) -> None:
        if hasattr(self, "_cancel_route_button"):
            self._cancel_route_button.configure(
                state=tk.NORMAL if self._route_active else tk.DISABLED
            )
        if not hasattr(self, "_simulate_button"):
            return
        if self._route_simulation_handler is None or not self._route_active:
            self._simulate_button.configure(text="SIM DRIVE", state=tk.DISABLED)
            return
        self._simulate_button.configure(
            text="STOP SIM" if self._simulation_active else "SIM DRIVE",
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


def _poi_render_category(category: PoiCategory, transit_mode: TransitMode) -> str:
    if category is not PoiCategory.TRANSIT:
        return category.name.casefold()
    if transit_mode is TransitMode.BUS:
        return "bus"
    if transit_mode is TransitMode.RAIL:
        return "rail"
    if transit_mode is TransitMode.TRAM_SUBWAY:
        return "tram-subway"
    return "transit"


def _format_distance(distance_m: float) -> str:
    if distance_m < 1609.344:
        feet = max(0, round(distance_m * 3.28084 / 50.0) * 50)
        return f"{feet:.0f} ft"
    return f"{distance_m / 1609.344:.1f} mi"
