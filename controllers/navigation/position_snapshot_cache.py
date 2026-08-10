"""Persistent serialization for the last valid geographic fix."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from controllers.cache import PersistentCacheIf
from controllers.navigation.navigation_state import PositionState


DEFAULT_POSITION_CACHE_DIRECTORY = (
    Path.home() / ".cache" / "openroadcode" / "position"
)


class PositionSnapshotCache:
    """Persist and restore the most recent valid position fix."""

    KEY = "position:last-good-fix:v1"

    def __init__(self, storage: PersistentCacheIf) -> None:
        self._storage = storage

    def load(self) -> PositionState | None:
        """Load the cached fix and mark it as cached.

        @return Cached position or None when absent or invalid.
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

    def store(self, state: PositionState) -> None:
        """Persist a valid live position fix.

        @param state Live position containing a usable fix and coordinates.
        @exception ValueError if state is cached or lacks a usable fix.
        """
        if (
            state.is_cached
            or not state.has_fix
            or state.latitude_deg is None
            or state.longitude_deg is None
        ):
            raise ValueError("only valid live position fixes can be cached")
        value = {
            "received_at": state.received_at.isoformat(),
            "latitude_deg": state.latitude_deg,
            "longitude_deg": state.longitude_deg,
            "altitude_m": state.altitude_m,
            "fix_mode": state.fix_mode,
            "accuracy_m": state.accuracy_m,
            "source": state.source,
        }
        self._storage.put(
            self.KEY,
            json.dumps(value, separators=(",", ":")).encode("utf-8"),
        )

    @staticmethod
    def _decode(value: Any) -> PositionState:
        if not isinstance(value, dict):
            raise ValueError("invalid position snapshot")
        latitude = float(value["latitude_deg"])
        longitude = float(value["longitude_deg"])
        fix_mode = int(value["fix_mode"])
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("cached coordinates are out of range")
        if fix_mode < 2:
            raise ValueError("cached position has no usable fix")
        return PositionState(
            received_at=datetime.fromisoformat(value["received_at"]),
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=_optional_float(value.get("altitude_m")),
            fix_mode=fix_mode,
            accuracy_m=_optional_float(value.get("accuracy_m")),
            source=str(value.get("source") or "unknown"),
            is_cached=True,
        )


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
