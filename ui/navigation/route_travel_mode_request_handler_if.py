# SPDX-License-Identifier: MIT

"""Optional route capability; advertise only when implemented."""

from abc import ABC, abstractmethod
from ui.navigation.route_types import TravelMode


class RouteTravelModeRequestHandlerIf(ABC):
    """Change the costing mode of an existing route."""

    @abstractmethod
    def request_travel_mode(self, travel_mode: TravelMode) -> None:
        """Request a new route costing mode.

        @param travel_mode Requested travel mode.
        """
        ...
