# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Present a user-started, dedicated nested Weston without owning Android."""
import os
import subprocess
from pathlib import Path


class WaydroidSurfacePlayer:
    """Implement the hosted-surface lifecycle used by BrowserMediaScreen.

    The POI launcher already requested the application. Do not call show-full-ui:
    Waydroid 1.6.2 uses it to select the whole Android desktop and reset its policy.
    Weston, its session, installed apps and navigation survive closing the panel.
    """

    window_class = "Weston Compositor"

    def vertical_crop(self):
        """The kiosk shell has no desktop panel to trim."""
        runtime = os.environ.get('XDG_RUNTIME_DIR')
        if runtime:
            try:
                pid = int((Path(runtime) / 'openroadcode-waydroid-kiosk').read_text().strip())
                command = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
                if b'--shell=kiosk-shell.so' in command:
                    return (0, 48)
            except (OSError, ValueError):
                pass
        return (32, 48)

    def play(self, target, *, display, window_position=None, window_size=None):
        del target, window_position, window_size
        environment = dict(os.environ, DISPLAY=display)
        environment['WAYLAND_DISPLAY'] = os.environ.get('ORC_WAYDROID_DISPLAY', 'wayland-0')
        # Never choose arbitrarily between multiple user compositors.
        result = subprocess.run(
            ['xdotool', 'search', '--class', '^Weston Compositor$'],
            env=environment, capture_output=True, text=True, timeout=3, check=False)
        windows = {line for line in result.stdout.splitlines() if line.strip().isdigit()}
        if result.returncode != 0 or len(windows) != 1:
            raise RuntimeError('Start exactly one dedicated Weston compositor before opening Android')
        return True

    def request_theme_refresh(self):
        """Repaint ORC chrome without restarting the external Android activity."""

    def stop(self):
        """The frontend detaches the borrowed window; no Android process is owned."""
