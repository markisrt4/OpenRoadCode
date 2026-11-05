# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Deliver gestures to the owned scrcpy X11 window, never a default display."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from ui.navigation.waze_gesture_if import WazeGesture


class ScrcpyWazeGestures:
    def __init__(self, player, embedder):
        self._player, self._embedder = player, embedder

    @property
    def available(self):
        return self._embedder.window_id is not None and self._player.gesture_surface() is not None

    def perform(self, gesture, cancelled):
        gesture = WazeGesture(gesture)
        surface, window = self._player.gesture_surface(), self._embedder.window_id
        if surface is None or window is None or cancelled():
            return
        session, title, frame_size, display = surface
        payload = json.dumps(dict(window=window, title=title, frame_size=frame_size, gesture=gesture.value))
        process = subprocess.Popen([sys.executable, '-m', 'frontends.x11.scrcpy_gesture_sender'],
            cwd=Path(__file__).resolve().parents[3], env=dict(os.environ, DISPLAY=display),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline, pending = time.monotonic() + 5, payload
            while True:
                current = self._player.gesture_surface()
                if cancelled() or current is None or current[0] is not session or self._embedder.window_id != window:
                    return
                if time.monotonic() >= deadline:
                    raise RuntimeError('The Waze gesture sender did not respond')
                try:
                    _, error = process.communicate(input=pending, timeout=.05)
                    break
                except subprocess.TimeoutExpired:
                    pending = None
            if process.returncode:
                raise RuntimeError('Waze gesture failed: ' + error[-500:])
        finally:
            if process.poll() is None:
                process.terminate()  # Sender releases mouse/Ctrl in its finally block.
                try:
                    process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=1)
