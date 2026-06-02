import os
import shutil
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Optional

from apps.launchers.app_launcher_if import AppLauncherIf
from apps.launchers.process_manager import (
    close_matching_display_apps,
    is_process_running,
)

@dataclass(frozen=True)
class SDRPPProfile:
    name: str
    mode: str
    step_hz: int
    start_frequency_hz: Optional[int] = None


FM_BROADCAST_PROFILE = SDRPPProfile(
    name="FM Broadcast",
    mode="WFM",
    step_hz=200_000,
    start_frequency_hz=88_100_000,
)

AIRBAND_AM_PROFILE = SDRPPProfile(
    name="Airband AM",
    mode="AM",
    step_hz=25_000,
    start_frequency_hz=125_000_000,
)

WEATHER_NOAA_PROFILE = SDRPPProfile(
    name="NOAA Weather Radio",
    mode="NFM",
    step_hz=25_000,
    start_frequency_hz=162_550_000,
)

HAM_RADIO_PROFILE = SDRPPProfile(
    name="Ham Radio",
    mode="NFM",
    step_hz=1_000,
    start_frequency_hz=450_000_000,
)

from modules.logging.logging_paths import app_logging_file

class SDRPPLauncher(AppLauncherIf):
    def __init__(
        self,
        profile: SDRPPProfile = FM_BROADCAST_PROFILE,
        log_file: Optional[str] = None,
        fullscreen: bool = True,
        resource_manager=None,
        owner_name: str = "sdrpp",
        rigctl_host: str = "127.0.0.1",
        rigctl_port: int = 4532,
        rigctl_timeout_sec: float = 15.0,
    ):
        self.profile = profile
        self.log_file = (
            log_file
            or app_logging_file(
                "carsdr",
                "carsdr-sdrpp.log",
            )
        )
        self.fullscreen = fullscreen
        self._process: Optional[subprocess.Popen] = None
        self.resource_manager = resource_manager
        self.owner_name = owner_name
        self.rigctl_host = rigctl_host
        self.rigctl_port = rigctl_port
        self.rigctl_timeout_sec = rigctl_timeout_sec

    def is_running(self) -> bool:
        if self._process is not None and self._process.poll() is None:
            return True

        return is_process_running("sdrpp") or is_process_running("sdr\\+\\+")

    def is_rigctl_ready(self) -> bool:
        try:
            with socket.create_connection(
                (self.rigctl_host, self.rigctl_port),
                timeout=0.5,
            ):
                return True
        except OSError:
            return False

    def wait_for_rigctl(
        self,
        set_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        deadline = time.time() + self.rigctl_timeout_sec
        last_error: Optional[BaseException] = None

        while time.time() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"SDR++ exited before rigctl became ready. "
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
            f"rigctl not ready after SDR++ launch: {last_error}. "
            f"Expected {self.rigctl_host}:{self.rigctl_port}. "
            f"Check SDR++ Rigctl Server module and log: {self.log_file}"
        )

    def launch(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        if self.resource_manager:
            self.resource_manager.acquire(
                self.owner_name,
                force=True,
                set_status=set_status,
            )

        subprocess.run(["sudo", "systemctl", "stop", "readsb"], check=False)

        if self._process is not None and self._process.poll() is not None:
            self._process = None
            
        if self.is_running():
            if self.is_rigctl_ready():
                if set_status:
                    set_status(f"SDR++ already running and rigctl ready: {self.profile.name}")
                return

            if set_status:
                set_status("SDR++ already running, waiting for rigctl...")

            try:
                self.wait_for_rigctl(set_status=set_status)
            except Exception as exc:
                if set_status:
                    set_status(f"SDR++ launched, rigctl not ready yet: {exc}")
            return

        sdrpp_path = shutil.which("sdrpp") or shutil.which("sdr++")
        if not sdrpp_path:
            raise RuntimeError("Could not find sdrpp or sdr++ in PATH")

        env = os.environ.copy()
        env["DISPLAY"] = remote_display
        env["XDG_SESSION_TYPE"] = "x11"
        env["GDK_BACKEND"] = "x11"
        env["LIBGL_ALWAYS_SOFTWARE"] = "1"

        if set_status:
            set_status(f"Launching SDR++ on {remote_display}...")

        with open(self.log_file, "a", encoding="utf-8") as log:
            log.write("\n\n========== Launching SDR++ ==========\n")
            log.write(f"display={remote_display}\n")
            log.write(f"profile={self.profile.name}\n")
            log.flush()

            self._process = subprocess.Popen(
                [sdrpp_path, "--autostart"],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        if self.fullscreen:
            subprocess.Popen(
                [
                    "bash",
                    "-lc",
                    (
                        f'sleep 3; '
                        f'DISPLAY="{remote_display}" '
                        'wmctrl -r "SDR++" -b add,fullscreen'
                    ),
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        if set_status:
            set_status("SDR++ launched. Waiting for rigctl...")

        try:
            self.wait_for_rigctl(set_status=set_status)
        except Exception as exc:
            if set_status:
                set_status(f"SDR++ launched, rigctl not ready yet: {exc}")

        if set_status:
            set_status(
                f"SDR++ ready on {remote_display}: {self.profile.name}. "
                f"mode={self.profile.mode}, step={self.profile.step_hz} Hz."
            )

    def stop(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        if self._process is not None and self._process.poll() is None:
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

        close_matching_display_apps(
            display=remote_display,
            patterns=[
                "sdrpp",
                "sdr\\+\\+",
            ],
        )

        self._process = None

        time.sleep(0.25)

        if set_status:
            set_status("SDR++ stopped")

    def toggle(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> bool:
        if self.is_running():
            self.stop(
                remote_display=remote_display,
                set_status=set_status,
            )
            return False

        self.launch(remote_display=remote_display, set_status=set_status)
        return True
