"""Route semantic map requests while retaining native map camera state."""

from ui.navigation import MapRequestHandlerIf
from ui.navigation.poi_overlay_state import PoiOverlayState


class MapPlatformRequests(MapRequestHandlerIf):
    def __init__(
        self, native: MapRequestHandlerIf, send_earth, send_pois=lambda _state: None
    ) -> None:
        self._native = native
        self._send_earth = send_earth
        self._send_pois = send_pois
        self._poi_state = PoiOverlayState()

    @property
    def camera_initialized(self):
        return bool(getattr(self._native, "camera_initialized", False))

    @property
    def zoom_level(self):
        return getattr(self._native, "zoom_level", 16.5)

    @property
    def pitch_rad(self):
        return getattr(self._native, "pitch_rad", 0.0)

    @property
    def follow_enabled(self):
        return getattr(self._native, "follow_enabled", True)

    def _request(self, name, *args, **kwargs):
        getattr(self._native, name)(*args, **kwargs)
        self._send_earth(name, args, kwargs)

    def request_follow(self, enabled):
        self._request("request_follow", enabled)

    def request_recenter(self):
        self._request("request_recenter")

    def request_center_on(self, position):
        self._request("request_center_on", position)

    def request_pan(self, north_m, east_m):
        self._request("request_pan", north_m, east_m)

    def request_pan_screen(self, right_px, up_px):
        self._request("request_pan_screen", right_px, up_px)

    def request_zoom(self, zoom_level):
        self._request("request_zoom", zoom_level)

    def request_bearing(self, bearing_rad):
        self._request("request_bearing", bearing_rad)

    def request_pitch(self, pitch_rad):
        self._request("request_pitch", pitch_rad)

    def request_poi_focus(self, category):
        self._native.request_poi_focus(category)
        self._poi_state = PoiOverlayState(
            self._poi_state.markers, self._poi_state.category, category
        )
        self._send_pois(self._poi_state)

    def request_poi_results(self, markers, category):
        self._native.request_poi_results(markers, category)
        self._poi_state = PoiOverlayState(
            tuple(markers), category, self._poi_state.focused_category
        )
        self._send_pois(self._poi_state)

    def refresh_renderer_state(self):
        """Preserve native presentation replay across the platform wrapper."""
        refresh = getattr(self._native, "refresh_renderer_state", None)
        if refresh is not None:
            refresh()

    def request_style(self, style_id):
        self._native.request_style(style_id)
