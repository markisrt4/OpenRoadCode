# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted runit control used by the local Android/Termux integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
from urllib.request import urlopen


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
    profile_labels: dict[str, str] | None = None
    input_state: str | None = None
    input_detail: str | None = None


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
        "openroadcode-navigation": ("local", "remote", "simulated"),
        "openroadcode-automotive": ("local", "remote", "simulated"),
    }
    PROFILE_LABELS = {
        "local": "Android Bridge",
        "remote": "Device Hardware",
        "simulated": "Simulated",
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
        profile = self.profile(name)
        input_state, input_detail = self._input_health(name, state, profile)
        return ServiceStatus(
            name=name,
            state=state,
            detail=detail,
            profile=profile,
            available_profiles=self.available_profiles(name),
            profile_labels=(dict(self.PROFILE_LABELS) if self.available_profiles(name) else None),
            input_state=input_state,
            input_detail=input_detail,
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
            return "local"
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


    @staticmethod
    def _input_health(name: str, state: str, profile: str | None) -> tuple[str | None, str | None]:
        if name == "openroadcode-automotive":
            return RunitServiceManager._automotive_input_health(state, profile)
        if name != "openroadcode-navigation" or profile != "local":
            return None, None
        if state != "running":
            return "stopped", "Local phone input not in use"
        try:
            with urlopen("http://127.0.0.1:8766/health", timeout=0.5) as response:
                payload = json.load(response)
        except (OSError, ValueError, json.JSONDecodeError):
            return "waiting", "Waiting for Android Sensor Bridge"
        if payload.get("status") != "ready":
            return "waiting", "Android Sensor Bridge is not ready"
        imu_ready = (
            int(payload.get("accelerometer_samples", 0) or 0) > 0
            and int(payload.get("gyroscope_samples", 0) or 0) > 0
        )
        location_ready = payload.get("location_ready") is True
        if imu_ready and location_ready:
            return "connected", "Phone motion + GPS connected"
        missing = []
        if not imu_ready:
            missing.append("motion")
        if not location_ready:
            missing.append("GPS")
        return "waiting", "Waiting for " + " + ".join(missing)

    @staticmethod
    def _automotive_input_health(state: str, profile: str | None) -> tuple[str | None, str | None]:
        if state != "running":
            return "stopped", "Automotive input not in use"
        if profile == "simulated":
            return "connected", "Simulated vehicle data active"
        if profile != "local":
            return None, None
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 35000), timeout=0.5):
                pass
        except OSError:
            return "waiting", "Waiting for local ELM327 bridge"
        return "connected", "Local ELM327 bridge connected"

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
