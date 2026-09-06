# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-local input controls for Google Earth."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthInputCameraController(EarthCameraControllerIf):
    """Drive Google Earth's camera through Chrome DevTools input events."""

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
        # Absolute Earth camera control remains deliberately separate from
        # browser input. Position/follow is supplied by EarthGeolocationBridge.
        del view
        return False

    def zoom_in(self) -> bool:
        return self._wheel(-480.0)

    def zoom_out(self) -> bool:
        return self._wheel(480.0)

    def north_up(self) -> bool:
        return self._key("n", "KeyN", 78)

    def _wheel(self, delta_y: float) -> bool:
        """Zoom at the center of the Earth viewport using a browser wheel event."""
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

    def _key(self, key: str, code: str, virtual_key: int) -> bool:
        """Send the same key sequence Chrome generates for a printable shortcut."""
        try:
            self._client.activate(self._require_target_id())
            common = {
                "key": key,
                "code": code,
                "windowsVirtualKeyCode": virtual_key,
                "nativeVirtualKeyCode": virtual_key,
            }
            self._client.command_earth(
                "Input.dispatchKeyEvent",
                {"type": "rawKeyDown", **common},
            )
            self._client.command_earth(
                "Input.dispatchKeyEvent",
                {"type": "char", "text": key, "unmodifiedText": key, **common},
            )
            self._client.command_earth(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", **common},
            )
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _require_target_id(self) -> str:
        target = self._client.earth_target()
        if target is None:
            raise RuntimeError("Google Earth DevTools target is not available")
        return target.id
