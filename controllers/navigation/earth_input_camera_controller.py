# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-local input controls for Google Earth."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthInputCameraController(EarthCameraControllerIf):
    """Drive Google Earth's camera through Chrome DevTools input events."""

    _PRESET_WHEEL_STEPS = {
        "street": (-480.0, -480.0),
        "city": (480.0, 480.0),
        "region": (480.0, 480.0, 480.0, 480.0),
    }

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    @property
    def name(self) -> str:
        return "INPUT"

    def available(self) -> bool:
        try:
            return self._client.earth_target() is not None
        except (OSError, RuntimeError, ValueError):
            return False

    def set_view(self, view: EarthCameraView) -> bool:
        del view
        return False

    def zoom_in(self) -> bool:
        return self._wheel(-480.0)

    def zoom_out(self) -> bool:
        return self._wheel(480.0)

    def north_up(self) -> bool:
        return self._key("n", "KeyN", 78)

    def pan(self, *, up: float = 0.0, right: float = 0.0) -> bool:
        """Pan Earth with its normal arrow-key camera controls."""
        key = None
        if abs(up) >= abs(right) and up != 0.0:
            key = ("ArrowUp", "ArrowUp", 38) if up > 0 else ("ArrowDown", "ArrowDown", 40)
        elif right != 0.0:
            key = ("ArrowRight", "ArrowRight", 39) if right > 0 else ("ArrowLeft", "ArrowLeft", 37)
        if key is None:
            return True
        return self._key(*key, printable=False)

    def tilt(self, delta_deg: float) -> bool:
        """Tilt Earth using PageUp/PageDown camera shortcuts."""
        if delta_deg == 0.0:
            return True
        if delta_deg > 0.0:
            return self._key("PageUp", "PageUp", 33, printable=False)
        return self._key("PageDown", "PageDown", 34, printable=False)

    def apply_preset(self, name: str) -> bool:
        """Apply a coarse driving-scale view preset relative to the current view."""
        steps = self._PRESET_WHEEL_STEPS.get(name.casefold())
        if steps is None:
            raise ValueError(f"unsupported Earth view preset: {name}")
        return all(self._wheel(delta) for delta in steps)

    def _wheel(self, delta_y: float) -> bool:
        try:
            self._client.activate(self._require_target_id())
            viewport = self._client.evaluate_earth(
                "({width: Math.max(1, window.innerWidth), height: Math.max(1, window.innerHeight)})"
            )
            value = viewport.get("result", {}).get("result", {}).get("value", {})
            width = float(value.get("width", 800))
            height = float(value.get("height", 500))
            self._client.command_earth(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": width / 2.0,
                    "y": height / 2.0,
                    "deltaX": 0.0,
                    "deltaY": delta_y,
                },
            )
            return True
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def _key(
        self,
        key: str,
        code: str,
        virtual_key: int,
        *,
        printable: bool = True,
    ) -> bool:
        try:
            self._client.activate(self._require_target_id())
            common = {
                "key": key,
                "code": code,
                "windowsVirtualKeyCode": virtual_key,
                "nativeVirtualKeyCode": virtual_key,
            }
            self._client.command_earth("Input.dispatchKeyEvent", {"type": "rawKeyDown", **common})
            if printable:
                self._client.command_earth(
                    "Input.dispatchKeyEvent",
                    {"type": "char", "text": key, "unmodifiedText": key, **common},
                )
            self._client.command_earth("Input.dispatchKeyEvent", {"type": "keyUp", **common})
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _require_target_id(self) -> str:
        target = self._client.earth_target()
        if target is None:
            raise RuntimeError("Google Earth DevTools target is not available")
        return target.id
