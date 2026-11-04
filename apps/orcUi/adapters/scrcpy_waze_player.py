# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own one scrcpy virtual-display viewer for native Waze on Termux X11."""
import os
import logging
import re
import shlex
from pathlib import Path
import subprocess
import tempfile
from threading import Event, Lock, Thread
from uuid import uuid4
from common.logging.structured import event


class ScrcpyWazePlayer:
    window_class = None

    def __init__(self, *, retain_session=False):
        self._process = None
        self._process_lock = Lock()
        self._pending_destination = None
        self._destination_cancel = Event()
        self._retain_session = retain_session
        self._log_path = None
        self._log_offset = 0
        self.window_name = f'OpenRoadCode Waze Android {uuid4().hex}'

    def vertical_crop(self):
        return (0, 0)

    def request_theme_refresh(self):
        """Android owns its theme; do not restart an active route."""

    def prepare_destination(self, uri):
        """Queue a deep link for the next owned virtual display, never the phone display."""
        with self._process_lock:
            self._pending_destination = uri

    def play(self, target, *, display, window_position=None, window_size=None):
        del target, window_position
        with self._process_lock:
            process = self._process
            if self._retain_session and process is not None and process.poll() is None:
                uri, self._pending_destination = self._pending_destination, None
                if uri is not None:
                    self._destination_cancel.set()
                    cancelled = self._destination_cancel = Event()
                    Thread(target=self._deliver_destination,
                           args=(process, cancelled, uri, self._log_path, self._log_offset), daemon=True).start()
                return True
        self.stop()
        # An old viewer may still be tearing down while a new one starts.
        # Never let X11 discovery select that retired process's window.
        self.window_name = f'OpenRoadCode Waze Android {uuid4().hex}'
        width, height = window_size or (1280, 720)
        # Match the host aspect ratio instead of letterboxing a fixed 16:9
        # display. Keep enough Android pixels for legible app layouts and use
        # even dimensions for the video encoder.
        width, height = max(1, int(width)), max(1, int(height))
        scale = max(1280 / width, 720 / height)
        display_width = max(2, round(width * scale / 2) * 2)
        display_height = max(2, round(height * scale / 2) * 2)
        renderer = os.environ.get('ORC_SCRCPY_RENDERER', 'opengl')
        if renderer not in ('opengl', 'opengles2', 'software'):
            raise ValueError('ORC_SCRCPY_RENDERER must be opengl, opengles2 or software')
        command = ['scrcpy', f'--new-display={display_width}x{display_height}/240', '--start-app=com.waze',
                   '--no-audio', '--window-borderless', f'--window-title={self.window_name}',
                   f'--render-driver={renderer}', f'--window-width={width}', f'--window-height={height}']
        # SDL may reapply its startup position after X11 reparenting. Desktop
        # coordinates would then become an offset inside ORC and clip the view.
        # The embedder owns placement; the viewer starts at the same local origin.
        command.extend(('--window-x=0', '--window-y=0'))
        environment = dict(os.environ, DISPLAY=display, SDL_VIDEODRIVER='x11')
        log_path = Path(os.environ.get('TMPDIR') or tempfile.gettempdir()) / 'orc-scrcpy-waze.log'
        with log_path.open('ab') as log:
            log_offset = log.tell()
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
        with self._process_lock:
            self._process = process
            self._log_path, self._log_offset = log_path, log_offset
            uri, self._pending_destination = self._pending_destination, None
            cancelled = self._destination_cancel = Event()
        if uri is not None:
            Thread(target=self._deliver_destination,
                   args=(process, cancelled, uri, log_path, log_offset), daemon=True).start()
        return True

    def stop(self):
        self._destination_cancel.set()
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
    def _deliver_destination(process, cancelled, uri, log_path, log_offset):
        logger = logging.getLogger('navigation.waze')
        try:
            for _ in range(200):
                if cancelled.wait(.1):
                    return
                if process.poll() is not None:
                    break
                with log_path.open('rb') as stream:
                    stream.seek(log_offset)
                    match = re.search(rb'New display:[^\r\n]*\(id=(\d+)\)', stream.read(262144))
                if match is None:
                    continue
                display_id = int(match[1])
                if display_id <= 0 or cancelled.is_set():
                    return
                # adb shell joins arguments again; quote the URI's ampersand for
                # the remote shell as well as avoiding a host shell entirely.
                command = shlex.join(['am', 'start', '--display', str(display_id),
                    '-a', 'android.intent.action.VIEW', '-d', uri, '-p', 'com.waze'])
                result = subprocess.run(['adb', 'shell', command], capture_output=True,
                                        text=True, timeout=5, check=False)
                if result.returncode or any(word in result.stdout + result.stderr
                        for word in ('Error:', 'Exception', 'unable to resolve')):
                    break
                event(logger, logging.INFO, 'destination.sent', 'Waze destination sent to the virtual display')
                return
        except (OSError, subprocess.SubprocessError):
            pass
        event(logger, logging.WARNING, 'destination.failed',
              'Could not deliver the Waze destination to the virtual display; retry from ORC')

    @staticmethod
    def _stop_process(process):
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
