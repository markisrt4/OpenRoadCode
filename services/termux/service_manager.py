# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted runit control used by the local Android/Termux integration."""

from __future__ import annotations

import json
import re
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from protocols.sdrforge_control import authorize_local_sdrforge_request
from services.common.service_logging import (
    ServiceStatusLog,
    observed_status,
    service_action,
    supervisor_command,
)

COMPONENT = "runtime.services.runit"


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
    readiness: str | None = None
    readiness_detail: str | None = None


class RunitServiceManager:
    """Control only the explicitly supported OpenRoadCode runit services."""

    SERVICES = (
        "openroadcode-message-broker",
        "openroadcode-valhalla",
        "openroadcode-navigation",
        "openroadcode-automotive",
        "openroadcode-adsb",
        "openroadcode-carbonate",
        "openroadcode-calendar-sync",
        "openroadcode-sdrforge",
    )
    CORE_STACK = (
        "openroadcode-message-broker",
        "openroadcode-valhalla",
        "openroadcode-navigation",
        "openroadcode-automotive",
    )
    PROFILE_CONFIGS = {
        "openroadcode-navigation": ("local", "remote", "simulated"),
        "openroadcode-automotive": ("local", "remote", "simulated"),
        "openroadcode-sdrforge": ("local", "simulated"),
    }
    PROFILE_LABELS = {
        "local": "Android Bridge",
        "remote": "Device Hardware",
        "simulated": "Simulated",
    }

    def __init__(self) -> None:
        self._status_log = ServiceStatusLog()

    @observed_status(COMPONENT)
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
        readiness, readiness_detail = self._readiness(name, state, detail)
        return ServiceStatus(
            name=name,
            state=state,
            detail=detail,
            profile=profile,
            available_profiles=self.available_profiles(name),
            profile_labels=(
                {"local": "RTL-SDR USB", "simulated": "Simulated"}
                if name == "openroadcode-sdrforge"
                else dict(self.PROFILE_LABELS)
                if self.available_profiles(name)
                else None
            ),
            input_state=input_state,
            input_detail=input_detail,
            readiness=readiness,
            readiness_detail=readiness_detail,
        )

    @staticmethod
    def _readiness(name: str, state: str, detail: str) -> tuple[str | None, str | None]:
        """Report SDRForge HTTP readiness without blocking service-manager requests.

        Preserve runit's process state for existing clients. An unreachable API
        is starting during its first ten seconds, then failed. A running
        process alone never counts as ready.
        """
        if name != "openroadcode-sdrforge":
            return None, None
        if state != "running":
            return (
                "stopped" if state == "stopped" else "unknown",
                "SDRForge service is not running",
            )
        try:
            with urlopen("http://127.0.0.1:5570/v1/health", timeout=0.3) as response:
                payload = json.load(response)
            if isinstance(payload, dict) and payload.get("status") == "ok":
                return "ready", "SDRForge REST API is healthy"
        except (OSError, ValueError):
            pass
        match = re.search(r"\(pid \d+\) (\d+)s", detail)
        uptime = int(match.group(1)) if match else None
        if uptime is not None and uptime >= 10:
            return "failed", "SDRForge REST API is not healthy after startup"
        return "starting", "Waiting for SDRForge REST API"

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
            # Match the SDRForge runit launcher default without changing other services.
            return "simulated" if name == "openroadcode-sdrforge" else "local"
        content = selected.read_text(encoding="utf-8")
        for profile in profiles:
            if f"OPENROADCODE_RUNTIME_PROFILE={profile}" in content:
                return profile
            if f'OPENROADCODE_RUNTIME_PROFILE="{profile}"' in content:
                return profile
        return "custom"

    @service_action(COMPONENT, "set_profile")
    def set_profile(self, name: str, profile: str) -> ServiceStatus:
        self._validate(name)
        profiles = self.PROFILE_CONFIGS.get(name)
        if not profiles:
            raise ValueError(f"Service does not support profiles: {name}")
        if profile not in profiles:
            raise ValueError(f"Unsupported profile for {name}: {profile}")
        if name == "openroadcode-sdrforge" and profile == "local":
            raise ValueError(
                "RTL-SDR requires Android-authorized USB handoff; "
                "direct runit startup is not supported yet"
            )

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

    @service_action(COMPONENT, "start")
    def start(self, name: str) -> ServiceStatus:
        self._validate(name)
        if name == "openroadcode-sdrforge" and self.profile(name) == "local":
            raise ValueError("RTL-SDR startup requires Android-authorized USB handoff")
        self._sv("up", name)
        return self.status(name)

    @service_action(COMPONENT, "stop")
    def stop(self, name: str) -> ServiceStatus:
        self._validate(name)
        self._sv("down", name)
        return self.status(name)

    @service_action(COMPONENT, "restart")
    def restart(self, name: str) -> ServiceStatus:
        self._validate(name)
        if name == "openroadcode-sdrforge" and self.profile(name) == "local":
            raise ValueError("RTL-SDR restart requires Android-authorized USB handoff")
        self._sv("restart", name)
        return self.status(name)

    @service_action(COMPONENT, "switch_sdrforge_source")
    def switch_sdrforge_source(self, source: str) -> dict[str, str]:
        """Switch server ownership; USB startup must be requested by Android."""
        if source not in {"simulated", "local"}:
            raise ValueError(f"Unsupported SDRForge source: {source}")
        name = "openroadcode-sdrforge"
        current = self._sdrforge_source()
        if source == "local":
            if current == "rtl_sdr":
                return {"source": "rtl_sdr", "state": "ready"}
            self._sv("down", name)
            self._wait_sdrforge_source(None)
            return {"source": "rtl_sdr", "state": "usb_handoff_required"}
        if current == "rtl_sdr":
            # Only the locally running hardware server is eligible for this
            # graceful shutdown. Never kill arbitrary PIDs or supervised servers.
            self._sv("down", name)
            request = Request(
                "http://127.0.0.1:5570/v1/server/shutdown",
                data=b"",
                method="POST",
            )
            with urlopen(authorize_local_sdrforge_request(request), timeout=3) as response:
                if response.status != 200:
                    raise RuntimeError("SDRForge hardware shutdown was rejected")
            self._wait_sdrforge_source(None)
        elif current not in (None, "simulated"):
            raise RuntimeError(f"Unrecognized SDRForge source: {current}")
        if current == "simulated":
            return {"source": "simulated", "state": "ready"}
        self.set_profile(name, "simulated")
        self._sv("up", name)
        self._wait_sdrforge_source("simulated")
        return {"source": "simulated", "state": "ready"}

    @staticmethod
    def _sdrforge_source() -> str | None:
        try:
            with urlopen("http://127.0.0.1:5570/v1/receiver", timeout=0.7) as response:
                source = json.load(response).get("source_type")
                if source not in ("simulated", "rtl_sdr"):
                    raise RuntimeError("SDRForge did not report a recognized source")
                return source
        except OSError:
            return None

    @staticmethod
    def _sdrforge_ports_free() -> bool:
        for port in (5570, 5571, 4532):
            try:
                with socket.socket() as probe:
                    probe.bind(("127.0.0.1", port))
            except OSError:
                return False
        return True

    @classmethod
    def _wait_sdrforge_source(cls, expected: str | None) -> None:
        for _ in range(40):
            if cls._sdrforge_source() == expected:
                if expected is not None or cls._sdrforge_ports_free():
                    return
            time.sleep(0.25)
        raise RuntimeError(f"SDRForge did not transition to {expected or 'stopped'}")

    @service_action(COMPONENT, "start_core")
    def start_core(self) -> tuple[ServiceStatus, ...]:
        for name in self.CORE_STACK:
            self._sv("up", name)
        return tuple(self.status(name) for name in self.CORE_STACK)

    @service_action(COMPONENT, "stop_core")
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
        service = name if name in RunitServiceManager.SERVICES else None
        return supervisor_command(
            COMPONENT,
            action,
            service,
            lambda: subprocess.run(
                ["sv", action, name],
                check=check,
                capture_output=True,
                text=True,
                timeout=5.0,
            ),
        )
