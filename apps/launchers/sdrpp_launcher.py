import os
import shutil
import signal
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

from apps.launchers.app_launcher_if import AppLauncherIf
from apps.launchers.process_manager import is_process_running, kill_process_pattern


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
    mode="WFM",
    step_hz=25_000,
    start_frequency_hz=162_550_000,
)

HAM_RADIO_PROFILE = SDRPPProfile(
    name="Ham Radio",
    mode="FM",
    step_hz=1_000,
    start_frequency_hz=450_000_000,
)

class SDRPPLauncher(AppLauncherIf):
    def __init__(
        self,
        profile: SDRPPProfile = FM_BROADCAST_PROFILE,
        log_file: str = "/tmp/carsdr-sdrpp.log",
        fullscreen: bool = True,
        resource_manager=None,
        owner_name: str = "sdrpp",
    ):
        self.profile = profile
        self.log_file = log_file
        self.fullscreen = fullscreen
        self._process: Optional[subprocess.Popen] = None
        self.resource_manager = resource_manager
        self.owner_name = owner_name

    def is_running(self) -> bool:
        if self._process is not None and self._process.poll() is None:
            return True
        return is_process_running("sdrpp") or is_process_running("sdr\\+\\+")

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
    
        if self.is_running():
            if set_status:
                set_status(f"SDR++ already running: {self.profile.name}")
            return

        sdrpp_path = shutil.which("sdrpp") or shutil.which("sdr++")
        if not sdrpp_path:
            raise RuntimeError("Could not find sdrpp or sdr++ in PATH")

        env = os.environ.copy()
        env["DISPLAY"] = remote_display
        env["XDG_SESSION_TYPE"] = "x11"
        env["GDK_BACKEND"] = "x11"
        env["LIBGL_ALWAYS_SOFTWARE"] = "1"
        
        self._process = subprocess.Popen(
            [sdrpp_path],
            env=env,
            stdout=open(self.log_file, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        if self.fullscreen:
            subprocess.Popen(
                [
                    "bash",
                    "-lc",
                    (
                        f'sleep 2; '
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
            set_status(
                f"SDR++ launched on {remote_display} for {self.profile.name}. "
                f"Set mode={self.profile.mode}, step={self.profile.step_hz} Hz."
            )

    def stop(
        self,
        set_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        if self._process is not None and self._process.poll() is None:
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)

        kill_process_pattern("sdrpp")
        kill_process_pattern("sdr\\+\\+")

        self._process = None

        if set_status:
            set_status("SDR++ stopped")

    def toggle(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> bool:
        if self.is_running():
            self.stop(set_status=set_status)
            return False

        self.launch(remote_display=remote_display, set_status=set_status)
        return True
