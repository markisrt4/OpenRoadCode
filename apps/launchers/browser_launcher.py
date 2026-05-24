import os
import shutil
import subprocess
from typing import Callable, Optional

from apps.launchers.app_launcher_if import AppLauncherIf
from apps.launchers.process_manager import (
    close_matching_display_apps,
    is_process_running,
    kill_process_pattern,
)

class BrowserKioskLauncher(AppLauncherIf):
    def __init__(
        self,
        url: str,
        process_pattern: str = "chromium",
        log_file: str = "/tmp/carsdr-browser.log",
    ):
        self.url = url
        self.process_pattern = process_pattern
        self.log_file = log_file
        self._process: Optional[subprocess.Popen] = None

    def _find_browser(self) -> str:
        browser = (
            shutil.which("chromium-browser")
            or shutil.which("chromium")
            or shutil.which("google-chrome")
        )

        if not browser:
            raise RuntimeError("Could not find chromium-browser, chromium, or google-chrome")

        return browser

    def is_running(self) -> bool:
        if self._process is not None and self._process.poll() is None:
            return True
        return is_process_running(self.process_pattern)

    def launch(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        if self.is_running():
            if set_status:
                set_status("Browser already running")
            return

        browser_path = self._find_browser()

        env = os.environ.copy()
        env["DISPLAY"] = remote_display
        env["XDG_SESSION_TYPE"] = "x11"
        env["GDK_BACKEND"] = "x11"

        command = [
            browser_path,
            "--kiosk",
            "--noerrdialogs",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-restore-session-state",
            self.url,
        ]

        log = open(self.log_file, "a")

        self._process = subprocess.Popen(
            command,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        if set_status:
            set_status(f"Browser launched on {remote_display}")

    def stop(self, set_status=None) -> None:
        kill_process_pattern(self.process_pattern)
        self._process = None

        if set_status:
            set_status("Browser stopped")

            if set_status:
                set_status("Browser stopped")

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

