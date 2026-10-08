# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source-neutral analysis controls consumed by the existing HTTP frontend."""
from typing import Protocol


class MusicAnalysisSessionIf(Protocol):
    """Describe the existing session API without exposing a concrete controller."""

    def sources(self) -> tuple[str, ...]:
        """List available source identities.

        @return Source identifiers in presentation order.
        """
        ...

    def state(self) -> dict[str, object]:
        """Read the current session snapshot.

        @return Source, analysis and calibration state.
        """
        ...

    def select(self, source: str) -> dict[str, object]:
        """Select a source without starting capture.

        @param source Registered source identity.
        @return Updated session snapshot.
        """
        ...

    def start(self, source: str | None = None) -> dict[str, object]:
        """Start the selected source.

        @param source Optional source identity to select first.
        @return Updated session snapshot.
        """
        ...

    def stop(self, *, source: str | None = None) -> dict[str, object]:
        """Stop capture for the session or the named source.

        @param source Optional source identity.
        @return Updated session snapshot.
        """
        ...

    def push_pcm16(self, audio: bytes, sample_rate_hz: int, *, source: str = "browser") -> dict[str, object]:
        """Accept a PCM16 frame from an existing transport.

        @param audio Little-endian signed PCM16 audio bytes.
        @param sample_rate_hz Sample rate in Hz.
        @param source Source identity associated with the frame.
        @return Updated session snapshot.
        """
        ...

    def start_zeroize(self) -> dict[str, object]:
        """Begin ambient calibration.

        @return Updated calibration snapshot.
        """
        ...

    def finish_zeroize(self) -> dict[str, object]:
        """Finish ambient calibration.

        @return Updated calibration snapshot.
        """
        ...

    def clear_zeroize(self) -> dict[str, object]:
        """Clear the calibration profile.

        @return Updated calibration snapshot.
        """
        ...
