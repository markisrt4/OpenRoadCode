"""Embed an X11 application window inside an existing X11 host window."""

from __future__ import annotations

import re
import shutil
import subprocess
import time

from .window_embedder_if import WindowEmbedderIf


class X11WindowEmbedder(WindowEmbedderIf):
    """Use xdotool to reparent an application window into an ORC frontend host."""

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

    def embed(
        self,
        process_id: int,
        host_window_id: int,
        width: int,
        height: int,
        window_name: str | None = None,
    ) -> int:
        """Find an X11 client and reparent it into *host_window_id*.

        Process-based lookup is attempted first. Some proot/X11 combinations do not
        expose a useful ``_NET_WM_PID`` property, so callers may supply *window_name*
        as a fallback selector. Name lookup intentionally includes unmapped windows
        so a client can survive while its ORC panel is temporarily destroyed.
        """
        if not self.supported():
            raise RuntimeError("xdotool is required for embedded X11 windows")

        deadline = time.monotonic() + self._timeout_seconds
        window_id: int | None = None
        while time.monotonic() < deadline:
            window_id = self._find_by_process(process_id)
            if window_id is None and window_name:
                window_id = self._find_by_name(window_name)
            if window_id is not None:
                break
            time.sleep(0.1)

        if window_id is None:
            suffix = f" or window name {window_name!r}" if window_name else ""
            raise RuntimeError(
                f"no X11 window found for process {process_id}{suffix}"
            )

        subprocess.run(
            ["xdotool", "windowreparent", str(window_id), str(host_window_id)],
            check=True,
        )
        subprocess.run(
            ["xdotool", "windowmap", str(window_id)],
            check=False,
        )
        self._window_id = window_id
        self.resize(width, height)
        return window_id

    def detach(self, parent_window_id: int) -> None:
        """Move the client to a stable parent and hide it between ORC panels."""
        if self._window_id is None:
            return
        window_id = self._window_id
        subprocess.run(
            ["xdotool", "windowreparent", str(window_id), str(parent_window_id)],
            check=False,
        )
        subprocess.run(
            ["xdotool", "windowunmap", str(window_id)],
            check=False,
        )
        self._window_id = None

    @staticmethod
    def _find_by_process(process_id: int) -> int | None:
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--pid", str(process_id)],
            capture_output=True,
            text=True,
            check=False,
        )
        return X11WindowEmbedder._last_window_id(result)

    @staticmethod
    def _find_by_name(window_name: str) -> int | None:
        # xdotool treats --name as a regular expression. Escape literal names such
        # as "SDR++" so '+' is not interpreted as a regex quantifier.
        result = subprocess.run(
            ["xdotool", "search", "--name", re.escape(window_name)],
            capture_output=True,
            text=True,
            check=False,
        )
        return X11WindowEmbedder._last_window_id(result)

    @staticmethod
    def _last_window_id(result: subprocess.CompletedProcess[str]) -> int | None:
        if result.returncode != 0:
            return None
        candidates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not candidates:
            return None
        return int(candidates[-1])

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
