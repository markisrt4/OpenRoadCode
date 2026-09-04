# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted runit control used by the local Android/Termux integration."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Current state of one supervised OpenRoadCode service."""

    name: str
    state: str
    detail: str


class RunitServiceManager:
    """Control only the explicitly supported OpenRoadCode runit services."""

    SERVICES = (
        "openroadcode-broker",
        "openroadcode-navigation",
        "openroadcode-automotive",
        "openroadcode-adsb",
    )
    CORE_STACK = (
        "openroadcode-broker",
        "openroadcode-navigation",
        "openroadcode-automotive",
    )

    def status(self, name: str) -> ServiceStatus:
        self._validate(name)
        result = self._sv("status", name, check=False)
        detail = (result.stdout or result.stderr).strip()
        if detail.startswith("run:"):
            state = "running"
        elif detail.startswith("down:"):
            state = "stopped"
        else:
            state = "unknown"
        return ServiceStatus(name=name, state=state, detail=detail)

    def all_status(self) -> tuple[ServiceStatus, ...]:
        return tuple(self.status(name) for name in self.SERVICES)

    def start(self, name: str) -> ServiceStatus:
        self._validate(name)
        self._sv("up", name)
        return self.status(name)

    def stop(self, name: str) -> ServiceStatus:
        self._validate(name)
        self._sv("down", name)
        return self.status(name)

    def restart(self, name: str) -> ServiceStatus:
        self._validate(name)
        self._sv("restart", name)
        return self.status(name)

    def start_core(self) -> tuple[ServiceStatus, ...]:
        for name in self.CORE_STACK:
            self._sv("up", name)
        return tuple(self.status(name) for name in self.CORE_STACK)

    def stop_core(self) -> tuple[ServiceStatus, ...]:
        # Stop consumers before the infrastructure they consume.
        for name in reversed(self.CORE_STACK):
            self._sv("down", name)
        return tuple(self.status(name) for name in self.CORE_STACK)

    @classmethod
    def _validate(cls, name: str) -> None:
        if name not in cls.SERVICES:
            raise ValueError(f"Unsupported OpenRoadCode service: {name}")

    @staticmethod
    def _sv(action: str, name: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sv", action, name],
            check=check,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
