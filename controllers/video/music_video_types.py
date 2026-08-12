# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MusicVideoQuery:
    artist: str
    title: str
    album: str | None = None
    isrc: str | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class MusicVideo:
    video_id: str
    title: str
    channel_name: str
    thumbnail_url: str | None = None
    duration_ms: int | None = None
    is_official: bool = False
