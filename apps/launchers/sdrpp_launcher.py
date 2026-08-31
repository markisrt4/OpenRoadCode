# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import shlex
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    StatusCallback,
)
from apps.launchers.process_manager import (
    close_matching_display_apps,
    is_process_running,
    terminate_process,
)
from common.logging.logging_paths import logging_file_path


DEFAULT_TERMUX_SDRPP_SOURCE = Path("/root/SDRPlusPlus")
DEFAULT_TERMUX_PROOT_DISTRIBUTION = "debian"


@dataclass(frozen=True, slots=True)
class SDRPPProfile:
    """Define SDR++ startup mode, tuning step, and optional frequency."""
    name: str
    mode: str
    step_hz: int
    start_frequency_hz: int | None = None


class SDRPPLauncher(AppLauncherIf):
    """Launch SDR++ and wait for its RigCTL server."""

    def __init__(
        self,
        *,
        profile: SDRPPProfile,
        log_file: str | Path | None = None,
        fullscreen: bool = True,
        embedded: bool = False,
        resource_manager=None,
        owner_name: str = "sdrpp",
        rigctl_host: str = "127.0.0.1",
        rigctl_port: int = 4532,
        rigctl_timeout_seconds: float = 15.0,
        termux_proot_distribution: str = DEFAULT_TERMUX_PROOT_DISTRIBUTION,
        termux_sdrpp_source: str | Path = DEFAULT_TERMUX_SDRPP_SOURCE,
    ) -> None:
        self.profile = profile
        self.log_file = Path(
            log_file
            or logging_file_path(
                "openroadcode",
                "sdrpp.log",
            )
        )
        self.fullscreen = fullscreen
        self.embedded = embedded
        self.resource_manager = resource_manager
        self.owner_name = owner_name
        self.rigctl_host = rigctl_host
        self.rigctl_port = rigctl_port
        self.rigctl_timeout_seconds = rigctl_timeout_seconds
        self.termux_proot_distribution = termux_proot_distribution
        self.termux_sdrpp_source = Path(termux_sdrpp_source)
        self._process: subprocess.Popen[str] | None = None
        self._launched_via_proot = False

    def is_running(self) -> bool:
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None

        return (
            is_process_running("sdrpp")
            or is_process_running("sdr\\+\\+")
        )

    def launch(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        if self.resource_manager is not None:
            self.resource_manager.acquire(
                self.owner_name,
                force=True,
                set_status=set_status,
            )

        _stop_readsb_service()

        if self.is_running():
            if self.is_rigctl_ready():
                _status(
                    set_status,
                    f"SDR++ already ready: {self.profile.name}",
                )
                return

            _status(set_status, "Waiting for existing SDR++ RigCTL...")
            self.wait_for_rigctl()
            return

        command = self._launch_command(remote_display)
        self._launched_via_proot = _is_proot_command(command)
        environment = _sdrpp_environment(remote_display)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
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

        if self.fullscreen and not self.embedded:
            self._request_fullscreen(remote_display, environment)

        mode = "embedded" if self.embedded else "standalone"
        _status(
            set_status,
            f"SDR++ launched ({mode}); waiting for RigCTL...",
        )
        self.wait_for_rigctl()
        _status(
            set_status,
            f"SDR++ ready: {self.profile.name}",
        )

    def stop(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        if self._process is not None:
            terminate_process(self._process)
            self._process = None
        self._launched_via_proot = False

        close_matching_display_apps(
            display=remote_display,
            patterns=("sdrpp", "sdr\\+\\+"),
        )
        _status(set_status, "SDR++ stopped")

    def toggle(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> bool:
        if self.is_running():
            self.stop(remote_display, set_status)
            return False

        self.launch(remote_display, set_status)
        return True

    def window_process_id(self, timeout_seconds: float = 8.0) -> int:
        """Return the process ID that owns SDR++'s X11 window."""
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("SDR++ is not running under this launcher")

        if not self._launched_via_proot:
            return self._process.pid

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            pid = _find_descendant_matching(
                self._process.pid,
                ("./build/sdrpp", "/build/sdrpp", "SDRPlusPlus"),
            )
            if pid is not None:
                return pid
            time.sleep(0.1)

        raise RuntimeError("Could not find SDR++ child process inside proot")

    def is_rigctl_ready(self) -> bool:
        try:
            with socket.create_connection(
                (self.rigctl_host, self.rigctl_port),
                timeout=0.5,
            ):
                return True
        except OSError:
            return False

    def wait_for_rigctl(self) -> None:
        deadline = time.monotonic() + self.rigctl_timeout_seconds
        last_error: OSError | None = None

        while time.monotonic() < deadline:
            if (
                self._process is not None
                and self._process.poll() is not None
            ):
                raise RuntimeError(
                    "SDR++ exited before RigCTL became ready. "
                    f"Check log: {self.log_file}"
                )

            try:
                with socket.create_connection(
                    (self.rigctl_host, self.rigctl_port),
                    timeout=0.5,
                ):
                    return
            except OSError as exc:
                last_error = exc
                time.sleep(0.5)

        raise RuntimeError(
            "RigCTL did not become ready at "
            f"{self.rigctl_host}:{self.rigctl_port}: {last_error}"
        )

    def _launch_command(self, display: str) -> list[str]:
        executable = shutil.which("sdrpp") or shutil.which("sdr++")
        if executable is not None:
            return [executable, "--autostart"]

        if not _is_termux():
            raise RuntimeError("Could not find sdrpp or sdr++ in PATH")

        proot_distro = shutil.which("proot-distro")
        if proot_distro is None:
            raise RuntimeError(
                "Could not find native SDR++ or proot-distro on Termux"
            )

        source = str(self.termux_sdrpp_source)
        shell_command = (
            f"cd {shlex.quote(source)} && "
            "exec ./build/sdrpp -r root_dev --autostart"
        )
        return [
            proot_distro,
            "login",
            self.termux_proot_distribution,
            "--",
            "env",
            f"DISPLAY={display}",
            "XDG_SESSION_TYPE=x11",
            "GDK_BACKEND=x11",
            "LIBGL_ALWAYS_SOFTWARE=1",
            "bash",
            "-lc",
            shell_command,
        ]

    def _request_fullscreen(
        self,
        display: str,
        environment: dict[str, str],
    ) -> None:
        subprocess.Popen(
            [
                "bash",
                "-lc",
                (
                    f'sleep 3; DISPLAY="{display}" '
                    'wmctrl -r "SDR++" -b add,fullscreen'
                ),
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )


def _is_proot_command(command: list[str]) -> bool:
    return bool(command and Path(command[0]).name == "proot-distro")


def _find_descendant_matching(
    root_pid: int,
    command_fragments: tuple[str, ...],
) -> int | None:
    """Find a descendant process whose command line identifies SDR++."""
    pending = [root_pid]
    seen: set[int] = set()
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)

        if pid != root_pid:
            cmdline = _read_proc_cmdline(pid)
            if any(fragment in cmdline for fragment in command_fragments):
                return pid

        pending.extend(_read_proc_children(pid))
    return None


def _read_proc_children(pid: int) -> list[int]:
    path = Path(f"/proc/{pid}/task/{pid}/children")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return []
    if not text:
        return []
    return [int(value) for value in text.split() if value.isdigit()]


def _read_proc_cmdline(pid: int) -> str:
    path = Path(f"/proc/{pid}/cmdline")
    try:
        return path.read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        return ""


def _is_termux() -> bool:
    """Return True when running from the native Termux userspace."""
    if os.getenv("TERMUX_VERSION"):
        return True
    prefix = os.getenv("PREFIX", "")
    return prefix.startswith("/data/data/com.termux/")


def _stop_readsb_service() -> bool:
    """Stop readsb when systemd tooling exists on the current host."""
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return False

    sudo = shutil.which("sudo")
    command = [systemctl, "stop", "readsb"]
    if sudo is not None:
        command.insert(0, sudo)

    try:
        subprocess.run(command, check=False)
    except OSError:
        return False

    return True


def _sdrpp_environment(display: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DISPLAY": display,
            "XDG_SESSION_TYPE": "x11",
            "GDK_BACKEND": "x11",
            "LIBGL_ALWAYS_SOFTWARE": "1",
        }
    )
    return environment


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
