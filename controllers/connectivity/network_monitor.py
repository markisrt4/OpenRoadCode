# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Local network observations; internet checks remain the portable fallback."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import urllib.request
from collections.abc import Callable


def android_network_state() -> bool | None:
    """Read Android's validation state over loopback, never through an HTTP proxy."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8766/network', timeout=0.75) as response:
            state = json.loads(response.read(4096))
        if state.get('available') is not True:
            return None
        connected, validated = state.get('connected'), state.get('validated')
        if not isinstance(connected, bool) or not isinstance(validated, bool):
            return None
        return connected and validated
    except (OSError, ValueError, AttributeError):
        return None


def linux_network_state(executable: str) -> bool | None:
    """Query NetworkManager through nmcli's D-Bus client, without activating a check."""
    try:
        result = subprocess.run(
            [executable, '-t', '-f', 'STATE,CONNECTIVITY', 'general'],
            capture_output=True, text=True, check=False, timeout=2,
            env={**os.environ, 'LC_ALL': 'C'},
        )
        if result.returncode:
            return None
        state, _, connectivity = result.stdout.strip().partition(':')
        if state in {'disconnected', 'asleep', 'disconnecting', 'connecting'}:
            return False
        if state.startswith('connected'):
            if connectivity in {'none', 'portal', 'limited'}:
                return False
            # Unknown means NM's connectivity check is disabled; ORC must verify.
            if connectivity in {'full', 'unknown'}:
                return True
        return None
    except (OSError, subprocess.TimeoutExpired):
        return None


class NetworkMonitor:
    """Emit changes from Android or NetworkManager, with bounded shutdown."""
    def __init__(self, notify: Callable[[bool | None], None]) -> None:
        self._notify = notify
        self._stop = threading.Event()
        self._process: subprocess.Popen | None = None
        self._process_lock = threading.Lock()
        self._last = object()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name='orc-network-monitor', daemon=True)
        self._thread.start()

    def _emit(self, state: bool | None) -> None:
        if not self._stop.is_set() and state != self._last:
            self._last = state
            self._notify(state)

    def _run(self) -> None:
        if os.environ.get('TERMUX_VERSION') or os.path.exists('/system/bin/am'):
            while not self._stop.is_set():
                self._emit(android_network_state())
                self._stop.wait(1)
            return
        executable = shutil.which('nmcli')
        if executable is None:
            self._emit(None)
            return
        while not self._stop.is_set():
            self._emit(linux_network_state(executable))
            process = None
            try:
                with self._process_lock:
                    if self._stop.is_set():
                        return
                    process = subprocess.Popen(
                        [executable, 'monitor'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        text=True, env={**os.environ, 'LC_ALL': 'C'},
                    )
                    self._process = process
                if process.stdout is not None:
                    for _line in process.stdout:
                        if self._stop.is_set():
                            break
                        self._emit(linux_network_state(executable))
            except (OSError, ValueError):
                pass
            finally:
                self._terminate(process)
                with self._process_lock:
                    if self._process is process:
                        self._process = None
            self._emit(None)
            self._stop.wait(5)

    @staticmethod
    def _terminate(process: subprocess.Popen | None) -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=0.5)
        except OSError:
            pass
        finally:
            if process.stdout is not None:
                process.stdout.close()

    def close(self) -> None:
        self._stop.set()
        with self._process_lock:
            process = self._process
        self._terminate(process)
