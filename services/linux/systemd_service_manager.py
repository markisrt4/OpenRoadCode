# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted systemd control for OpenRoadCode services on Linux hosts."""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess


SYSTEMCTL_BIN = os.environ.get("OPENROADCODE_SYSTEMCTL", "/usr/bin/systemctl")
PRIVILEGED_ACTIONS = {"start", "stop", "restart"}


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Current state of one managed OpenRoadCode service."""

    name: str
    state: str
    detail: str


class SystemdServiceManager:
    """Control only the explicitly supported OpenRoadCode systemd services."""

    SERVICE_UNITS = {
        "openroadcode-message-broker": "openroadcode-message-broker.service",
        "openroadcode-navigation": "openroadcode-navigation.service",
        "openroadcode-automotive": "openroadcode-automotive.service",
        # Keep the API name aligned with the Termux manager while controlling
        # the Pi's existing ADS-B runtime unit.
        "openroadcode-adsb": "readsb.service",
    }
    SERVICES = tuple(SERVICE_UNITS)
    CORE_STACK = (
        "openroadcode-message-broker",
        "openroadcode-navigation",
        "openroadcode-automotive",
    )

    def status(self, name: str) -> ServiceStatus:
        unit = self._unit(name)
        active = self._systemctl("is-active", unit, check=False)
        state_text = active.stdout.strip()
        if active.returncode == 0 and state_text == "active":
            state = "running"
        elif state_text in {"inactive", "failed", "deactivating"}:
            state = "stopped"
        else:
            state = "unknown"

        detail_result = self._systemctl(
            "show",
            unit,
            "--property=ActiveState,SubState,UnitFileState",
            "--value",
            check=False,
        )
        detail = " / ".join(
            line.strip() for line in detail_result.stdout.splitlines() if line.strip()
        )
        if not detail:
            detail = (active.stdout or active.stderr).strip()
        return ServiceStatus(name=name, state=state, detail=detail)

    def all_status(self) -> tuple[ServiceStatus, ...]:
        return tuple(self.status(name) for name in self.SERVICES)

    def start(self, name: str) -> ServiceStatus:
        unit = self._unit(name)
        self._systemctl("start", unit)
        return self.status(name)

    def stop(self, name: str) -> ServiceStatus:
        unit = self._unit(name)
        self._systemctl("stop", unit)
        return self.status(name)

    def restart(self, name: str) -> ServiceStatus:
        unit = self._unit(name)
        self._systemctl("restart", unit)
        return self.status(name)

    def start_core(self) -> tuple[ServiceStatus, ...]:
        for name in self.CORE_STACK:
            self._systemctl("start", self._unit(name))
        return tuple(self.status(name) for name in self.CORE_STACK)

    def stop_core(self) -> tuple[ServiceStatus, ...]:
        # Stop consumers before infrastructure.
        for name in reversed(self.CORE_STACK):
            self._systemctl("stop", self._unit(name))
        return tuple(self.status(name) for name in self.CORE_STACK)

    @classmethod
    def _unit(cls, name: str) -> str:
        try:
            return cls.SERVICE_UNITS[name]
        except KeyError as exc:
            raise ValueError(f"Unsupported OpenRoadCode service: {name}") from exc

    @staticmethod
    def _systemctl(
        action: str,
        unit: str,
        *extra: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [SYSTEMCTL_BIN, action, unit, *extra]
        if action in PRIVILEGED_ACTIONS:
            command = ["sudo", "-n", *command]
        return subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
            timeout=8.0,
        )
