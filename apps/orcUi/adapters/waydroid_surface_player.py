# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Present a user-started, dedicated nested Weston without owning Android."""
import os
import subprocess


class WaydroidSurfacePlayer:
    """Implement the hosted-surface lifecycle used by BrowserMediaScreen.

    Only the short-lived show-full-ui client belongs to ORC. Weston, its session,
    installed apps and navigation survive closing the panel.
    """

    window_class = "Weston Compositor"

    def __init__(self):
        self._client = None

    def play(self, target, *, display, window_position=None, window_size=None):
        del target, window_position, window_size
        self.stop()
        environment = dict(os.environ, DISPLAY=display)
        environment['WAYLAND_DISPLAY'] = os.environ.get('ORC_WAYDROID_DISPLAY', 'wayland-0')
        # Never choose arbitrarily between multiple user compositors.
        result = subprocess.run(
            ['xdotool', 'search', '--class', '^Weston Compositor$'],
            env=environment, capture_output=True, text=True, timeout=3, check=False)
        windows = {line for line in result.stdout.splitlines() if line.strip().isdigit()}
        if result.returncode != 0 or len(windows) != 1:
            raise RuntimeError('Start exactly one dedicated Weston compositor before opening Android')
        self._client = subprocess.Popen(
            ['waydroid', 'show-full-ui'], env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    def request_theme_refresh(self):
        """Repaint ORC chrome without restarting the external Android activity."""

    def stop(self):
        client, self._client = self._client, None
        if client is not None and client.poll() is None:
            client.terminate()
            try:
                client.wait(timeout=2)
            except subprocess.TimeoutExpired:
                client.kill()
                client.wait(timeout=2)
