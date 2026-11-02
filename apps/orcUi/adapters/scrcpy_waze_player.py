# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own one scrcpy virtual-display viewer for native Waze on Termux X11."""
import os
from pathlib import Path
import subprocess
import tempfile


class ScrcpyWazePlayer:
    window_class = None
    window_name = 'OpenRoadCode Waze Android'

    def __init__(self):
        self._process = None

    def vertical_crop(self):
        return (0, 0)

    def request_theme_refresh(self):
        """Android owns its theme; do not restart an active route."""

    def play(self, target, *, display, window_position=None, window_size=None):
        del target
        self.stop()
        width, height = window_size or (1280, 720)
        renderer = os.environ.get('ORC_SCRCPY_RENDERER', 'opengl')
        if renderer not in ('opengl', 'opengles2', 'software'):
            raise ValueError('ORC_SCRCPY_RENDERER must be opengl, opengles2 or software')
        command = ['scrcpy', '--new-display=1280x720/240', '--start-app=com.waze',
                   '--no-audio', '--window-borderless', f'--window-title={self.window_name}',
                   f'--render-driver={renderer}', f'--window-width={width}', f'--window-height={height}']
        if window_position is not None:
            command.extend((f'--window-x={window_position[0]}', f'--window-y={window_position[1]}'))
        environment = dict(os.environ, DISPLAY=display, SDL_VIDEODRIVER='x11')
        log_path = Path(os.environ.get('TMPDIR') or tempfile.gettempdir()) / 'orc-scrcpy-waze.log'
        with log_path.open('ab') as log:
            self._process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
        return True

    def stop(self):
        process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
