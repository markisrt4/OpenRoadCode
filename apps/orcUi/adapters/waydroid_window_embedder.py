# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Recover missed nested-Weston output resizes without blocking the UI."""
import subprocess
from threading import Event, RLock, Thread

from frontends.x11.x11_window_embedder import X11WindowEmbedder


class WaydroidWindowEmbedder(X11WindowEmbedder):
    """Verify Android's output, since an X11 resize alone is not an acknowledgement."""

    def __init__(self):
        super().__init__()
        self._resize_lock = RLock()
        self._resize_cancel = Event()

    def resize(self, width, height):
        with self._resize_lock:
            self._resize_cancel.set()
            cancelled = self._resize_cancel = Event()
            super().resize(width, height)
            if self.window_id is None:
                return
            target = (max(1, int(width)), max(1, int(height)))
            crop = self._vertical_crop
            Thread(target=self._settle, args=(cancelled, target, crop), daemon=True).start()

    @staticmethod
    def _android_size():
        try:
            dimensions = []
            for name in ('waydroid.display_width', 'waydroid.display_height'):
                result = subprocess.run(['waydroid', 'prop', 'get', name],
                                        capture_output=True, text=True, timeout=2, check=True)
                dimensions.append(int(result.stdout.strip()))
            return tuple(dimensions)
        except (OSError, subprocess.SubprocessError, ValueError):
            return None

    def _settle(self, cancelled, target, crop):
        expected = (target[0], target[1] + sum(crop))
        # Allow normal output configuration to finish before touching geometry.
        for _ in range(3):
            if cancelled.wait(1):
                return
            actual = self._android_size()
            if actual is None or actual == expected:
                return
            with self._resize_lock:
                if cancelled.is_set() or self.window_id is None:
                    return
                # Repeating the same X11 size produces no ConfigureNotify.
                # Keep the intermediate size for a full compositor round trip.
                super().resize(max(1, target[0] - 2), target[1])
            if cancelled.wait(1):
                return
            with self._resize_lock:
                if cancelled.is_set() or self.window_id is None:
                    return
                super().resize(*target)

    def clear(self):
        with self._resize_lock:
            self._resize_cancel.set()
            super().clear()

    def detach(self, parent_window_id):
        with self._resize_lock:
            self._resize_cancel.set()
            super().detach(parent_window_id)
