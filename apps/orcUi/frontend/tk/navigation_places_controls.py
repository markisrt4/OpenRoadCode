# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Widget behavior for contract-bound POI and saved destination controls."""
import tkinter as tk
from ui.navigation import MapMarker, MapMarkerKind
from ui.navigation.poi_models import PoiAction, PoiCategory, PointOfInterest, TransitMode
from ui.navigation.route_types import TravelMode
from .navigation_panel_layout import show_poi_card
from .navigation_poi_actions import execute_poi_action, poll_poi_launch_results

_POI_SEARCH_SETTLE_MS = 750


class NavigationPlacesControls:
    """Present places results and emit semantic requests from navigation widgets."""

    def _destination_shortcut(self, shortcut: str) -> None:
        category = {
            "food": PoiCategory.FOOD,
            "gas": PoiCategory.FUEL,
            "grocery": PoiCategory.GROCERY,
        }.get(shortcut)
        if category is not None:
            self._start_poi_search(category)
            return
        self._places_handler.clear()
        self._request_handler.request_poi_focus(None)
        self._active_poi_render_category = ""
        self._active_poi_search = None
        self._request_handler.request_poi_results((), "")
        favorite = self._places_handler.favorite(shortcut)
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

        self._places_handler.clear()
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
        self._places_handler.clear()
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
        if self._places_closed:
            return
        detail = (
            transit_mode.name.replace("_", " ").casefold()
            if category is PoiCategory.TRANSIT and transit_mode is not TransitMode.ALL
            else category.name.casefold()
        )
        self._shortcut_status.set(f"Searching nearby {detail}…")
        self._places_handler.search(category, transit_mode)

    def _poll_poi_events(self) -> None:
        self._poi_poll_after_id = None
        if self._closed or self._places_closed:
            return
        poll_poi_launch_results(self)
        self._sync_renderer_camera()
        if self._places_handler.poll_camera_interaction():
            # Native mouse/touch gestures happen inside MapLibre, bypassing the
            # Python request handler. Suspend GPS follow so it cannot immediately
            # overwrite the user's manually chosen viewport before the debounced
            # POI refresh asks the renderer for its new bounds.
            self.set_follow_enabled(False)
            self._request_handler.request_follow(False)
            self._schedule_active_poi_refresh()
        result = self._places_handler.poll_search_result()
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
            if result.error:
                self._shortcut_status.set(result.error)
            elif result.count > 0:
                noun = result.category.name.casefold()
                suffix = "s" if result.count != 1 else ""
                self._shortcut_status.set(f"{result.count} {noun} result{suffix}")
            else:
                self._shortcut_status.set(f"No {result.category.name.casefold()} results nearby")
        poi = self._places_handler.poll_selected()
        if poi is not None:
            print(f"[orcUi] showing POI business popup for {poi.name!r}")
            self._show_poi_card(poi)
        if self.winfo_exists():
            self._poi_poll_after_id = self.after(100, self._poll_poi_events)

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

    @property
    def online_actions_allowed(self) -> bool:
        return self._online_mode is None or self._online_mode.online

    def _refresh_poi_action_buttons(self) -> None:
        local_button = self.__dict__.get('_local_3d_button')
        if local_button is not None and local_button.winfo_exists():
            local_button.configure(state=tk.DISABLED if self._poi_launching else tk.NORMAL)
        if self._earth_button is not None and self._earth_button.winfo_exists():
            enabled = self.online_actions_allowed and not self._poi_launching
            self._earth_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)
            icon = self.__dict__.get("_earth_icon")
            if icon is not None:
                self._earth_button.configure(image=icon if enabled else self._earth_offline_icon)
        for button in self._poi_action_buttons:
            if button.winfo_exists():
                button.configure(state=tk.NORMAL if self.online_actions_allowed and not self._poi_launching else tk.DISABLED)

    def _execute_poi_action(self, poi: PointOfInterest, action: PoiAction) -> None:
        execute_poi_action(self, poi, action)


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
