# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Resources owned by the media composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from common.resource_cleanup import close_resources

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable

    from apps.orcUi.adapters.music_visualizer_browser import MusicVisualizerBrowser
    from controllers.audio.music_analysis.music_visualizer_controller import (
        MusicVisualizerController,
    )
    from controllers.spotify.media_preview_controller import MediaPreviewController
    from controllers.video import MusicVideoController
    from frontends.tk.media.browser_media_screen import BrowserMediaScreen
    from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen


@dataclass(slots=True)
class MediaComposition:
    music_video_controller: MusicVideoController
    home_factory: Callable[[tk.Misc], tk.Widget]
    home_visualizer_factory: Callable[[tk.Misc], tk.Widget] | None
    visualizer: MusicVisualizerScreen | BrowserMediaScreen
    visualizer_runtime: MusicVisualizerController | MusicVisualizerBrowser
    unsubscribe_online: Callable[[], None] = lambda: None
    preview: MediaPreviewController | None = None
    close_spotify_presentations: Callable[[], None] = lambda: None
    close_spotify_accounts: Callable[[], None] = lambda: None

    configure_spotify: Callable[[], None] | None = None
    close_spotify_configuration: Callable[[], None] = lambda: None

    _closed: bool = field(default=False, init=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close_resources(
            self.unsubscribe_online,
            self.preview.close if self.preview is not None else lambda: None,
            self.close_spotify_accounts,
            self.close_spotify_presentations,
            self.visualizer.hide,
            self.visualizer_runtime.close,
            self.music_video_controller.stop_video,
        )
