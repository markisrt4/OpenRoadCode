# SPDX-License-Identifier: MIT

"""Optional route capability; advertise only when implemented."""

from abc import ABC, abstractmethod


class RouteAlternativeRequestHandlerIf(ABC):
    """Select an available alternative route."""

    @abstractmethod
    def request_select_alternative(self, alternative_index: int) -> None:
        """Request selection of an alternative route.

        @param alternative_index Zero-based alternative-route index.
        """
        ...
