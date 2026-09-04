# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Launch SDR++ without teaching frontends about host-specific process details."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


@dataclass
class SDRPPProcess:
    """Handle for one SDR++ launch owned by OpenRoadCode."""

    process: subprocess.Popen
    launch_mode: str

    @property
    def pid(self) -> int:
        return self.process.pid

    @property
    def is_running(self) -> bool:
        return self.process.poll() is None

    def stop(self, timeout_s: float = 3.0) -> None:
        if not self.is_running:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout_s)


class SDRPPLauncher:
    """Choose native SDR++ or the Termux Debian/proot build at runtime."""

    def __init__(self, *, display: str | None = None) -> None:
        self._display = display or os.environ.get("DISPLAY", ":1")

    def launch(self) -> SDRPPProcess:
        if self._is_termux():
            return self._launch_termux_proot()
        return self._launch_native()

    @staticmethod
    def _is_termux() -> bool:
        prefix = os.environ.get("PREFIX", "")
        return "com.termux" in prefix or Path("/data/data/com.termux/files/usr").exists()

    def _launch_native(self) -> SDRPPProcess:
        executable = shutil.which("sdrpp")
        if executable is None:
            raise RuntimeError("SDR++ is not installed on this host")
        env = os.environ.copy()
        env["DISPLAY"] = self._display
        process = subprocess.Popen([executable], env=env)
        return SDRPPProcess(process=process, launch_mode="native")

    def _launch_termux_proot(self) -> SDRPPProcess:
        proot_distro = shutil.which("proot-distro")
        if proot_distro is None:
            raise RuntimeError("proot-distro is required to launch SDR++ on Termux")

        command = (
            "export DISPLAY=:1; "
            "export XDG_RUNTIME_DIR=/tmp/runtime-root; "
            "export XDG_SESSION_TYPE=x11; "
            "export GDK_BACKEND=x11; "
            "export LIBGL_ALWAYS_SOFTWARE=1; "
            "unset WAYLAND_DISPLAY; "
            "mkdir -p \"$XDG_RUNTIME_DIR\"; chmod 700 \"$XDG_RUNTIME_DIR\"; "
            "cd ~/SDRPlusPlus; exec ./build/sdrpp -r root_dev"
        )
        process = subprocess.Popen(
            [proot_distro, "login", "debian", "--shared-tmp", "--", "bash", "-lc", command],
            env=os.environ.copy(),
        )
        return SDRPPProcess(process=process, launch_mode="termux-proot")
