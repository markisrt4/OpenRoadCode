# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Control a preconfigured, dedicated readsb systemd service."""

import subprocess


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
        state = self._state()
        # Process state alone cannot prove that readsb opened the assigned SDR.
        # Until hardware readiness evidence is available, fail closed.
        return self._receiver_ready(state)

    def _receiver_ready(self, state: dict[str, str]) -> bool:
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
