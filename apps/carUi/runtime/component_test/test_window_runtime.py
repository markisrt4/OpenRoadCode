"""Tests for Tk window-mode configuration."""

from __future__ import annotations

import unittest
from collections.abc import Callable

from apps.carUi.runtime.window_runtime import apply_fullscreen


class FakeWindow:
    def __init__(self) -> None:
        self.geometries: list[str] = []
        self.attribute_values: list[tuple[str, object]] = []
        self.idle_callbacks: list[Callable[[], None]] = []
        self.updated = False

    def after_idle(self, callback: Callable[[], None]) -> object:
        self.idle_callbacks.append(callback)
        return "callback-id"

    def attributes(self, option: str, value: object) -> object:
        self.attribute_values.append((option, value))
        return ""

    def geometry(self, geometry: str) -> object:
        self.geometries.append(geometry)
        return ""

    def update_idletasks(self) -> None:
        self.updated = True

    def winfo_screenheight(self) -> int:
        return 600

    def winfo_screenwidth(self) -> int:
        return 1024


class WindowRuntimeTests(unittest.TestCase):
    def test_applies_geometry_and_fullscreen_immediately(self) -> None:
        window = FakeWindow()

        apply_fullscreen(window)  # type: ignore[arg-type]

        self.assertTrue(window.updated)
        self.assertEqual(window.geometries, ["1024x600+0+0"])
        self.assertEqual(
            window.attribute_values,
            [("-fullscreen", True)],
        )

    def test_reasserts_fullscreen_after_window_maps(self) -> None:
        window = FakeWindow()
        apply_fullscreen(window)  # type: ignore[arg-type]

        callback = window.idle_callbacks[0]
        callback()

        self.assertEqual(
            window.geometries,
            ["1024x600+0+0", "1024x600+0+0"],
        )
        self.assertEqual(
            window.attribute_values,
            [("-fullscreen", True), ("-fullscreen", True)],
        )


if __name__ == "__main__":
    unittest.main()
