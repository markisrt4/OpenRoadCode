# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Launch and own the native MapLibre renderer for an embedded UI host."""

from __future__ import annotations

import os
import shlex
import subprocess
import logging
import threading
from common.logging.structured import JsonStore, collect_native_output, event
from pathlib import Path

from apps.launchers.process_manager import find_matching_processes, terminate_process

_MAP_RENDERER_PROCESS_PATTERN = r"(^|/)openroadcode-map-renderer([[:space:]]|$)"


class MapRendererLauncher:
    """Own one native renderer process embedded in an X11 parent window."""

    def __init__(
        self,
        *,
        command: list[str] | None = None,
        log_file: str | Path | None = None,
    ) -> None:
        self._command = command
        self._log_file = Path(log_file) if log_file else None
        self._process: subprocess.Popen[str] | None = None
        self._collector: threading.Thread | None = None

    def is_running(self) -> bool:
        """Return whether the renderer process owned by this launcher is alive."""

        if self._process is None:
            return False
        if self._process.poll() is None:
            return True
        if self._collector:
            self._collector.join(timeout=2)
        event(
            logging.getLogger("map_renderer.lifecycle"),
            logging.ERROR,
            "process.exited",
            "Map renderer exited unexpectedly",
            child_pid=self._process.pid,
            exit_code=self._process.returncode,
        )
        self._process = None
        return False

    def launch(self, *, display: str, parent_window_id: int) -> None:
        """Start the renderer and reparent its native window into ``parent_window_id``."""

        if self.is_running():
            return

        # A renderer left behind by an interrupted/restarted UI is not owned by
        # this launcher instance. Kill it before starting the renderer that will
        # consume the freshly generated theme style. Otherwise the stale process
        # can keep displaying the previous style and make theme changes appear
        # to have been ignored.
        self._terminate_stale_renderers()

        command = self._command or _default_command()
        environment = os.environ.copy()
        environment.update(
            {
                "DISPLAY": display,
                "OPENROADCODE_MAP_PARENT_WINDOW": str(parent_window_id),
            }
        )

        store = JsonStore(self._log_file)
        self._process = subprocess.Popen(
            command,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._collector = threading.Thread(
            target=collect_native_output,
            args=(self._process.stdout, store, self._process.pid),
            name="orc-renderer-logs",
            daemon=True,
        )
        self._collector.start()
        event(
            logging.getLogger("map_renderer.lifecycle"),
            logging.INFO,
            "process.started",
            "Map renderer process started",
            child_pid=self._process.pid,
        )

    def stop(self) -> None:
        """Stop the renderer process owned by this launcher."""

        if self._process is None:
            return
        child_pid = self._process.pid
        terminate_process(self._process)
        if self._collector:
            self._collector.join(timeout=2)
        event(
            logging.getLogger("map_renderer.lifecycle"),
            logging.INFO,
            "process.stopped",
            "Map renderer process stopped",
            child_pid=child_pid,
        )
        self._process = None

    @staticmethod
    def _terminate_stale_renderers() -> None:
        """Terminate renderer processes not owned by this launcher instance."""

        current_pid = os.getpid()
        for process in find_matching_processes(_MAP_RENDERER_PROCESS_PATTERN):
            if process.pid == current_pid:
                continue
            try:
                os.kill(process.pid, 15)
            except ProcessLookupError:
                pass


def _default_command() -> list[str]:
    override = os.environ.get("OPENROADCODE_MAP_RENDERER_COMMAND")
    if override:
        return shlex.split(override)

    repo_root = Path(__file__).resolve().parents[2]
    prefix = os.environ.get("PREFIX", "")
    if prefix.startswith("/data/data/com.termux/files/usr"):
        return [
            "bash",
            str(repo_root / "development" / "termux" / "start_map_renderer.sh"),
        ]

    return ["bash", str(repo_root / "scripts" / "runtime" / "start_map_renderer.sh")]
