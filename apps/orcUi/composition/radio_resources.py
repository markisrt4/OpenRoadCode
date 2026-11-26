# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resources owned by the radio composition."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from common.resource_cleanup import close_resources

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable

    from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
    from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
    from controllers.radio.rf_radio_session import ReceiverSession
    from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
    from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
    from frontends.tk.radio import RadioScreen
    from protocols.rigctl.rigctl_client import RigctlClient
    from ui.media.song_launch import SongLaunchRequest
    from ui.radio.receiver_settings_if import ReceiverSettingsIf


@dataclass(slots=True)
class StreamingRadioResources:
    """Retain worker and browser ownership independently of widget lifetime."""

    cancel_callback: Callable[[object], None]
    executor: ThreadPoolExecutor = field(
        default_factory=lambda: ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="orcui-streaming-radio",
        )
    )
    artwork_executor: ThreadPoolExecutor = field(
        default_factory=lambda: ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="orcui-radio-artwork",
        )
    )
    rf_executor: ThreadPoolExecutor = field(
        default_factory=lambda: ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="orcui-rf-radio",
        )
    )
    rf_sessions: set[ReceiverSession] = field(default_factory=set)
    sessions: set[StreamingRadioBrowser] = field(default_factory=set)
    unsubscribe: Callable[[], None] = lambda: None
    adsb_callback: object | None = None
    closed: bool = False
    stop_receiver: Callable[[], None] = lambda: None

    def run_work(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.executor.submit(work)

    def run_rf(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.rf_executor.submit(work)

    def run_artwork(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.artwork_executor.submit(work)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True

        def cancel_adsb() -> None:
            if self.adsb_callback is not None:
                self.cancel_callback(self.adsb_callback)
                self.adsb_callback = None

        close_resources(
            self.unsubscribe,
            cancel_adsb,
            *(session.close for session in tuple(self.sessions)),
            *(session.close for session in tuple(self.rf_sessions)),
            lambda: self.rf_executor.shutdown(wait=True, cancel_futures=True),
            self.stop_receiver,
            lambda: self.executor.shutdown(wait=False, cancel_futures=True),
            lambda: self.artwork_executor.shutdown(wait=False, cancel_futures=True),
        )


@dataclass(slots=True)
class RadioComposition:
    """Own radio presentation resources created by the composition root."""

    screen: RadioScreen
    directory: RadioBrowserDirectory
    favorites: StreamingRadioFavorites
    home_factory: Callable[[tk.Misc], tk.Widget]
    open_weather_radio: Callable[[], None]
    streaming_resources: StreamingRadioResources
    bind_song_launch: Callable[[Callable[[SongLaunchRequest], None]], None] = lambda _handler: None
    close_charts: Callable[[], None] = lambda: None
    bind_video_player: Callable[[ManagedBrowserMediaPlayer], None] = lambda _player: None
    bind_spotify_factory: Callable[
        [Callable[[tk.Misc, str, str], tk.Widget]], None
    ] = lambda _factory: None
    rigctl_client: RigctlClient | None = None
    receiver_settings: ReceiverSettingsIf | None = None

    def close(self) -> None:
        """Retire browser sessions and workers; runtime retains playback ownership."""
        self.streaming_resources.close()
        self.close_charts()
