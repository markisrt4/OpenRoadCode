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
        return shutil.which("xdotool") is not None

    @property
    def window_id(self) -> int | None:
        return self._window_id

    def embed(self, process_id: int, host_window_id: int, width: int, height: int, window_name: str | None = None) -> int:
        """Find, reparent, map, and size an X11 client inside the host window.

        Proot frequently makes ``_NET_WM_PID`` unusable, so name lookup is a
        supported fallback.  When several matching SDR++ windows exist we choose
        the largest one instead of trusting xdotool's arbitrary result order.
        """
        if not self.supported():
            raise RuntimeError("xdotool is required for embedded X11 windows")

        deadline = time.monotonic() + self._timeout_seconds
        last_error: subprocess.SubprocessError | None = None
        while time.monotonic() < deadline:
            window_id = self._find_by_process(process_id)
            if window_id is None and window_name:
                window_id = self._find_by_name(window_name)
            if window_id is None:
                time.sleep(0.1)
                continue

            try:
                subprocess.run(["xdotool", "windowreparent", str(window_id), str(host_window_id)], check=True, capture_output=True, text=True)
                subprocess.run(["xdotool", "windowmap", str(window_id)], check=True, capture_output=True, text=True)
                self._window_id = window_id
                # X11/Termux:X11 can process reparent and map asynchronously.  A
                # second geometry pass after sync avoids the occasional blank host.
                self.resize(width, height)
                subprocess.run(["xdotool", "sync", str(window_id)], check=False, capture_output=True)
                time.sleep(0.05)
                self.resize(width, height)
                return window_id
            except subprocess.SubprocessError as error:
                last_error = error
                self._window_id = None
                time.sleep(0.15)

        suffix = f" or window name {window_name!r}" if window_name else ""
        detail = f"; last X11 error: {last_error}" if last_error else ""
        raise RuntimeError(f"no usable X11 window found for process {process_id}{suffix}{detail}")

    def detach(self, parent_window_id: int) -> None:
        if self._window_id is None:
            return
        window_id = self._window_id
        subprocess.run(["xdotool", "windowreparent", str(window_id), str(parent_window_id)], check=False)
        subprocess.run(["xdotool", "windowunmap", str(window_id)], check=False)
        self._window_id = None

    @staticmethod
    def _find_by_process(process_id: int) -> int | None:
        if process_id <= 0:
            return None
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(process_id)], capture_output=True, text=True, check=False)
        return X11WindowEmbedder._best_window_id(result)

    @staticmethod
    def _find_by_name(window_name: str) -> int | None:
        escaped = re.escape(window_name)
        # Prefer the currently visible main window.  Detached ORC clients are
        # intentionally unmapped, so fall back to all matching windows when needed.
        visible = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", escaped], capture_output=True, text=True, check=False)
        window_id = X11WindowEmbedder._best_window_id(visible)
        if window_id is not None:
            return window_id
        result = subprocess.run(["xdotool", "search", "--name", escaped], capture_output=True, text=True, check=False)
        return X11WindowEmbedder._best_window_id(result)

    @staticmethod
    def _best_window_id(result: subprocess.CompletedProcess[str]) -> int | None:
        if result.returncode != 0:
            return None
        candidates: list[int] = []
        for line in result.stdout.splitlines():
            try:
                candidates.append(int(line.strip()))
            except ValueError:
                continue
        if not candidates:
            return None

        best_id = candidates[-1]
        best_area = -1
        for window_id in candidates:
            geometry = subprocess.run(["xdotool", "getwindowgeometry", "--shell", str(window_id)], capture_output=True, text=True, check=False)
            if geometry.returncode != 0:
                continue
            values: dict[str, int] = {}
            for line in geometry.stdout.splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in {"WIDTH", "HEIGHT"}:
                    try:
                        values[key] = int(value)
                    except ValueError:
                        pass
            area = values.get("WIDTH", 0) * values.get("HEIGHT", 0)
            if area > best_area:
                best_area = area
                best_id = window_id
        return best_id

    # Kept for compatibility with older tests/helpers.
    _last_window_id = _best_window_id

    def resize(self, width: int, height: int) -> None:
        if self._window_id is None:
            return
        width = max(1, int(width)); height = max(1, int(height))
        subprocess.run(["xdotool", "windowsize", str(self._window_id), str(width), str(height)], check=False)
        subprocess.run(["xdotool", "windowmove", str(self._window_id), "0", "0"], check=False)

    def clear(self) -> None:
        self._window_id = None
