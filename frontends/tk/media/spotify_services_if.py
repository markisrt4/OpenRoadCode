# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Narrow browser player contract used by Tk media screens."""

from typing import Protocol


class BrowserMediaPlayerIf(Protocol):
    """Launch and stop browser-hosted media for a Tk panel."""

    def play(
        self,
        target: str,
        *,
        display: str,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
    ) -> bool:
        """! @brief Open a media target on the requested display.

        @param target Media URL or target understood by the browser-backed player.
        @param display X11 display on which the browser should be launched.
        @param window_position Optional x/y position for the browser window.
        @param window_size Optional width/height for the browser window.
        @return True when the media target was opened successfully, otherwise False.
        """
        ...

    def stop(self) -> None:
        """Stop the browser instance owned by this player."""
        ...
