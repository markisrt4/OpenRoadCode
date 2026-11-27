"""Toolkit-independent requests and results for Trending airplay details."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AirplayRequest:
    artist: str
    title: str | None
    period: str
    station: str | None
    view: Literal["trend", "stations"]


@dataclass(frozen=True, slots=True)
class AirplayDetails:
    counts: tuple[tuple[str, int | None], ...] = ()
    incomplete: bool = False
