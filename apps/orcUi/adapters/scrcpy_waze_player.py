# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own one scrcpy virtual-display viewer for native Waze on Termux X11."""
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Lock, Thread
from uuid import uuid4


class ScrcpyWazePlayer:
    window_class = None

    def __init__(self):
        self._process = None
        self._process_lock = Lock()
        self.window_name = f'OpenRoadCode Waze Android {uuid4().hex}'

    def vertical_crop(self):
        return (0, 0)

    def request_theme_refresh(self):
        """Android owns its theme; do not restart an active route."""

    def play(self, target, *, display, window_position=None, window_size=None):
        del target
        self.stop()
        # An old viewer may still be tearing down while a new one starts.
        # Never let X11 discovery select that retired process's window.
        self.window_name = f'OpenRoadCode Waze Android {uuid4().hex}'
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
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
        with self._process_lock:
            self._process = process
        return True

    def stop(self):
        with self._process_lock:
            process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        # Signal synchronously so application shutdown cannot strand the viewer;
        # only the potentially slow wait/kill/reap belongs on the worker.
        Thread(target=self._stop_process, args=(process,), daemon=True).start()

    @staticmethod
    def _stop_process(process):
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
