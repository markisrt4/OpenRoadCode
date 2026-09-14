# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted systemd control for OpenRoadCode services on Linux hosts."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess


SYSTEMCTL_BIN = os.environ.get("OPENROADCODE_SYSTEMCTL", "/usr/bin/systemctl")
PRIVILEGED_ACTIONS = {"start", "stop", "restart"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = Path(
    os.environ.get("OPENROADCODE_SERVICE_PROFILE_DIR", "/var/lib/openroadcode/service-profiles")
)


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Current state of one managed OpenRoadCode service."""

    name: str
    state: str
    detail: str
    profile: str | None = None
    available_profiles: tuple[str, ...] = ()


class SystemdServiceManager:
    """Control only the explicitly supported OpenRoadCode systemd services."""

    SERVICE_UNITS = {
        "openroadcode-message-broker": "openroadcode-message-broker.service",
        "openroadcode-navigation": "openroadcode-navigation.service",
        "openroadcode-automotive": "openroadcode-automotive.service",
        "openroadcode-adsb": "readsb.service",
    }
    SERVICES = tuple(SERVICE_UNITS)
    CORE_STACK = (
        "openroadcode-message-broker",
        "openroadcode-navigation",
        "openroadcode-automotive",
    )
    PROFILE_CONFIGS = {
        "openroadcode-navigation": {
            "live": PROJECT_ROOT / "config/runtime.toml",
            "simulated": PROJECT_ROOT / "config/runtime.simulated.toml",
        },
        "openroadcode-automotive": {
            "live": PROJECT_ROOT / "config/runtime.toml",
            "simulated": PROJECT_ROOT / "config/runtime.simulated.toml",
        },
    }

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
        self._unit(name)
        return tuple(self.PROFILE_CONFIGS.get(name, ()))

    def profile(self, name: str) -> str | None:
        profiles = self.PROFILE_CONFIGS.get(name)
        if not profiles:
            return None
        selected = self._profile_file(name)
        if not selected.exists():
            return "live"
        content = selected.read_text(encoding="utf-8")
        for profile, config_path in profiles.items():
            if str(config_path) in content:
                return profile
        return "custom"

    def set_profile(self, name: str, profile: str) -> ServiceStatus:
        profiles = self.PROFILE_CONFIGS.get(name)
        if not profiles:
            raise ValueError(f"Service does not support profiles: {name}")
        try:
            config_path = profiles[profile]
        except KeyError as exc:
            raise ValueError(f"Unsupported profile for {name}: {profile}") from exc
        if not config_path.is_file():
            raise ValueError(f"Runtime profile config not found: {config_path}")

        was_running = self.status(name).state == "running"
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        profile_file = self._profile_file(name)
        temporary = profile_file.with_suffix(".tmp")
        escaped = str(config_path).replace("\\", "\\\\").replace('"', '\\"')
        temporary.write_text(
            f'OPENROADCODE_RUNTIME_CONFIG="{escaped}"\n',
            encoding="utf-8",
        )
        temporary.chmod(0o644)
        temporary.replace(profile_file)
        if was_running:
            self._systemctl("restart", self._unit(name))
        return self.status(name)

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
    def _profile_file(name: str) -> Path:
        return PROFILE_DIR / f"{name}.env"

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
