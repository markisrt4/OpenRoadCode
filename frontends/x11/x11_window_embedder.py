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

    def embed(
        self,
        process_id: int,
        host_window_id: int,
        width: int,
        height: int,
        *,
        window_name: str | None = None,
        window_class: str | None = None,
    ) -> int:
        """Find, reparent, map, and size an X11 client inside the host window."""
        if not self.supported():
            raise RuntimeError("xdotool is required for embedded X11 windows")

        deadline = time.monotonic() + self._timeout_seconds
        last_error: subprocess.SubprocessError | None = None
        while time.monotonic() < deadline:
            window_id = self._find_by_process(process_id)
            if window_id is None and window_class:
                window_id = self._find_by_class(window_class)
            if window_id is None and window_name:
                window_id = self._find_by_name(window_name)
            if window_id is None:
                time.sleep(0.1)
                continue
            try:
                subprocess.run(["xdotool", "windowreparent", str(window_id), str(host_window_id)], check=True, capture_output=True, text=True)
                subprocess.run(["xdotool", "windowmap", str(window_id)], check=True, capture_output=True, text=True)
                self._window_id = window_id
                self.resize(width, height)
                subprocess.run(["xdotool", "sync", str(window_id)], check=False, capture_output=True)
                time.sleep(0.05)
                self.resize(width, height)
                return window_id
            except subprocess.SubprocessError as error:
                last_error = error
                self._window_id = None
                time.sleep(0.15)

        selectors = []
        if process_id > 0:
            selectors.append(f"process {process_id}")
        if window_class:
            selectors.append(f"window class {window_class!r}")
        if window_name:
            selectors.append(f"window name {window_name!r}")
        target = " or ".join(selectors) or "requested application"
        detail = f"; last X11 error: {last_error}" if last_error else ""
        raise RuntimeError(f"no usable X11 window found for {target}{detail}")

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
    def _find_by_class(window_class: str) -> int | None:
        escaped = re.escape(window_class)
        visible = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", escaped], capture_output=True, text=True, check=False)
        window_id = X11WindowEmbedder._best_window_id(visible)
        if window_id is not None:
            return window_id
        result = subprocess.run(["xdotool", "search", "--class", escaped], capture_output=True, text=True, check=False)
        return X11WindowEmbedder._best_window_id(result)

    @staticmethod
    def _find_by_name(window_name: str) -> int | None:
        escaped = re.escape(window_name)
        visible = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", escaped], capture_output=True, text=True, check=False)
        window_id = X11WindowEmbedder._best_window_id(visible)
        if window_id is not None:
            return window_id
        result = subprocess.run(["xdotool", "search", "--name", escaped], capture_output=True, text=True, check=False)
        return X11WindowEmbedder._best_window_id(result)

    @staticmethod
    def _last_window_id(result: subprocess.CompletedProcess[str]) -> int | None:
        """Return the last parsed result, retained for existing callers/tests."""
        if result.returncode != 0:
            return None
        candidates = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        if not candidates:
            return None
        return int(candidates[-1])

    @staticmethod
    def _best_window_id(result: subprocess.CompletedProcess[str]) -> int | None:
        if result.returncode != 0:
            return None
        candidates: list[int] = []
        for line in (result.stdout or "").splitlines():
            try:
                candidates.append(int(line.strip()))
            except ValueError:
                continue
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        best_id = candidates[-1]
        best_area = -1
        for window_id in candidates:
            geometry = subprocess.run(["xdotool", "getwindowgeometry", "--shell", str(window_id)], capture_output=True, text=True, check=False)
            if geometry.returncode != 0:
                continue
            width = height = 0
            has_geometry = False
            for line in (geometry.stdout or "").splitlines():
                if line.startswith("WIDTH="):
                    try:
                        width = int(line[6:])
                        has_geometry = True
                    except ValueError:
                        pass
                elif line.startswith("HEIGHT="):
                    try:
                        height = int(line[7:])
                        has_geometry = True
                    except ValueError:
                        pass
            if not has_geometry:
                continue
            area = width * height
            if area > best_area:
                best_area = area
                best_id = window_id
        return best_id

    def resize(self, width: int, height: int) -> None:
        if self._window_id is None:
            return
        width = max(1, int(width)); height = max(1, int(height))
        subprocess.run(["xdotool", "windowsize", str(self._window_id), str(width), str(height)], check=False)
        subprocess.run(["xdotool", "windowmove", str(self._window_id), "0", "0"], check=False)

    def clear(self) -> None:
        self._window_id = None
