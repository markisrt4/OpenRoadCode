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
        return not self.lines

