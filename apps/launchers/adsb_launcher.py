import subprocess
import time
from typing import Callable, Optional

from apps.launchers.app_launcher_if import AppLauncherIf
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.process_manager import (
    is_process_running,
    kill_process_pattern,
    close_display_apps,
)


class ADSBLauncher(AppLauncherIf):
    def __init__(
        self,
        url: str = "http://127.0.0.1/tar1090",
        readsb_log: str = "/tmp/carsdr-readsb.log",
        close_existing_display_apps: bool = False,
        resource_manager=None,
        owner_name: str = "adsb",
    ):
        self.url = url
        self.readsb_log = readsb_log
        self.close_existing_display_apps = close_existing_display_apps
        self.resource_manager = resource_manager
        self.owner_name = owner_name

        self.browser = BrowserKioskLauncher(
            url=url,
            process_pattern="127.0.0.1/tar1090",
            log_file="/tmp/carsdr-adsb-browser.log",
        )

        self._readsb_proc: Optional[subprocess.Popen] = None

    def services_running(self) -> bool:
        return is_process_running("readsb") and is_process_running("tar1090")

    def is_running(self) -> bool:
        return self.browser.is_running()

    def launch(self, remote_display=":2", set_status=None) -> None:

        if self.resource_manager:
            self.resource_manager.acquire(
                self.owner_name,
                force=True,
                set_status=set_status,
            )

        kill_process_pattern("sdrpp")
        kill_process_pattern("sdr\\+\\+")
        subprocess.run(["sudo", "systemctl", "start", "readsb"], check=False)

        self.browser.launch(
            remote_display=remote_display,
            set_status=set_status,
        )

        if set_status:
            set_status("Launching ADS-B dashboard...")

        if self.close_existing_display_apps:
            close_display_apps(display=remote_display)

        if not is_process_running("readsb"):
            if set_status:
                set_status("readsb is not running. Start readsb service first.")
            return

        self.browser.launch(
            remote_display=remote_display,
            set_status=set_status,
        )

        if set_status:
            set_status("ADS-B dashboard launched")

    def stop(self, set_status=None) -> None:
        self.browser.stop(set_status=None)

        if set_status:
            set_status("ADS-B dashboard closed")

    def toggle(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> bool:
        if self.browser.is_running():
            self.stop(set_status=set_status)
            return False

        self.launch(
            remote_display=remote_display,
            set_status=set_status,
        )
        return True
    
    def wait_for_readsb(self, timeout_seconds: float = 5.0) -> bool:
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            if is_process_running("readsb"):
                return True
            time.sleep(0.25)

        return False
