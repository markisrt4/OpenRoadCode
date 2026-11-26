"""Toolkit-independent requests for an embedded Trending video session."""

from typing import Protocol


class TrendingVideoSession(Protocol):
    """Own search, browser playback, and cleanup for one video pane."""

    def poll_target(self) -> str | None:
        """Return the resolved target, or None while search is pending."""
        ...

    def play(self, target: str, position: tuple[int, int], size: tuple[int, int]) -> bool:
        """Open a resolved target at the supplied display geometry."""
        ...

    def theater(self, window_id: int) -> None:
        """Request theater mode for the embedded browser window."""
        ...

    def close(self) -> None:
        """Retire pending work and stop playback."""
        ...
