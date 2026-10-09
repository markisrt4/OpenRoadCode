# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent state and requests for the map-controls drawer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MapControlsDrawerState:
    expanded: bool = False


class MapControlsDrawerUiIf(ABC):
    @abstractmethod
    def set_map_controls_drawer_state(self, state: MapControlsDrawerState) -> None:
        """Render the complete drawer visibility state."""


class MapControlsDrawerRequestHandlerIf(ABC):
    @abstractmethod
    def request_map_controls_expanded(self, expanded: bool) -> None:
        """Request the expanded or collapsed drawer state."""
