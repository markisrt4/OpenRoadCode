# SPDX-License-Identifier: MIT
"""Managed native librespot Spotify Connect receiver.

This adapter owns the receiver process, not the Spotify Web API or UI.
The receiver needs Spotify Premium and a compatible local audio backend.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

LOGGER = logging.getLogger("media.spotify.librespot")


class LibrespotReceiver:
    """Start and stop a native Spotify Connect receiver without a browser."""

    def __init__(
        self,
        *,
        executable: str = "librespot",
        name: str = "OpenRoadCode",
        backend: str | None = None,
        cache_dir: str | Path | None = None,
        network_allowed: Callable[[], bool] = lambda: True,
    ) -> None:
        self._executable = executable
        self._name = name
        self._backend = backend
        self._cache_dir = Path(cache_dir).expanduser() if cache_dir else Path.home() / ".cache" / "openroadcode" / "librespot"
        self._network_allowed = network_allowed
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None

    @property
    def available(self) -> bool:
        return shutil.which(self._executable) is not None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        """Launch the receiver. Discovery and authentication happen asynchronously."""
        with self._lock:
            if not self._network_allowed():
                raise RuntimeError("Spotify receiver unavailable while offline")
            if self.running:
                return
            executable = shutil.which(self._executable)
            if executable is None:
                raise RuntimeError("librespot executable not found")
            self._cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(self._cache_dir, 0o700)
            command = [executable, "--name", self._name, "--cache", str(self._cache_dir)]
            if self._backend:
                command.extend(["--backend", self._backend])
            self._process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            LOGGER.info("Started librespot receiver pid=%s", self._process.pid)

    def stop(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)

    def close(self) -> None:
        self.stop()
