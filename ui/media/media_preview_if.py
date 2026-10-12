# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Toolkit-independent access to a cached now-playing preview."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from ui.media.media_ui_if import MediaState


class MediaPreviewIf(ABC):
    @abstractmethod
    def read_state(self) -> MediaState:
        """! @brief Return cached state without network access or refresh work."""

    @abstractmethod
    def request_artwork(self, url: str, result: Callable[[bytes | None], None]) -> None:
        """! @brief Load PNG artwork outside the UI thread.
        @param url Artwork URL from the cached media snapshot.
        @param result Worker-thread callback receiving PNG bytes or None.
        """
