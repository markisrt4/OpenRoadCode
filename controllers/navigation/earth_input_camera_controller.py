# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-local input controls for Google Earth."""

from __future__ import annotations

from typing import Any

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthInputCameraController(EarthCameraControllerIf):
    """Drive Google Earth's camera through Chrome DevTools input events."""

    _PRESET_WHEEL_STEPS = {
        "street": (-480.0, -480.0),
        "city": (480.0, 480.0),
        "region": (480.0, 480.0, 480.0, 480.0),
    }
    _PAN_BASE_REPEATS = 15
    _PAN_MIN_REPEATS = 6
    _PAN_MAX_REPEATS = 40
    _TILT_VIEWPORT_FRACTION = 0.05
    _ROTATE_VIEWPORT_FRACTION_PER_45_DEG = 0.12
    _CHASE_ZOOM_STEPS = 12
    _CHASE_ZOOM_FOCUS_Y = 0.36
    _LOCATION_RIGHT_MARGIN_PX = 34.0
    _LOCATION_BOTTOM_MARGIN_PX = 34.0
    _LOCATION_NAME_TOKENS = (
        "my location",
        "your location",
        "current location",
        "locate me",
        "location",
    )

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)
        self._zoom_bias = 0

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
        ok = self._wheel(-480.0)
        if ok:
            self._zoom_bias = min(8, self._zoom_bias + 1)
        return ok

    def zoom_out(self) -> bool:
        ok = self._wheel(480.0)
        if ok:
            self._zoom_bias = max(-8, self._zoom_bias - 1)
        return ok

    def zoom_closest(self) -> bool:
        """Drive Earth toward its closest useful zoom level."""
        ok = all(
            self._wheel(-600.0, y_fraction=self._CHASE_ZOOM_FOCUS_Y)
            for _ in range(self._CHASE_ZOOM_STEPS)
        )
        if ok:
            self._zoom_bias = 8
        return ok

    def north_up(self) -> bool:
        return self._key("n", "KeyN", 78)

    def top_down(self) -> bool:
        """Reset Earth to a zero-pitch top-down view."""
        return self._key("u", "KeyU", 85)

    def toggle_menu_bar(self) -> bool:
        """Toggle Google Earth's menu bar using its Ctrl+Shift+B shortcut."""
        return self._key("B", "KeyB", 66, printable=False, modifiers=10)

    def activate_location_tracking(self) -> bool:
        """Activate Earth's location tool, preferring semantic discovery over coordinates."""
        try:
            self._client.activate(self._require_target_id())

            # Google Earth Web moves controls as toolbars/layout change.  A
            # fixed bottom-right coordinate was therefore a particularly
            # optimistic way to find Locate Me.  Prefer the accessibility tree
            # and only keep the old coordinate as a final compatibility fallback.
            point = self._location_control_point()
            if point is not None:
                return self._click(*point)

            width, height = self._viewport_size()
            return self._click(
                max(1.0, width - self._LOCATION_RIGHT_MARGIN_PX),
                max(1.0, height - self._LOCATION_BOTTOM_MARGIN_PX),
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def location_control_diagnostics(self) -> tuple[str, ...]:
        """Return compact accessibility candidates useful when Locate Me cannot be found."""
        try:
            self._client.command_earth("Accessibility.enable")
            tree = self._client.command_earth("Accessibility.getFullAXTree")
        except (OSError, RuntimeError, TypeError, ValueError):
            return ()

        candidates: list[str] = []
        for node in tree.get("nodes", []):
            if not isinstance(node, dict):
                continue
            name = self._ax_value(node.get("name"))
            role = self._ax_value(node.get("role"))
            if not name:
                continue
            lowered = name.casefold()
            if any(token in lowered for token in self._LOCATION_NAME_TOKENS):
                candidates.append(f"{role or '?'}: {name}")
        return tuple(candidates[:12])

    def pan(self, *, up: float = 0.0, right: float = 0.0) -> bool:
        """Pan using Earth arrow controls with zoom-relative travel."""
        key = None
        if abs(up) >= abs(right) and up != 0.0:
            key = ("ArrowUp", "ArrowUp", 38) if up > 0 else ("ArrowDown", "ArrowDown", 40)
        elif right != 0.0:
            key = ("ArrowRight", "ArrowRight", 39) if right > 0 else ("ArrowLeft", "ArrowLeft", 37)
        if key is None:
            return True
        scale = 1.35 ** self._zoom_bias
        repeats = round(self._PAN_BASE_REPEATS * scale)
        repeats = max(self._PAN_MIN_REPEATS, min(self._PAN_MAX_REPEATS, repeats))
        return all(self._key(*key, printable=False) for _ in range(repeats))

    def tilt(self, delta_deg: float) -> bool:
        """Tilt with a small Shift+left-drag step."""
        if delta_deg == 0.0:
            return True
        try:
            _, height = self._viewport_size()
            magnitude = max(0.5, min(2.0, abs(delta_deg) / 5.0))
            dy = height * self._TILT_VIEWPORT_FRACTION * magnitude
            if delta_deg < 0.0:
                dy = -dy
            return self._drag(dx=0.0, dy=dy, modifiers=8)
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def rotate(self, delta_deg: float) -> bool:
        """Rotate Earth heading with a horizontal Shift+left-drag."""
        if abs(delta_deg) < 0.1:
            return True
        try:
            width, _ = self._viewport_size()
            bounded = max(-90.0, min(90.0, delta_deg))
            dx = width * self._ROTATE_VIEWPORT_FRACTION_PER_45_DEG * (bounded / 45.0)
            return self._drag(dx=dx, dy=0.0, modifiers=8)
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def apply_preset(self, name: str) -> bool:
        """Apply a coarse driving-scale view preset relative to the current view."""
        steps = self._PRESET_WHEEL_STEPS.get(name.casefold())
        if steps is None:
            raise ValueError(f"unsupported Earth view preset: {name}")
        return all(self._wheel(delta) for delta in steps)

    def _location_control_point(self) -> tuple[float, float] | None:
        """Resolve a location-like accessibility node to viewport coordinates."""
        self._client.command_earth("Accessibility.enable")
        tree = self._client.command_earth("Accessibility.getFullAXTree")
        ranked: list[tuple[int, dict[str, Any]]] = []

        for node in tree.get("nodes", []):
            if not isinstance(node, dict):
                continue
            backend_id = node.get("backendDOMNodeId")
            if not isinstance(backend_id, int):
                continue
            name = self._ax_value(node.get("name"))
            if not name:
                continue
            lowered = name.casefold()
            score = next(
                (len(self._LOCATION_NAME_TOKENS) - i for i, token in enumerate(self._LOCATION_NAME_TOKENS) if token in lowered),
                0,
            )
            if score:
                ranked.append((score, node))

        ranked.sort(key=lambda item: item[0], reverse=True)
        for _, node in ranked:
            backend_id = int(node["backendDOMNodeId"])
            try:
                model = self._client.command_earth(
                    "DOM.getBoxModel", {"backendNodeId": backend_id}
                ).get("model")
            except RuntimeError:
                continue
            if not isinstance(model, dict):
                continue
            quad = model.get("border") or model.get("content")
            if not isinstance(quad, list) or len(quad) < 8:
                continue
            xs = [float(quad[i]) for i in range(0, 8, 2)]
            ys = [float(quad[i]) for i in range(1, 8, 2)]
            return sum(xs) / len(xs), sum(ys) / len(ys)
        return None

    @staticmethod
    def _ax_value(value: Any) -> str:
        if isinstance(value, dict):
            raw = value.get("value")
            return "" if raw is None else str(raw)
        return "" if value is None else str(value)

    def _click(self, x: float, y: float) -> bool:
        self._client.command_earth(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "buttons": 1, "clickCount": 1},
        )
        self._client.command_earth(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "x": x, "y": y, "button": "left", "buttons": 0, "clickCount": 1},
        )
        return True

    def _viewport_size(self) -> tuple[float, float]:
        self._client.activate(self._require_target_id())
        viewport = self._client.evaluate_earth(
            "({width: Math.max(1, window.innerWidth), height: Math.max(1, window.innerHeight)})"
        )
        if isinstance(viewport, dict):
            return float(viewport.get("width", 800)), float(viewport.get("height", 500))
        return 800.0, 500.0

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
            {"type": "mouseReleased", "x": end_x, "y": end_y, "button": "left", "buttons": 0, "modifiers": modifiers, "clickCount": 1},
        )
        return True

    def _wheel(self, delta_y: float, *, y_fraction: float = 0.5) -> bool:
        try:
            self._client.activate(self._require_target_id())
            width, height = self._viewport_size()
            y_fraction = max(0.05, min(0.95, y_fraction))
            self._client.command_earth(
                "Input.dispatchMouseEvent",
                {"type": "mouseWheel", "x": width / 2.0, "y": height * y_fraction, "deltaX": 0.0, "deltaY": delta_y},
            )
            return True
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

    def _key(self, key: str, code: str, virtual_key: int, *, printable: bool = True, modifiers: int = 0) -> bool:
        try:
            self._client.activate(self._require_target_id())
            common = {"key": key, "code": code, "windowsVirtualKeyCode": virtual_key, "nativeVirtualKeyCode": virtual_key, "modifiers": modifiers}
            self._client.command_earth("Input.dispatchKeyEvent", {"type": "rawKeyDown", **common})
            if printable:
                self._client.command_earth("Input.dispatchKeyEvent", {"type": "char", "text": key, "unmodifiedText": key, **common})
            self._client.command_earth("Input.dispatchKeyEvent", {"type": "keyUp", **common})
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _require_target_id(self) -> str:
        target = self._client.earth_target()
        if target is None:
            raise RuntimeError("Google Earth DevTools target is not available")
        return target.id
