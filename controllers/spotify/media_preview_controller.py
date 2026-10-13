# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Share existing media state and artwork loading with a lightweight preview."""

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from threading import Lock
from ui.media.media_preview_if import MediaPreviewIf
from ui.media.media_ui_if import MediaState


class MediaPreviewController(MediaPreviewIf):
    def __init__(self, state: Callable[[], MediaState], artwork: Callable[[str], bytes],
                 *, online_allowed: Callable[[], bool] = lambda: True):
        self._state, self._artwork = state, artwork
        self._online_allowed = online_allowed
        self._lock = Lock()
        self._closed = False
        self._generation = 0
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="media-preview")

    def read_state(self) -> MediaState:
        return self._state()

    def request_artwork(self, url, result):
        with self._lock:
            if self._closed:
                return
            self._generation += 1
            self._executor.submit(self._load, url, result, self._generation)

    def _load(self, url, result, generation):
        with self._lock:
            if self._closed or generation != self._generation:
                return
        data = None
        try:
            if self._online_allowed():
                data = self._artwork(url)
        except Exception:
            # Artwork is decorative; metadata and provider actions stay usable.
            pass
        with self._lock:
            current = not self._closed and generation == self._generation
        if current:
            result(data)

    def close(self):
        """Release preview workers and discard completions after shutdown."""
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=True)
