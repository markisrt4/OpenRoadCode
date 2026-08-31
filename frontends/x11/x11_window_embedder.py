"""Embed an X11 application window inside an existing X11 host window."""

from __future__ import annotations

import shutil
import subprocess
import time

from .window_embedder_if import WindowEmbedderIf


class X11WindowEmbedder(WindowEmbedderIf):
    """Use xdotool to reparent a process window into an ORC frontend host."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._window_id: int | None = None

    @staticmethod
    def supported() -> bool:
        """Return whether the xdotool helper is available."""
        return shutil.which("xdotool") is not None

    @property
    def window_id(self) -> int | None:
        return self._window_id

    def embed(self, process_id: int, host_window_id: int, width: int, height: int) -> int:
        """Find the visible X11 window for *process_id* and reparent it into *host_window_id*."""
        if not self.supported():
            raise RuntimeError("xdotool is required for embedded X11 windows")

        deadline = time.monotonic() + self._timeout_seconds
        window_id: int | None = None
        while time.monotonic() < deadline:
            result = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--pid", str(process_id)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                candidates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                if candidates:
                    window_id = int(candidates[-1])
                    break
            time.sleep(0.1)

        if window_id is None:
            raise RuntimeError(f"no visible X11 window found for process {process_id}")

        subprocess.run(
            ["xdotool", "windowreparent", str(window_id), str(host_window_id)],
            check=True,
        )
        self._window_id = window_id
        self.resize(width, height)
        return window_id

    def resize(self, width: int, height: int) -> None:
        """Resize the currently embedded client to match its ORC host."""
        if self._window_id is None:
            return
        width = max(1, int(width))
        height = max(1, int(height))
        subprocess.run(
            ["xdotool", "windowsize", str(self._window_id), str(width), str(height)],
            check=False,
        )
        subprocess.run(
            ["xdotool", "windowmove", str(self._window_id), "0", "0"],
            check=False,
        )

    def clear(self) -> None:
        """Forget the embedded window after its application exits."""
        self._window_id = None
