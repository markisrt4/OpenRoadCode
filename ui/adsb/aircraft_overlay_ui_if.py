# SPDX-License-Identifier: MIT
"""Aircraft presentation boundary, independent of map renderer and SDR transport."""

from abc import ABC, abstractmethod
from ui.adsb.aircraft_overlay_state import AircraftOverlayState


class AircraftOverlayUiIf(ABC):
    @abstractmethod
    def set_aircraft_overlay_state(self, state: AircraftOverlayState) -> None:
        """Present a complete immutable aircraft snapshot."""
        ...
