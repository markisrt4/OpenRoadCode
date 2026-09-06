# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bridge ORC navigation fixes into Google Earth's geolocation watcher."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient


class EarthGeolocationWatchProbe:
    """Capture Earth's watchPosition callback and feed it ORC position fixes."""

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    def install(self) -> bool:
        """Wrap watchPosition and retain Earth's success callback."""
        try:
            value = self._client.evaluate_earth(
                r"""(() => {
                    const geo = navigator.geolocation;
                    if (!geo) return false;
                    if (window.__orcEarthGeoWatchProbe?.installed) return true;
                    const originalWatch = geo.watchPosition.bind(geo);
                    const originalClear = geo.clearWatch.bind(geo);
                    const state = {
                        installed: true,
                        registrations: 0,
                        lastRegistrationMs: null,
                        callbacks: new Map()
                    };
                    Object.defineProperty(geo, 'watchPosition', {
                        configurable: true,
                        value: function(success, error, options) {
                            state.registrations += 1;
                            state.lastRegistrationMs = Date.now();
                            let browserId = null;
                            const ignoredNativeError = function(nativeError) {
                                // Chromium/Termux may have no native location provider. ORC is
                                // the provider for this Earth session, so do not fail Earth's
                                // watcher merely because Chromium's network service cannot fix.
                                if (!window.__orcEarthGeoWatchProbe?.callbacks.has(browserId) && error) {
                                    error(nativeError);
                                }
                            };
                            browserId = originalWatch(success, ignoredNativeError, options);
                            state.callbacks.set(browserId, success);
                            return browserId;
                        }
                    });
                    Object.defineProperty(geo, 'clearWatch', {
                        configurable: true,
                        value: function(browserId) {
                            state.callbacks.delete(browserId);
                            return originalClear(browserId);
                        }
                    });
                    window.__orcEarthGeoWatchProbe = state;
                    return true;
                })()"""
            )
        except (OSError, RuntimeError, ValueError):
            return False
        return value is True

    def registration_count(self) -> int | None:
        """Return how many watchPosition registrations Earth has made."""
        try:
            value = self._client.evaluate_earth(
                "(() => window.__orcEarthGeoWatchProbe?.registrations ?? null)()"
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
        """Deliver one synthetic GeolocationPosition to every active Earth watcher."""
        payload = {
            "latitude": float(latitude_deg),
            "longitude": float(longitude_deg),
            "accuracy": max(0.0, float(accuracy_m)),
            "altitude": None if altitude_m is None else float(altitude_m),
            "altitudeAccuracy": None,
            "heading": None if heading_deg is None else float(heading_deg) % 360.0,
            "speed": None if speed_m_s is None else max(0.0, float(speed_m_s)),
        }
        try:
            value = self._client.evaluate_earth(
                f"""(() => {{
                    const state = window.__orcEarthGeoWatchProbe;
                    if (!state?.installed || !state.callbacks?.size) return false;
                    const coords = Object.freeze({payload!r}
                        .replace ? null : null);
                    return true;
                }})()"""
            )
        except (OSError, RuntimeError, ValueError):
            value = None
        # Build the JavaScript with JSON rather than Python repr. Kept separate so
        # browser objects exactly match the GeolocationPosition shape Earth expects.
        import json
        expression = f"""(() => {{
            const state = window.__orcEarthGeoWatchProbe;
            if (!state?.installed || !state.callbacks?.size) return false;
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
            let delivered = 0;
            for (const callback of state.callbacks.values()) {{
                try {{ callback(position); delivered += 1; }} catch (_) {{}}
            }}
            return delivered > 0;
        }})()"""
        try:
            return self._client.evaluate_earth(expression) is True
        except (OSError, RuntimeError, ValueError):
            return False
