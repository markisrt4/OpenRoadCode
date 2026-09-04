"""Run commands in a Debian environment without exposing how Debian is hosted."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path


class DebianCommandRunner:
    """Execute commands in native Debian or a Debian proot-distro environment."""

    DISTRO_NAME = "debian"
    _VIRGL_SOCKET_NAME = ".virgl_test"

    def __init__(self) -> None:
        self._mode = self._detect_mode()

    @classmethod
    def supported(cls) -> bool:
        """Return whether a usable Debian environment can be reached."""
        return cls._detect_mode() is not None

    @property
    def is_proot(self) -> bool:
        """Return whether Debian is hosted through proot-distro."""
        return self._mode == "proot"

    @classmethod
    def _detect_mode(cls) -> str | None:
        prefix = os.environ.get("PREFIX", "")
        in_termux = "com.termux" in prefix

        if not in_termux and shutil.which("apt-get") and shutil.which("dpkg-query"):
            return "native"

        if shutil.which("proot-distro"):
            result = subprocess.run(
                ["proot-distro", "login", cls.DISTRO_NAME, "--", "true"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                return "proot"

        return None

    def command(self, args: Sequence[str], *, shared_tmp: bool = False) -> list[str]:
        """Return the host command required to execute *args* inside Debian."""
        if self._mode == "native":
            return list(args)
        if self._mode == "proot":
            command = ["proot-distro", "login", self.DISTRO_NAME]
            if shared_tmp:
                command.append("--shared-tmp")
            command.extend(["--", *args])
            return command
        raise RuntimeError("No Debian environment is available")

    def graphical_command(self, args: Sequence[str]) -> list[str]:
        """Return a command suitable for launching a graphical Debian application.

        Native Debian receives the command unchanged.  Under Termux/proot, ORC
        shares the X11 socket and uses Mesa's virpipe client when the Android
        virgl renderer is installed.  This keeps Bionic GPU libraries out of
        the glibc process while still providing hardware-accelerated OpenGL.
        """
        if self._mode == "native":
            return list(args)
        if self._mode != "proot":
            raise RuntimeError("No Debian environment is available")

        environment: list[str] = []
        display = os.environ.get("DISPLAY")
        if display:
            environment.append(f"DISPLAY={display}")
        environment.append("XDG_RUNTIME_DIR=/tmp")

        if self._ensure_virgl_server():
            environment.extend((
                "LIBGL_ALWAYS_SOFTWARE=true",
                "GALLIUM_DRIVER=virpipe",
            ))

        return self.command(["env", *environment, *args], shared_tmp=True)

    def _ensure_virgl_server(self) -> bool:
        """Start Termux's virgl renderer when available and return success."""
        server = shutil.which("virgl_test_server_android")
        tmpdir = os.environ.get("TMPDIR")
        if not server or not tmpdir:
            return False

        socket_path = Path(tmpdir) / self._VIRGL_SOCKET_NAME
        if socket_path.exists():
            return True

        try:
            subprocess.Popen(
                [server, "--no-fork", "--socket-path", str(socket_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return False

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if socket_path.exists():
                return True
            time.sleep(0.05)
        return False

    def run(self, args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess:
        """Execute *args* in Debian and return the completed process."""
        return subprocess.run(self.command(args), **kwargs)
