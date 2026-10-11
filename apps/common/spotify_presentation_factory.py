# SPDX-License-Identifier: MIT

"""Composition support shared by ORC and legacy Car UI callers."""

import io
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable

from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.spotify.spotify_presentation import SpotifyPresentation
from controllers.spotify.spotify_state_service import SpotifyStateService
from controllers.video import MusicVideoController
from ui.ui_dispatcher_if import UiDispatcherIf


def cached_artwork_loader(cache: ImageCache, *, max_size: int = 1024) -> Callable[[str], bytes]:
    """Keep the existing persistent cache behind an encoded presentation boundary."""
    def load(uri: str) -> bytes:
        image = cache.get(uri, width=max_size, height=max_size)
        try:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
        finally:
            image.close()
    return load


def create_spotify_presentation(
    service: SpotifyStateService, cache: ImageCache, lyrics: LrclibLyricsClient,
    video: MusicVideoController, dispatcher: UiDispatcherIf,
    workers: ThreadPoolExecutor, *, online: Callable[[], bool] = lambda: True,
    rich: bool = True, process_id: Callable[[], int | None] = lambda: None,
) -> SpotifyPresentation:
    def run_work(callback: Callable[[], None]) -> None:
        workers.submit(callback)

    return SpotifyPresentation(
        read_state=service.latest_state, online=online, playback=service, tracks=service, seek=service,
        load_artwork=cached_artwork_loader(cache, max_size=1024 if rich else 64),
        load_lyrics=lambda state: lyrics.get_lyrics(
            track_name=state.title or "", artist_name=state.artist or "",
            album_name=state.album or "", duration_ms=int((state.duration_s or 0) * 1000),
        ),
        video_available=video.current_track_has_video, video_active=video.is_video_active,
        watch_video=lambda current, restore: video.watch_current_track(is_current=current, restore_allowed=restore),
        return_to_spotify=lambda current: video.return_to_spotify(is_current=current),
        read_video_process_id=process_id, set_volume=service.request_volume,
        run_work=run_work, dispatcher=dispatcher, rich=rich,
    )
