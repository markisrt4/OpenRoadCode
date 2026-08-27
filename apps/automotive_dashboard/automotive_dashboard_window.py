# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import tkinter as tk

from apps.common.instruments.gauge_config import GaugeConfig
from apps.common.instruments.gauge_style import GaugeStyle
from apps.common.instruments.instrument_panel import InstrumentPanel
from messaging.contracts.automotive import VehicleStateData


RPM_PER_RAD_S = 60.0 / (2.0 * math.pi)
MPH_PER_MPS = 2.2369362920544
PSI_PER_PA = 0.00014503773773020923


class AutomotiveDashboardWindow(tk.Frame):
    """Display SI-normalized vehicle telemetry as presentation-unit gauges."""

    def __init__(self, parent) -> None:
        self._style = GaugeStyle()
        super().__init__(parent, bg=self._style.background)

        gauges = {
            "boost": GaugeConfig("BOOST", "psi", -15.0, 25.0),
            "rpm": GaugeConfig("RPM", "x1000", 0.0, 7.0),
            "speed": GaugeConfig("SPEED", "mph", 0.0, 120.0),
            "coolant": GaugeConfig("COOLANT", "°F", 100.0, 240.0),
            "throttle": GaugeConfig("THROTTLE", "%", 0.0, 100.0),
            "voltage": GaugeConfig("VOLTAGE", "V", 11.0, 15.0, precision=2),
        }

        self._panel = InstrumentPanel(
            self,
            gauges=gauges,
            columns=3,
            style=self._style,
        )
        self._panel.pack(fill=tk.BOTH, expand=True)

    def update_vehicle_state(self, state: VehicleStateData) -> None:
        """Render SI contract data using dashboard presentation units."""
        self._panel.set_values(
            {
                "boost": (
                    None
                    if state.boost_pressure_pa is None
                    else state.boost_pressure_pa * PSI_PER_PA
                ),
                "rpm": (
                    None
                    if state.engine_speed_rad_s is None
                    else state.engine_speed_rad_s * RPM_PER_RAD_S / 1000.0
                ),
                "speed": (
                    None
                    if state.vehicle_speed_m_s is None
                    else state.vehicle_speed_m_s * MPH_PER_MPS
                ),
                "coolant": (
                    None
                    if state.coolant_temperature_k is None
                    else (state.coolant_temperature_k - 273.15) * 9.0 / 5.0 + 32.0
                ),
                "throttle": (
                    None
                    if state.throttle_position is None
                    else state.throttle_position * 100.0
                ),
                "voltage": state.control_voltage_v,
            }
        )
