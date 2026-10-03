# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Read viewport city names from the native map without interfering with POIs."""

from dataclasses import dataclass
import math
from queue import Empty, SimpleQueue
from threading import Thread

from messaging.zeromq.subscriber import ZeroMqSubscriber

CITY_RESULT_TOPIC = "map.weather.cities"
CITY_CLICK_TOPIC = "map.click"


@dataclass(frozen=True)
class RawWeatherCity:
    name: str
    latitude: float
    longitude: float


def decode_city_result(payload):
    """Validate the native reply and deduplicate vector-tile city points."""
    if not isinstance(payload, dict):
        return None
    request_id, raw = payload.get("request_id"), payload.get("cities")
    if not isinstance(request_id, int) or isinstance(request_id, bool) or not isinstance(raw, list):
        return None
    cities = []
    for item in raw[:12]:
        if not isinstance(item, dict):
            continue
        name, latitude, longitude = item.get("name"), item.get("latitude"), item.get("longitude")
        if (not isinstance(name, str) or not name.strip() or len(name) > 160
                or not isinstance(latitude, (int, float)) or isinstance(latitude, bool)
                or not isinstance(longitude, (int, float)) or isinstance(longitude, bool)
                or not math.isfinite(latitude) or not math.isfinite(longitude)
                or not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
            continue
        city = RawWeatherCity(name.strip(), round(latitude, 5), round(longitude, 5))
        if city not in cities:
            cities.append(city)
    return request_id, tuple(cities)


def decode_city_click(payload):
    """Accept only native hits on city-weather features, never ordinary map clicks."""
    if not isinstance(payload, dict):
        return None
    identity = payload.get("marker_id")
    if isinstance(identity, str) and identity.startswith("weather-city:") and len(identity) <= 256:
        return identity
    return None


class MapWeatherCitySource:
    """Queue city-query replies onto the UI thread using a separate subscription."""

    def __init__(self, subscriber=None):
        self._subscriber = subscriber or ZeroMqSubscriber()
        self._subscriber.subscribe(CITY_RESULT_TOPIC)
        self._subscriber.subscribe(CITY_CLICK_TOPIC)
        self._queue = SimpleQueue()
        self._clicks = SimpleQueue()
        Thread(target=self._receive, name="map-weather-cities", daemon=True).start()

    def poll(self):
        """Return a pending request id and city tuple, or None."""
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def poll_selected_city(self):
        """Return a clicked city identity without consuming viewport replies."""
        try:
            return self._clicks.get_nowait()
        except Empty:
            return None

    def close(self):
        """Stop reception and release the subscriber's thread-owned socket."""
        self._subscriber.close()

    def _receive(self):
        while True:
            try:
                topic, payload = self._subscriber.receive()
            except RuntimeError:
                return
            except ValueError:
                continue
            if topic == CITY_RESULT_TOPIC:
                result = decode_city_result(payload)
                if result is not None:
                    self._queue.put(result)
            elif topic == CITY_CLICK_TOPIC:
                identity = decode_city_click(payload)
                if identity is not None:
                    self._clicks.put(identity)
