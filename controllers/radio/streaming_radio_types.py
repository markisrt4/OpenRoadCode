# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StreamingRadioStation:
    """Normalized internet-radio station metadata used by OpenRoadCode."""

    station_id: str
    name: str
    stream_url: str
    homepage_url: str | None = None
    artwork_url: str | None = None
    state: str | None = None
    country_code: str | None = None
    codec: str | None = None
    bitrate_kbps: int | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        station_id = self.station_id.strip()
        name = self.name.strip()
        stream_url = self.stream_url.strip()
        if not station_id:
            raise ValueError("station_id must not be empty")
        if not name:
            raise ValueError("station name must not be empty")
        if not stream_url:
            raise ValueError("stream_url must not be empty")

        object.__setattr__(self, "station_id", station_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "stream_url", stream_url)
        object.__setattr__(self, "country_code", _clean_upper(self.country_code))
        object.__setattr__(self, "state", _clean(self.state))
        object.__setattr__(self, "homepage_url", _clean(self.homepage_url))
        object.__setattr__(self, "artwork_url", _clean(self.artwork_url))
        object.__setattr__(self, "codec", _clean_upper(self.codec))
        object.__setattr__(self, "tags", tuple(tag.strip() for tag in self.tags if tag.strip()))

        if self.bitrate_kbps is not None and self.bitrate_kbps < 0:
            raise ValueError("bitrate_kbps must not be negative")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clean_upper(value: str | None) -> str | None:
    value = _clean(value)
    return value.upper() if value else None
