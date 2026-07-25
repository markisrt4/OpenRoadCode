from __future__ import annotations

import os
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
        resource_manager=None,
        owner_name: str = "sdrpp",
        rigctl_host: str = "127.0.0.1",
        rigctl_port: int = 4532,
        rigctl_timeout_seconds: float = 15.0,
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
        self.resource_manager = resource_manager
        self.owner_name = owner_name
        self.rigctl_host = rigctl_host
        self.rigctl_port = rigctl_port
        self.rigctl_timeout_seconds = rigctl_timeout_seconds
        self._process: subprocess.Popen[str] | None = None

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

        subprocess.run(
            ["sudo", "systemctl", "stop", "readsb"],
            check=False,
        )

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

        executable = shutil.which("sdrpp") or shutil.which("sdr++")
        if executable is None:
            raise RuntimeError("Could not find sdrpp or sdr++ in PATH")

        environment = _sdrpp_environment(remote_display)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                [executable, "--autostart"],
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        finally:
            log_handle.close()

        if self.fullscreen:
            self._request_fullscreen(remote_display, environment)

        _status(set_status, "SDR++ launched; waiting for RigCTL...")
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
