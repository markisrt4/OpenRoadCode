# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-local input controls for Google Earth."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthInputCameraController(EarthCameraControllerIf):
    """Drive Google Earth's normal camera shortcuts through Chrome DevTools input."""

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
        return self._key("+")

    def zoom_out(self) -> bool:
        return self._key("-")

    def north_up(self) -> bool:
        return self._key("n")

    def _key(self, key: str) -> bool:
        """Send a real browser key press to the Earth page via CDP."""
        try:
            self._client.activate(self._require_target_id())
            params = self._key_params(key)
            self._client.command_earth("Input.dispatchKeyEvent", {"type": "keyDown", **params})
            self._client.command_earth("Input.dispatchKeyEvent", {"type": "keyUp", **params})
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _require_target_id(self) -> str:
        target = self._client.earth_target()
        if target is None:
            raise RuntimeError("Google Earth DevTools target is not available")
        return target.id

    @staticmethod
    def _key_params(key: str) -> dict[str, object]:
        if key == "+":
            return {
                "key": "+",
                "code": "Equal",
                "windowsVirtualKeyCode": 187,
                "nativeVirtualKeyCode": 187,
                "text": "+",
                "unmodifiedText": "+",
                "modifiers": 8,
            }
        if key == "-":
            return {
                "key": "-",
                "code": "Minus",
                "windowsVirtualKeyCode": 189,
                "nativeVirtualKeyCode": 189,
                "text": "-",
                "unmodifiedText": "-",
            }
        if key == "n":
            return {
                "key": "n",
                "code": "KeyN",
                "windowsVirtualKeyCode": 78,
                "nativeVirtualKeyCode": 78,
                "text": "n",
                "unmodifiedText": "n",
            }
        raise ValueError(f"unsupported Earth key: {key}")
