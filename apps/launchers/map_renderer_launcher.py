# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Launch and own the native MapLibre renderer for an embedded UI host."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from apps.launchers.process_manager import terminate_process


class MapRendererLauncher:
    """Own one native renderer process embedded in an X11 parent window."""

    def __init__(
        self,
        *,
        command: list[str] | None = None,
        log_file: str | Path | None = None,
    ) -> None:
        self._command = command
        self._log_file = Path(
            log_file
            or Path.home() / ".cache" / "openroadcode" / "map-renderer.log"
        )
        self._process: subprocess.Popen[str] | None = None

    def is_running(self) -> bool:
        """Return whether the renderer process owned by this launcher is alive."""

        if self._process is None:
            return False
        if self._process.poll() is None:
            return True
        self._process = None
        return False

    def launch(self, *, display: str, parent_window_id: int) -> None:
        """Start the renderer and reparent its native window into ``parent_window_id``."""

        if self.is_running():
            return

        command = self._command or _default_command()
        environment = os.environ.copy()
        environment.update(
            {
                "DISPLAY": display,
                "OPENROADCODE_MAP_PARENT_WINDOW": str(parent_window_id),
            }
        )

        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self._log_file.open("a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                command,
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        finally:
            log_handle.close()

    def stop(self) -> None:
        """Stop the renderer process owned by this launcher."""

        if self._process is None:
            return
        terminate_process(self._process)
        self._process = None


def _default_command() -> list[str]:
    override = os.environ.get("OPENROADCODE_MAP_RENDERER_COMMAND")
    if override:
        return shlex.split(override)

    repo_root = Path(__file__).resolve().parents[2]
    termux_launcher = repo_root / "development" / "termux" / "start_map_renderer.sh"
    if termux_launcher.is_file():
        return ["bash", str(termux_launcher)]

    raise RuntimeError(
        "No map renderer launcher is configured. Set "
        "OPENROADCODE_MAP_RENDERER_COMMAND."
    )
