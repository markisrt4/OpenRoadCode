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
    _PAN_VIEWPORT_FRACTION = 0.24
    _TILT_VIEWPORT_FRACTION = 0.22

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
        """Pan by a fixed fraction of the visible viewport.

        Because the gesture is specified in screen space, the ground distance
        naturally scales with the current Earth zoom level.
        """
        if up == 0.0 and right == 0.0:
            return True
        try:
            width, height = self._viewport_size()
            dx = -right * width * self._PAN_VIEWPORT_FRACTION
            dy = up * height * self._PAN_VIEWPORT_FRACTION
            return self._drag(dx=dx, dy=dy)
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def tilt(self, delta_deg: float) -> bool:
        """Tilt with Google's documented Shift+left-drag gesture."""
        if delta_deg == 0.0:
            return True
        try:
            _, height = self._viewport_size()
            dy = height * self._TILT_VIEWPORT_FRACTION
            if delta_deg < 0.0:
                dy = -dy
            return self._drag(dx=0.0, dy=dy, modifiers=8)
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def apply_preset(self, name: str) -> bool:
        """Apply a coarse driving-scale view preset relative to the current view."""
        steps = self._PRESET_WHEEL_STEPS.get(name.casefold())
        if steps is None:
            raise ValueError(f"unsupported Earth view preset: {name}")
        return all(self._wheel(delta) for delta in steps)

    def _viewport_size(self) -> tuple[float, float]:
        self._client.activate(self._require_target_id())
        viewport = self._client.evaluate_earth(
            "({width: Math.max(1, window.innerWidth), height: Math.max(1, window.innerHeight)})"
        )
        value = viewport.get("result", {}).get("result", {}).get("value", {})
        return float(value.get("width", 800)), float(value.get("height", 500))

    def _drag(self, *, dx: float, dy: float, modifiers: int = 0) -> bool:
        self._client.activate(self._require_target_id())
        width, height = self._viewport_size()
        start_x = width / 2.0
        start_y = height / 2.0
        end_x = max(1.0, min(width - 1.0, start_x + dx))
        end_y = max(1.0, min(height - 1.0, start_y + dy))
        common = {"button": "left", "buttons": 1, "modifiers": modifiers}
        self._client.command_earth(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": start_x, "y": start_y, "clickCount": 1, **common},
        )
        self._client.command_earth(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": end_x, "y": end_y, **common},
        )
        self._client.command_earth(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": end_x,
                "y": end_y,
                "button": "left",
                "buttons": 0,
                "modifiers": modifiers,
                "clickCount": 1,
            },
        )
        return True

    def _wheel(self, delta_y: float) -> bool:
        try:
            self._client.activate(self._require_target_id())
            width, height = self._viewport_size()
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
        modifiers: int = 0,
    ) -> bool:
        try:
            self._client.activate(self._require_target_id())
            common = {
                "key": key,
                "code": code,
                "windowsVirtualKeyCode": virtual_key,
                "nativeVirtualKeyCode": virtual_key,
                "modifiers": modifiers,
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
