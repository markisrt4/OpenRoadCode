"""Run commands in a Debian environment without exposing how Debian is hosted."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence


class DebianCommandRunner:
    """Execute commands in native Debian or a Debian proot-distro environment."""

    DISTRO_NAME = "debian"

    def __init__(self) -> None:
        self._mode = self._detect_mode()

    @classmethod
    def supported(cls) -> bool:
        """Return whether a usable Debian environment can be reached."""
        return cls._detect_mode() is not None

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

    def run(self, args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess:
        """Execute *args* in Debian and return the completed process."""
        return subprocess.run(self.command(args), **kwargs)
