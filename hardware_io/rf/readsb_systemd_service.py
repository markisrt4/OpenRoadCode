# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Control a preconfigured, dedicated readsb systemd service."""

import subprocess
import time
from pathlib import Path


class ReadsbSystemdService:
    """Use deployment-provisioned permissions and a fixed receiver assignment."""

    def __init__(self, serial: str, *, timeout: float = 15.0) -> None:
        if not serial or timeout <= 0:
            raise ValueError("serial and positive timeout required")
        self._serial = serial
        self._timeout = timeout

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["systemctl", "--no-ask-password", *args, "readsb.service"],
            capture_output=True,
            text=True,
            timeout=self._timeout,
            check=False,
        )

    def _state(self) -> dict[str, str]:
        result = self._run(
            "show",
            "--property=ActiveState,SubState,MainPID,ControlPID,ControlGroup",
        )
        if result.returncode:
            return {}
        return dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )

    def start(self, serial: str) -> bool:
        """Start only the receiver provisioned by the deployment layer."""
        if serial != self._serial:
            return False
        if not self.stop():
            return False
        if self._run("start").returncode:
            return False
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            if self._receiver_ready(self._state()):
                return True
            time.sleep(0.2)
        return False

    def _receiver_ready(self, state: dict[str, str]) -> bool:
        if state.get("ActiveState") != "active":
            return False
        pid = state.get("MainPID", "")
        if not pid.isdecimal() or int(pid) <= 0:
            return False
        try:
            matches = []
            for device in Path("/sys/bus/usb/devices").iterdir():
                try:
                    if (
                        (device / "serial").read_text().strip() == self._serial
                        and (device / "idVendor").read_text().strip() == "0bda"
                        and (device / "idProduct").read_text().strip() in {"2832", "2838"}
                    ):
                        bus = int((device / "busnum").read_text())
                        address = int((device / "devnum").read_text())
                        matches.append(Path(f"/dev/bus/usb/{bus:03d}/{address:03d}"))
                except (OSError, ValueError):
                    continue
            if len(matches) != 1:
                return False
            for fd in (Path("/proc") / pid / "fd").iterdir():
                try:
                    if fd.readlink() == matches[0]:
                        return True
                except OSError:
                    continue
        except OSError:
            return False
        return False

    def stop(self) -> bool:
        """Require a stopped unit and no remaining systemd control group."""
        if self._run("stop").returncode:
            return False
        state = self._state()
        return (
            state.get("ActiveState") == "inactive"
            and state.get("SubState") == "dead"
            and state.get("MainPID") == "0"
            and state.get("ControlPID") == "0"
            and state.get("ControlGroup") == ""
        )
