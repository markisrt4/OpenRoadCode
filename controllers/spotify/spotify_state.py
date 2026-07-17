from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpotifyState:
    is_available: bool = False
    configuration_required: bool = False
    is_playing: bool = False

    track_name: str | None = None
    artist_name: str | None = None
    album_name: str | None = None

    album_art_url: str | None = None
    
    track_uri: str | None = None
    album_art_url: str | None = None
    spotify_url: str | None = None
    release_date: str | None = None

    device_name: str | None = None
    volume_percent: int | None = None

    progress_ms: int | None = None
    duration_ms: int | None = None

    status_message: str = "Spotify unavailable"

    @property
    def progress_percent(self) -> float | None:
        if self.progress_ms is None or self.duration_ms is None:
            return None

        if self.duration_ms <= 0:
            return None

        return max(0.0, min(100.0, self.progress_ms * 100.0 / self.duration_ms))
