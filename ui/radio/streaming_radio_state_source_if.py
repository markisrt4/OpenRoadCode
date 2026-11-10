# SPDX-License-Identifier: MIT

"""Read-only streaming playback contract for summary presentation."""

from typing import Protocol

from .streaming_radio_state import StreamingRadioPlaybackState


class StreamingRadioStateSourceIf(Protocol):
    """Supply a consistent immutable playback snapshot without backend access."""

    def snapshot(self) -> StreamingRadioPlaybackState:
        """! @brief Read the current playback state.

        @return Immutable station and playing status snapshot.
        """
        ...
