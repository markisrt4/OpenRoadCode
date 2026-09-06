# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for external-application graphics runtime selection."""

import unittest

from apps.launchers.graphics_environment import (
    GraphicsRuntime,
    detect_graphics_runtime,
    graphics_environment,
)


class GraphicsEnvironmentTest(unittest.TestCase):
    def test_non_termux_platform_uses_system_environment(self) -> None:
        runtime = detect_graphics_runtime(environment={"PREFIX": "/usr"})

        self.assertEqual(runtime.backend, "system")
        self.assertFalse(runtime.hardware_accelerated)
        self.assertEqual(runtime.environment, {})

    def test_termux_qualcomm_with_freedreno_selects_zink(self) -> None:
        runtime = detect_graphics_runtime(
            environment={"PREFIX": "/data/data/com.termux/files/usr"},
            hardware="qcom",
            platform="canoe",
            kgsl_present=True,
            freedreno_icd_present=True,
        )

        self.assertEqual(runtime.backend, "freedreno-zink")
        self.assertTrue(runtime.hardware_accelerated)
        self.assertEqual(runtime.environment, {"MESA_LOADER_DRIVER_OVERRIDE": "zink"})

    def test_unknown_termux_gpu_does_not_force_vendor_driver(self) -> None:
        runtime = detect_graphics_runtime(
            environment={"PREFIX": "/data/data/com.termux/files/usr"},
            hardware="unknown",
            platform="unknown",
            kgsl_present=False,
            freedreno_icd_present=False,
        )

        self.assertEqual(runtime.backend, "generic")
        self.assertFalse(runtime.hardware_accelerated)
        self.assertEqual(runtime.environment, {})

    def test_graphics_environment_preserves_existing_values(self) -> None:
        base = {"DISPLAY": ":1", "EXAMPLE": "value"}
        runtime = GraphicsRuntime(
            backend="freedreno-zink",
            hardware_accelerated=True,
            environment={"MESA_LOADER_DRIVER_OVERRIDE": "zink"},
        )

        result = graphics_environment(base, runtime=runtime)

        self.assertEqual(result["DISPLAY"], ":1")
        self.assertEqual(result["EXAMPLE"], "value")
        self.assertEqual(result["MESA_LOADER_DRIVER_OVERRIDE"], "zink")
        self.assertNotIn("MESA_LOADER_DRIVER_OVERRIDE", base)


if __name__ == "__main__":
    unittest.main()
