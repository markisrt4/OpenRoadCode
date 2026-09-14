# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted runit control used by the local Android/Termux integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = Path.home() / ".config/openroadcode/service-profiles"


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Current state of one supervised OpenRoadCode service."""

    name: str
    state: str
    detail: str
    profile: str | None = None
    available_profiles: tuple[str, ...] = ()


class RunitServiceManager:
    """Control only the explicitly supported OpenRoadCode runit services."""

    SERVICES = (
        "openroadcode-message-broker",
        "openroadcode-navigation",
        "openroadcode-automotive",
        "openroadcode-adsb",
    )
    CORE_STACK = (
        "openroadcode-message-broker",
        "openroadcode-navigation",
        "openroadcode-automotive",
    )
    PROFILE_CONFIGS = {
        "openroadcode-navigation": ("phone", "target", "simulated"),
        "openroadcode-automotive": ("phone", "target", "simulated"),
    }

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
        return ServiceStatus(
            name=name,
            state=state,
            detail=detail,
            profile=self.profile(name),
            available_profiles=self.available_profiles(name),
        )

    def all_status(self) -> tuple[ServiceStatus, ...]:
        return tuple(self.status(name) for name in self.SERVICES)

    def available_profiles(self, name: str) -> tuple[str, ...]:
        self._validate(name)
        return tuple(self.PROFILE_CONFIGS.get(name, ()))

    def profile(self, name: str) -> str | None:
        profiles = self.PROFILE_CONFIGS.get(name)
        if not profiles:
            return None
        selected = self._profile_file(name)
        if not selected.exists():
            return "target"
        content = selected.read_text(encoding="utf-8")
        for profile in profiles:
            if f"OPENROADCODE_RUNTIME_PROFILE={profile}" in content:
                return profile
            if f'OPENROADCODE_RUNTIME_PROFILE="{profile}"' in content:
                return profile
        return "custom"

    def set_profile(self, name: str, profile: str) -> ServiceStatus:
        self._validate(name)
        profiles = self.PROFILE_CONFIGS.get(name)
        if not profiles:
            raise ValueError(f"Service does not support profiles: {name}")
        if profile not in profiles:
            raise ValueError(f"Unsupported profile for {name}: {profile}")

        was_running = self.status(name).state == "running"
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        profile_file = self._profile_file(name)
        profile_file.write_text(
            f'export OPENROADCODE_RUNTIME_PROFILE="{profile}"\n',
            encoding="utf-8",
        )
        if was_running:
            self._sv("restart", name)
        return self.status(name)

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
        for name in reversed(self.CORE_STACK):
            self._sv("down", name)
        return tuple(self.status(name) for name in self.CORE_STACK)

    @classmethod
    def _validate(cls, name: str) -> None:
        if name not in cls.SERVICES:
            raise ValueError(f"Unsupported OpenRoadCode service: {name}")

    @staticmethod
    def _profile_file(name: str) -> Path:
        return PROFILE_DIR / f"{name}.env"

    @staticmethod
    def _sv(action: str, name: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sv", action, name],
            check=check,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
