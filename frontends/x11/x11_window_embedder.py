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
        """Find a visible process-tree window and reparent it into the ORC host."""
        if not self.supported():
            raise RuntimeError("xdotool is required for embedded X11 windows")

        deadline = time.monotonic() + self._timeout_seconds
        window_id: int | None = None
        while time.monotonic() < deadline:
            for candidate_pid in self._process_tree(process_id):
                result = subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--pid", str(candidate_pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    continue
                candidates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                if candidates:
                    window_id = int(candidates[-1])
                    break
            if window_id is not None:
                break
            time.sleep(0.1)

        if window_id is None:
            raise RuntimeError(f"no visible X11 window found for process tree {process_id}")

        subprocess.run(
            ["xdotool", "windowreparent", str(window_id), str(host_window_id)],
            check=True,
        )
        subprocess.run(["xdotool", "windowmap", str(window_id)], check=False)
        self._window_id = window_id

        # Some games perform one or more self-directed window moves immediately
        # after map/reparent. Reassert the host geometry briefly while the game
        # settles so the embedded client does not remain offset or recentered.
        for delay in (0.0, 0.12, 0.28):
            if delay:
                time.sleep(delay)
            self.resize(width, height)
        subprocess.run(["xdotool", "windowraise", str(window_id)], check=False)
        return window_id

    @staticmethod
    def _process_tree(root_pid: int) -> tuple[int, ...]:
        """Return *root_pid* and all currently visible descendants."""
        result = subprocess.run(
            ["ps", "-eo", "pid=,ppid="],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return (root_pid,)

        children: dict[int, list[int]] = {}
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) != 2:
                continue
            try:
                pid, parent = (int(fields[0]), int(fields[1]))
            except ValueError:
                continue
            children.setdefault(parent, []).append(pid)

        ordered: list[int] = [root_pid]
        index = 0
        while index < len(ordered):
            ordered.extend(children.get(ordered[index], ()))
            index += 1
        # Prefer descendants first because wrappers such as proot-distro may
        # create their own helper windows while the actual game owns the child.
        return tuple(reversed(ordered))

    def resize(self, width: int, height: int) -> None:
        """Resize and anchor the currently embedded client to its ORC host."""
        if self._window_id is None:
            return
        width = max(1, int(width))
        height = max(1, int(height))
        subprocess.run(
            ["xdotool", "windowmove", str(self._window_id), "0", "0"],
            check=False,
        )
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
