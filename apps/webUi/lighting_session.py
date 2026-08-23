# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from threading import RLock

from apps.common.lighting_runtime_factory import create_lighting_controller
from common.color import hex_to_rgb, rgb_to_hex
from controllers.lighting import DummyLightingController, LightingControllerIf


class WebLightingSession:
    """Own WebUi lighting state and explicit emulator/physical binding."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._lock = RLock()
        self._backend_name = "emulator"
        self._controller: LightingControllerIf = DummyLightingController()
        self._controller.connect().result()

    @property
    def controller(self) -> LightingControllerIf:
        """Current bound controller; callers must re-read after a backend bind."""
        with self._lock:
            return self._controller

    def state(self) -> dict[str, object]:
        with self._lock:
            state = self._controller.current_state()
            return {
                "backend": self._backend_name,
                "connected": state.connected,
                "connection_status": state.connection_status.value,
                "device_address": state.device_address,
                "last_connection_error": state.last_connection_error,
                "power_enabled": state.power_enabled,
                "color": rgb_to_hex(state.color),
                "brightness_percent": state.brightness_percent,
            }

    def bind(self, backend: str) -> dict[str, object]:
        normalized = backend.strip().lower()
        if normalized not in {"emulator", "ble"}:
            raise ValueError("backend must be 'emulator' or 'ble'")
        with self._lock:
            previous = self._controller
            controller: LightingControllerIf = DummyLightingController() if normalized == "emulator" else create_lighting_controller(project_root=self._project_root, backend="leddmx")
            controller.connect().result()
            self._controller = controller
            self._backend_name = normalized
            try: previous.close()
            except Exception: pass
        return self.state()

    def command(self, command: str, value: object = None) -> dict[str, object]:
        normalized = command.strip().lower()
        with self._lock:
            if normalized == "power": self._controller.set_power(bool(value)).result()
            elif normalized == "color": self._controller.set_color(hex_to_rgb(str(value))).result()
            elif normalized == "brightness": self._controller.set_brightness(int(value)).result()
            else: raise ValueError(f"Unknown lighting command: {command}")
        return self.state()
