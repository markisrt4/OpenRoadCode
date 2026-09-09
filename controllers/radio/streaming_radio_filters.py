# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation-independent station filtering for Streaming Radio."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .streaming_radio_types import StreamingRadioStation

GENRE_FILTERS = (
    "All", "Rock", "Country", "Pop", "News/Talk", "Sports", "Jazz",
    "Classical", "Christian", "Hip-Hop/R&B", "Electronic", "Variety",
)
QUALITY_FILTERS = ("All", "Low", "Mid", "High")
BAND_FILTERS = ("All", "FM", "AM", "DAB", "Internet-only", "Unknown")

_GENRE_TAGS = {
    "Rock": {"rock", "classic rock", "alternative rock", "indie rock", "hard rock"},
    "Country": {"country", "americana", "bluegrass"},
    "Pop": {"pop", "top 40", "top40", "adult contemporary", "hot ac"},
    "News/Talk": {"news", "talk", "talk radio", "public radio", "politics"},
    "Sports": {"sports", "sport", "sports talk"},
    "Jazz": {"jazz", "smooth jazz"},
    "Classical": {"classical", "opera"},
    "Christian": {"christian", "christian contemporary", "gospel", "religious", "worship"},
    "Hip-Hop/R&B": {"hip hop", "hip-hop", "rap", "r&b", "rnb", "urban"},
    "Electronic": {"electronic", "edm", "dance", "house", "techno", "trance"},
    "Variety": {"variety", "eclectic", "mixed", "community"},
}


def _normalize_tag(tag: str) -> str:
    return " ".join(tag.casefold().replace("_", " ").replace("-", " ").split())


def is_explicit_internet_only(station: StreamingRadioStation) -> bool:
    tags = {_normalize_tag(tag) for tag in station.tags}
    return bool(tags & {"internet", "internet only", "online only", "web radio", "webradio"})


def station_genre_matches(station: StreamingRadioStation, genre: str) -> bool:
    if genre == "All":
        return True
    accepted = _GENRE_TAGS.get(genre)
    if accepted is None:
        return False
    tags = {_normalize_tag(tag) for tag in station.tags}
    return bool(tags & {_normalize_tag(tag) for tag in accepted})


def station_quality(station: StreamingRadioStation) -> str:
    bitrate = station.bitrate_kbps
    if bitrate is None or bitrate <= 0:
        return "Unknown"
    if bitrate < 96:
        return "Low"
    if bitrate < 192:
        return "Mid"
    return "High"


def station_band(station: StreamingRadioStation) -> str:
    if is_explicit_internet_only(station):
        return "Internet-only"
    tags = {_normalize_tag(tag) for tag in station.tags}
    if tags & {"dab", "dab+", "digital audio broadcasting", "dabradio"}:
        return "DAB"
    if tags & {"fm", "fm radio", "fmradio"}:
        return "FM"
    if tags & {"am", "am radio", "amradio", "medium wave", "mw"}:
        return "AM"
    name = station.name.casefold()
    if re.search(r"\bfm\b", name):
        return "FM"
    if re.search(r"\bam\b", name):
        return "AM"
    for match in re.finditer(r"(?<!\d)(\d{2,3}\.\d)(?!\d)", name):
        frequency = float(match.group(1))
        if 87.5 <= frequency <= 108.0:
            return "FM"
    if re.search(r"\b(?:5[3-9]\d|[6-9]\d{2}|1[0-6]\d{2}|1700|1710)\s*(?:khz|am)\b", name):
        return "AM"
    return "Unknown"


@dataclass(frozen=True, slots=True)
class StationFilters:
    """Immutable filter selection, independent of Tk and directory loading."""

    genre: str = "All"
    quality: str = "All"
    band: str = "All"

    def __post_init__(self) -> None:
        for name, value, choices in (
            ("genre", self.genre, GENRE_FILTERS),
            ("quality", self.quality, QUALITY_FILTERS),
            ("band", self.band, BAND_FILTERS),
        ):
            if value not in choices:
                raise ValueError(f"Unknown {name} filter: {value}")

    @property
    def active_count(self) -> int:
        return sum(value != "All" for value in (self.genre, self.quality, self.band))

    @property
    def internet_only(self) -> bool:
        return self.band == "Internet-only"

    def matches(self, station: StreamingRadioStation) -> bool:
        band = station_band(station)
        if self.band != "All" and band != self.band:
            return False
        if not station_genre_matches(station, self.genre):
            return False
        return self.quality == "All" or station_quality(station) == self.quality

    def apply(self, stations: Iterable[StreamingRadioStation]) -> tuple[StreamingRadioStation, ...]:
        """Preserve directory/favorites ordering while applying all selections."""
        return tuple(station for station in stations if self.matches(station))
