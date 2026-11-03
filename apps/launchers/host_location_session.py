# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Reuse navigation or own a user-session producer; never require sudo at runtime."""
import os
from pathlib import Path
import socket
import subprocess
import sys
from threading import Event, Lock, Thread

from services.navigation.navigation_command_client import (
    NavigationCommandClient, NavigationCommandError, NavigationCommandUnavailableError,
)


class HostLocationSessionError(RuntimeError):
    """A user-actionable startup failure without raw supervisor output."""


class HostLocationSession:
    def __init__(self, client=None):
        self._client = client if client is not None else NavigationCommandClient()
        self._owned = []
        self._lock = Lock()
        self._start_lock = Lock()
        self._closed = Event()

    @staticmethod
    def _listening(port):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.3):
                return True
        except OSError:
            return False

    def start(self):
        with self._start_lock:
            self._start()

    def _start(self):
        if self._closed.is_set():
            return
        try:
            self._client.prepare_host_location()
            return
        except NavigationCommandError as error:
            raise HostLocationSessionError('Navigation needs an update before location sharing can start. Restart navigation, then retry.') from error
        except NavigationCommandUnavailableError:
            if self._listening(5560):
                raise HostLocationSessionError('Navigation is busy. Please try location sharing again in a moment.')
        with self._lock:
            if self._closed.is_set() or any(module == 'services.navigation.navigation_service_cli'
                                           and process.poll() is None for module, process in self._owned):
                return
        if not self._listening(5556):
            if self._listening(5557):
                raise HostLocationSessionError('The location messaging service is unavailable. Restart ORC and retry.')
            with self._lock:
                broker_running = any(module == 'messaging.zeromq.broker_cli' and process.poll() is None
                                     for module, process in self._owned)
            if not broker_running:
                self._spawn('messaging.zeromq.broker_cli', '--publisher-endpoint', 'tcp://127.0.0.1:5556',
                            '--subscriber-endpoint', 'tcp://127.0.0.1:5557')
        self._spawn('services.navigation.navigation_service_cli', '--profile', 'local')

    def _spawn(self, module, *arguments):
        if self._closed.is_set():
            return
        root = Path(__file__).resolve().parents[2]
        process = subprocess.Popen([sys.executable, '-m', module, *arguments], cwd=root,
            env=dict(os.environ, PYTHONUNBUFFERED='1'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with self._lock:
            if not self._closed.is_set():
                self._owned.append((module, process))
                return
        process.terminate()
        Thread(target=self._reap, args=(process,), daemon=True).start()

    @staticmethod
    def _reap(process):
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)

    def close(self):
        self._closed.set()
        with self._lock:
            owned, self._owned = self._owned, []
        for _, process in reversed(owned):
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                Thread(target=self._reap, args=(process,), daemon=True).start()
