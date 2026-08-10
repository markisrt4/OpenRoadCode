"""JSON serialization for persisted weather snapshots."""

from __future__ import annotations

import json
from typing import Any

from controllers.cache import PersistentCacheIf
from controllers.weather.weather_snapshot import WeatherSnapshot


class WeatherSnapshotCache:
    """Persist and validate the latest typed weather snapshot."""

    KEY = "open-meteo:forecast:v1"

    def __init__(self, storage: PersistentCacheIf) -> None:
        self._storage = storage

    def load(self) -> WeatherSnapshot | None:
        """Load the latest snapshot, ignoring absent or invalid data.

        @return Valid cached snapshot or None.
        """
        data = self._storage.get(self.KEY)
        if data is None:
            return None
        try:
            value = json.loads(data.decode("utf-8"))
            return self._decode(value)
        except (KeyError, TypeError, ValueError, UnicodeDecodeError):
            self._storage.remove(self.KEY)
            return None

    def store(self, snapshot: WeatherSnapshot) -> None:
        """Serialize and atomically persist a weather snapshot.

        @param snapshot Valid weather data to store.
        """
        value = {
            "latitude": snapshot.latitude,
            "longitude": snapshot.longitude,
            "location_name": snapshot.location_name,
            "source": snapshot.source,
            "fetched_at": snapshot.fetched_at,
            "forecast": snapshot.forecast,
        }
        self._storage.put(
            self.KEY,
            json.dumps(value, separators=(",", ":")).encode("utf-8"),
        )

    @staticmethod
    def _decode(value: Any) -> WeatherSnapshot:
        if not isinstance(value, dict) or not isinstance(
            value["forecast"], dict
        ):
            raise ValueError("invalid weather snapshot")
        return WeatherSnapshot(
            latitude=float(value["latitude"]),
            longitude=float(value["longitude"]),
            location_name=str(value["location_name"]),
            source=str(value["source"]),
            fetched_at=float(value["fetched_at"]),
            forecast=value["forecast"],
        )
