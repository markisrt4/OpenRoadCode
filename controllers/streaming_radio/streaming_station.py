# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-independent streaming radio station model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamingStation:
    """One playable internet radio station discovered by a provider."""

    station_id: str
    name: str
    stream_url: str
    homepage_url: str | None = None
    image_url: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    tags: tuple[str, ...] = ()
    codec: str | None = None
    bitrate_kbps: int | None = None
