"""Route semantic map requests while retaining native map camera state."""

from ui.navigation import MapRequestHandlerIf


class MapPlatformRequests(MapRequestHandlerIf):
    def __init__(self, native: MapRequestHandlerIf, send_earth) -> None:
        self._native = native
        self._send_earth = send_earth

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

    def request_poi_results(self, markers, category):
        self._native.request_poi_results(markers, category)

    def request_style(self, style_id):
        self._native.request_style(style_id)
