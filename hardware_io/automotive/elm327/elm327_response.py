from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Elm327Response:
    """Raw response returned by an ELM327-compatible device."""

    command: str
    raw: str
    lines: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        """Return whether the response contains no data lines.

        @retval True No normalized response lines were received.
        @retval False At least one response line is present.
        """
        return not self.lines
