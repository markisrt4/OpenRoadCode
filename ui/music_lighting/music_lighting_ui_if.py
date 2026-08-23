# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from controllers.music_lighting.music_lighting_types import MusicLightingState


class MusicLightingUiIf(ABC):
    """State pushed into any frontend surface exposing music lighting."""

    @abstractmethod
    def set_music_lighting_state(self, state: MusicLightingState) -> None:
        """Display current music-lighting configuration.

        @param state Complete music-lighting state.
        """
        ...
