# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for configurable vehicle-gauge redline presentation."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from apps.common.uiTheme import (
    VEHICLE_GAUGE_REDLINE_THEME,
    VEHICLE_GAUGE_THEME,
    VehicleGaugeRedlineTheme,
)
from frontends.tk.automotive.vehicle_gauge_panel import DEFAULT_GAUGES
from frontends.tk.automotive.vehicle_gauge_panel import VehicleGaugePanel
from ui.automotive import (
    VehicleConnectionUiIf,
    VehicleDiagnosticsUiIf,
    VehicleTireUiIf,
    VehicleTripUiIf,
    VehicleUiIf,
)


class VehicleGaugeRedlineThemeTest(unittest.TestCase):
    def test_default_themes_live_in_common_ui_theme(self) -> None:
        self.assertEqual(VEHICLE_GAUGE_THEME.background_color, "#090a0b")
        self.assertEqual(VEHICLE_GAUGE_REDLINE_THEME.danger_color, "#e10d1c")

    def test_primary_gauges_opt_into_intense_redlines(self) -> None:
        definitions = {item.gauge_id: item for item in DEFAULT_GAUGES}

        for gauge_id in ("rpm", "boost", "speed"):
            self.assertTrue(definitions[gauge_id].intense_redline)
            self.assertIsNotNone(definitions[gauge_id].danger_high)

    def test_rejects_nonpositive_geometry_scale(self) -> None:
        with self.assertRaisesRegex(ValueError, "scales must be positive"):
            VehicleGaugeRedlineTheme(highlight_width_scale=0.0)

    def test_panel_implements_only_its_displayed_automotive_contracts(self) -> None:
        for contract in (
            VehicleUiIf,
            VehicleConnectionUiIf,
            VehicleTripUiIf,
            VehicleTireUiIf,
            VehicleDiagnosticsUiIf,
        ):
            self.assertTrue(issubclass(VehicleGaugePanel, contract))
        self.assertFalse(VehicleGaugePanel.__abstractmethods__)

    def test_contract_setters_convert_si_values_at_frontend_boundary(self) -> None:
        panel = VehicleGaugePanel.__new__(VehicleGaugePanel)
        recorder = Mock()
        panel._set_contract_value = recorder  # type: ignore[method-assign]

        panel.set_vehicle_speed(10.0)
        recorder.assert_called_with("speed_mph", 22.369362920544)

        panel.set_boost_pressure(6894.757293168)
        recorder.assert_called_with("boost_psi", 1.0)

        panel.set_coolant_temperature(273.15)
        recorder.assert_called_with("coolant_temp_f", 32.0)

    def test_frontend_contains_no_embedded_palette_or_font_family(self) -> None:
        package = Path(__file__).resolve().parents[1]
        source = "\n".join(
            (package / name).read_text(encoding="utf-8")
            for name in ("vehicle_gauge_panel.py", "vehicle_gauge_widgets.py")
        )

        self.assertNotRegex(source, r"#[0-9a-fA-F]{6}")
        self.assertNotIn("DejaVu", source)


if __name__ == "__main__":
    unittest.main()
