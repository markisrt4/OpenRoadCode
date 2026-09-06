# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Feed ORC navigation fixes directly to Google Earth's geolocation API."""

from __future__ import annotations

import json

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient


class EarthGeolocationBridge:
    """Provide Google Earth with a synthetic geolocation API backed by ORC."""

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    def install(self) -> bool:
        """Replace browser geolocation reads with an ORC-owned provider."""
        try:
            value = self._client.evaluate_earth(
                r"""(() => {
                    const geo = navigator.geolocation;
                    if (!geo) return false;
                    if (window.__orcEarthGeoBridge?.installed) return true;

                    const state = {
                        installed: true,
                        registrations: 0,
                        nextWatchId: 1,
                        callbacks: new Map(),
                        pendingCurrent: [],
                        latestFix: null
                    };

                    const deliverAsync = (callback, position) => {
                        if (typeof callback !== 'function' || !position) return;
                        queueMicrotask(() => {
                            try { callback(position); } catch (_) {}
                        });
                    };

                    Object.defineProperty(geo, 'watchPosition', {
                        configurable: true,
                        value: function(success, error, options) {
                            void error;
                            void options;
                            const id = state.nextWatchId++;
                            state.registrations += 1;
                            state.callbacks.set(id, success);
                            if (state.latestFix) deliverAsync(success, state.latestFix);
                            return id;
                        }
                    });

                    Object.defineProperty(geo, 'clearWatch', {
                        configurable: true,
                        value: function(id) {
                            state.callbacks.delete(id);
                        }
                    });

                    Object.defineProperty(geo, 'getCurrentPosition', {
                        configurable: true,
                        value: function(success, error, options) {
                            void error;
                            void options;
                            if (state.latestFix) deliverAsync(success, state.latestFix);
                            else state.pendingCurrent.push(success);
                        }
                    });

                    state.deliver = function(position) {
                        state.latestFix = position;
                        for (const callback of state.callbacks.values()) {
                            deliverAsync(callback, position);
                        }
                        const pending = state.pendingCurrent.splice(0);
                        for (const callback of pending) deliverAsync(callback, position);
                        return state.callbacks.size > 0 || pending.length > 0;
                    };

                    window.__orcEarthGeoBridge = state;
                    return true;
                })()"""
            )
        except (OSError, RuntimeError, ValueError):
            return False
        return value is True

    def registration_count(self) -> int | None:
        """Return the number of Earth watchPosition registrations observed."""
        try:
            value = self._client.evaluate_earth(
                "(() => window.__orcEarthGeoBridge?.registrations ?? null)()"
            )
        except (OSError, RuntimeError, ValueError):
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return int(value)

    def push_position(
        self,
        latitude_deg: float,
        longitude_deg: float,
        *,
        accuracy_m: float = 5.0,
        heading_deg: float | None = None,
        speed_m_s: float | None = None,
        altitude_m: float | None = None,
    ) -> bool:
        """Deliver one GeolocationPosition-shaped ORC fix to Google Earth."""
        payload = {
            "latitude": float(latitude_deg),
            "longitude": float(longitude_deg),
            "accuracy": max(0.0, float(accuracy_m)),
            "altitude": None if altitude_m is None else float(altitude_m),
            "altitudeAccuracy": None,
            "heading": None if heading_deg is None else float(heading_deg) % 360.0,
            "speed": None if speed_m_s is None else max(0.0, float(speed_m_s)),
        }
        expression = f"""(() => {{
            const state = window.__orcEarthGeoBridge;
            if (!state?.installed || typeof state.deliver !== 'function') return false;
            const raw = {json.dumps(payload)};
            const coords = Object.freeze({{
                latitude: raw.latitude,
                longitude: raw.longitude,
                accuracy: raw.accuracy,
                altitude: raw.altitude,
                altitudeAccuracy: raw.altitudeAccuracy,
                heading: raw.heading,
                speed: raw.speed,
                toJSON() {{ return raw; }}
            }});
            const position = Object.freeze({{
                coords,
                timestamp: Date.now(),
                toJSON() {{ return {{coords: coords.toJSON(), timestamp: this.timestamp}}; }}
            }});
            return state.deliver(position);
        }})()"""
        try:
            return self._client.evaluate_earth(expression) is True
        except (OSError, RuntimeError, ValueError):
            return False
