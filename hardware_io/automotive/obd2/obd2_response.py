from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Obd2Response:
    """
    Response returned by an OBD-II adapter.
    """

    command: str
    raw: str
    lines: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not self.lines
