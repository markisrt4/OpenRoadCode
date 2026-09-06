# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Detect when Google Earth registers its browser geolocation watch."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient


class EarthGeolocationWatchProbe:
    """Transparently count Google Earth's navigator.geolocation watches."""

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    def install(self) -> bool:
        """Wrap watchPosition without changing its callbacks or return value."""
        try:
            value = self._client.evaluate_earth(
                r"""(() => {
                    const geo = navigator.geolocation;
                    if (!geo) return false;
                    if (window.__orcEarthGeoWatchProbe?.installed) return true;
                    const originalWatch = geo.watchPosition.bind(geo);
                    const state = {installed: true, registrations: 0, lastRegistrationMs: null};
                    Object.defineProperty(geo, 'watchPosition', {
                        configurable: true,
                        value: function(success, error, options) {
                            state.registrations += 1;
                            state.lastRegistrationMs = Date.now();
                            return originalWatch(success, error, options);
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
