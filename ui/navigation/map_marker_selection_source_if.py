"""Toolkit-independent source of map-marker selection events."""

from abc import ABC, abstractmethod


class MapMarkerSelectionSourceIf(ABC):
    """Expose renderer selections without leaking toolkit event objects."""

    @abstractmethod
    def poll_selected_marker_id(self) -> str | None:
        """Consume the next marker selection.

        @return The selected marker identifier, or None if no selection is pending.
        """
        ...
