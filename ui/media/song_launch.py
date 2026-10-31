"""Toolkit-independent requests for opening a discovered song."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class SongDestination(str, Enum):
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"


@dataclass(frozen=True, slots=True)
class SongLaunchRequest:
    title: str
    artist: str
    destination: SongDestination

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.artist.strip():
            raise ValueError("Song title and artist are required")

    @property
    def search_text(self) -> str:
        return f"{self.artist.strip()} {self.title.strip()}"


class SongLaunchHandlerIf(Protocol):
    def launch_song(self, request: SongLaunchRequest) -> None: ...
