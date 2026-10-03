# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""City weather state, asynchronous data and viewport discovery."""

from datetime import datetime
import threading
from time import monotonic, time

from controllers.weather.city_weather import CityWeatherProvider, WeatherCity, city_label, city_value
from protocols.map_renderer.map_weather_city_source import MapWeatherCitySource


class NavigationCityWeather:
    """Keep city map labels independent of radar, heatmaps and route weather."""

    def __init__(self, host, renderer, unit_system, *, provider=None, source=None, clock=time):
        self._host, self._renderer, self._unit_system = host, renderer, unit_system
        self._provider = provider or CityWeatherProvider()
        self._source = source
        self._clock = clock
        self.enabled = False
        self.kind = "temperature"
        self.period = "past"
        self.hours = 1
        self.playing = False
        self.status = "Enable city weather, then pan or zoom to an area"
        self.on_changed = lambda: None
        self._cities = ()
        self._weather = ()
        self._cache = {}
        self._generation = 0
        self._poll_generation = 0
        self._play_generation = 0
        self._visible = False
        self._closed = False
        self._busy = False
        self._request_id = 0
        self._pending_id = None
        self._last_query = 0
        self._loaded_at = 0
        self._retry_at = 0
        self._anchor = 0
        self._query_warning = False

    def set_enabled(self, enabled):
        """Enable independent city labels or clear them without changing the map camera."""
        self.enabled = bool(enabled)
        self._generation += 1
        self._pending_id = None
        self.set_playing(False)
        if not self.enabled:
            self.status = "City weather off"
            self.publish()
        else:
            if self._source is None:
                self._source = MapWeatherCitySource()
            self.status = "Finding cities in this map view…"
            self._last_query = 0
            self._retry_at = 0
            self._cities = ()
            self._weather = ()
            self.publish()
            if self._visible:
                self._query()
        self.on_changed()

    def select(self, *, kind=None, period=None, hours=None):
        """Change the field or time without making another weather request."""
        if kind is not None:
            if kind not in {"temperature", "wind", "precipitation"}:
                raise ValueError("Unknown city weather field")
            self.kind = kind
        if period is not None:
            if period not in {"past", "future"}:
                raise ValueError("Unknown city weather time period")
            self.period = period
        if hours is not None:
            if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 24:
                raise ValueError("City weather hours must be between 1 and 24")
            self.hours = hours
        self.publish()
        self.on_changed()

    def show(self):
        """Poll cities only while Navigation is visible; replay labels after renderer startup."""
        if self._closed:
            return
        self._visible = True
        self._poll_generation += 1
        self._last_query = 0
        self._pending_id = None
        self.publish()
        self._poll(self._poll_generation)

    def hide(self):
        """Pause playback and viewport requests while Navigation is hidden."""
        self._visible = False
        self._poll_generation += 1
        self.set_playing(False)
        self.publish()

    def close(self):
        """Invalidate late weather workers and release the independent map subscription."""
        self._closed = True
        self._generation += 1
        self.hide()
        if self._source is not None:
            self._source.close()
        self._provider.close()

    def refresh(self):
        """Refresh the batch while reusing current city names and coordinates."""
        if self._closed or not self.enabled or not self._cities or self._busy:
            return
        self._busy = True
        self.status = "Loading city weather…"
        self.on_changed()
        generation, cities = self._generation, self._cities

        def load():
            try:
                weather, error = self._provider.hourly(cities), None
            except Exception as failure:
                weather, error = (), str(failure)
            if not self._closed:
                self._host.schedule_ui_callback(0, lambda: self._complete(generation, weather, error))

        threading.Thread(target=load, name="city-weather", daemon=True).start()

    def _complete(self, generation, weather, error):
        self._busy = False
        if self._closed or not self.enabled:
            return
        if generation != self._generation:
            if self._visible and not self._weather:
                self.refresh()
            return
        self._weather = weather if not error else ()
        self._loaded_at = self._clock()
        self._retry_at = self._loaded_at + (60 if error else 900)
        self._anchor = int(self._loaded_at // 3600) * 3600
        if error:
            self.status = f"City weather unavailable: {error}"
            self.set_playing(False)
        else:
            for item in weather:
                self._cache[item.city] = (self._loaded_at, item)
            if len(self._cache) > 96:
                oldest = sorted(self._cache, key=lambda city: self._cache[city][0])
                for city in oldest[:-96]:
                    del self._cache[city]
            self.status = f"{len(weather)} cities · Open-Meteo · Model estimates"
        self.publish()
        self.on_changed()

    def _query(self):
        self._request_id += 1
        self._pending_id = self._request_id
        self._last_query = monotonic()
        self._renderer.search_weather_cities(self._pending_id)

    def _poll(self, generation):
        if self._closed or not self._visible or generation != self._poll_generation:
            return
        if self.enabled:
            self._drain_cities()
            if self._pending_id is not None and monotonic() - self._last_query >= 10:
                self._pending_id = None
                self._query_warning = True
                self.status = "City query timed out · rebuild the navigation renderer and retry"
                self.on_changed()
            if self._pending_id is None and monotonic() - self._last_query >= 4:
                self._query()
            if self._cities and self._clock() >= self._retry_at and not self._busy:
                self.refresh()
        self._host.schedule_ui_callback(500, lambda: self._poll(generation))

    def _drain_cities(self):
        if self._source is None:
            return
        while (reply := self._source.poll()) is not None:
            request_id, cities = reply
            if request_id != self._pending_id:
                continue
            self._pending_id = None
            recovered = self._query_warning
            self._query_warning = False
            # Stable ordering avoids another API request when vector-tile order changes.
            cities = tuple(sorted((WeatherCity(city.name, city.latitude, city.longitude) for city in cities),
                                  key=lambda city: (city.name, city.latitude, city.longitude)))
            if cities == self._cities:
                if recovered or not cities:
                    self.status = (f"{len(self._weather)} cities · Open-Meteo · Model estimates" if self._weather
                                   else "No city names here · zoom out or pan to a town")
                    self.on_changed()
                continue
            self._cities = cities
            self._generation += 1
            self._weather = ()
            self._retry_at = 0
            self.publish()
            if cities:
                cached = [self._cache.get(city) for city in cities]
                if all(item is not None and self._clock() - item[0] < 900 for item in cached):
                    self._weather = tuple(item[1] for item in cached)
                    self._loaded_at = min(item[0] for item in cached)
                    self._retry_at = self._loaded_at + 900
                    self._anchor = int(self._clock() // 3600) * 3600
                    self.status = f"{len(cities)} cities · Open-Meteo · Model estimates"
                    self.publish()
                    self.on_changed()
                else:
                    self.refresh()
            else:
                self.set_playing(False)
                self.status = "No city names here · zoom out or pan to a town"
                self.on_changed()

    def set_playing(self, playing):
        """Animate local cached hourly data, leaving radar playback untouched."""
        self.playing = bool(playing and self.enabled and self._weather and self._visible)
        self._play_generation += 1
        self.on_changed()
        if self.playing:
            generation = self._play_generation
            self._host.schedule_ui_callback(1500, lambda: self._advance(generation))

    def _advance(self, generation):
        if self._closed or not self.playing or generation != self._play_generation:
            return
        # History plays oldest-to-newest. Rain totals grow from 1 to 24 hours.
        if self.period == "past" and self.kind != "precipitation":
            hours = self.hours - 1 if self.hours > 1 else 24
        else:
            hours = self.hours + 1 if self.hours < 24 else 1
        self.select(hours=hours)
        self._host.schedule_ui_callback(1500, lambda: self._advance(generation))

    def time_label(self):
        """Describe exact snapshot time or rainfall window in local time."""
        anchor = self._anchor or int(self._clock() // 3600) * 3600
        target = anchor + self.hours * 3600 * (-1 if self.period == "past" else 1)

        def stamp(timestamp):
            return datetime.fromtimestamp(timestamp).astimezone().strftime("%a %I:%M %p %Z").replace(" 0", " ")

        if self.kind == "precipitation":
            start, end = (target, anchor) if self.period == "past" else (anchor, target)
            return f"{self.hours}h total · {stamp(start)} → {stamp(end)}"
        return f"{self.hours}h {'ago' if self.period == 'past' else 'ahead'} · {stamp(target)}"

    def publish(self):
        """Draw big weather numbers and smaller names using a separate GeoJSON source."""
        if self._closed:
            return
        features = []
        imperial = self._unit_system().value == "imperial"
        if self.enabled and self._visible:
            for weather in self._weather:
                value = city_value(weather, self.kind, self.hours, self.period, self._anchor)
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [
                    weather.city.longitude, weather.city.latitude]}, "properties": {
                        "name": weather.city.name, "value": city_label(value, self.kind, imperial),
                        "color": "#f8e58b" if self.kind == "temperature" else
                                 "#a6edff" if self.kind == "wind" else "#a2f2c4"}})
        self._renderer.set_city_weather({"type": "FeatureCollection", "features": features})
