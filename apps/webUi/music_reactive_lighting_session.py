# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web-facing control surface for music-reactive lighting."""
from __future__ import annotations

from controllers.lighting import MusicReactiveLighting


class WebMusicReactiveLightingSession:
    """Expose music-reactive lighting state without leaking backend details."""

    def __init__(self, reactive_lighting: MusicReactiveLighting | None = None) -> None:
        self._reactive_lighting = reactive_lighting

    def state(self) -> dict[str, bool]:
        """Return availability, enable state, and hardware connection state."""
        reactive = self._reactive_lighting
        if reactive is None:
            return {
                "available": False,
                "enabled": False,
                "connected": False,
            }
        return {
            "available": True,
            "enabled": reactive.is_enabled,
            "connected": reactive.is_connected,
        }

    def set_enabled(self, enabled: bool) -> dict[str, bool]:
        """Enable or disable music-reactive lighting and return current state."""
        reactive = self._reactive_lighting
        if reactive is None:
            raise RuntimeError("Music-reactive lighting is unavailable")
        reactive.set_enabled(enabled)
        return self.state()
