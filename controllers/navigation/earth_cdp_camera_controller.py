# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Preferred Google Earth camera controller using Chromium DevTools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


@dataclass(frozen=True)
class EarthRuntimeProbe:
    """Harmless page-level facts used to verify the Earth CDP connection."""

    title: str
    url: str
    ready_state: str
    canvas_count: int
    custom_element_names: tuple[str, ...]


class EarthCdpCameraController(EarthCameraControllerIf):
    """Own the stable CDP boundary while Earth camera control is investigated."""

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    @property
    def name(self) -> str:
        return "CDP"

    def available(self) -> bool:
        try:
            return self._client.earth_target() is not None
        except (OSError, ValueError):
            return False

    def probe_runtime(self) -> EarthRuntimeProbe:
        """Prove Runtime.evaluate works without changing Google Earth state."""
        value = self._client.evaluate_earth(
            """(() => ({
                title: document.title,
                url: location.href,
                readyState: document.readyState,
                canvasCount: document.querySelectorAll('canvas').length,
                customElementNames: [...document.querySelectorAll('*')]
                    .map(element => element.localName)
                    .filter(name => name && name.includes('-'))
                    .filter((name, index, values) => values.indexOf(name) === index)
                    .sort()
                    .slice(0, 100)
            }))()"""
        )
        if not isinstance(value, dict):
            raise RuntimeError("Google Earth runtime probe returned an unexpected value")
        names = value.get("customElementNames")
        if not isinstance(names, list):
            names = []
        return EarthRuntimeProbe(
            title=str(value.get("title", "")),
            url=str(value.get("url", "")),
            ready_state=str(value.get("readyState", "")),
            canvas_count=int(value.get("canvasCount", 0)),
            custom_element_names=tuple(str(name) for name in names),
        )

    def inspect_globals(self, *, keywords: tuple[str, ...] = ("earth", "camera", "map", "scene", "view")) -> tuple[str, ...]:
        """Return matching top-level global names without invoking Earth internals."""
        encoded_keywords = repr([keyword.lower() for keyword in keywords])
        expression = (
            "(() => { const needles = "
            + encoded_keywords
            + "; return Object.getOwnPropertyNames(window)"
            ".filter(name => needles.some(needle => name.toLowerCase().includes(needle)))"
            ".sort().slice(0, 200); })()"
        )
        value: Any = self._client.evaluate_earth(expression)
        if not isinstance(value, list):
            return ()
        return tuple(str(name) for name in value)

    def set_view(self, view: EarthCameraView) -> bool:
        # Deliberately do not depend on undocumented Earth internals yet.
        # Runtime.evaluate is now available, but camera mutation stays disabled
        # until the runtime probe identifies a mechanism worth isolating here.
        del view
        return False
