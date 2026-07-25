import tkinter as tk

from apps.common.instruments.gauge_config  import GaugeConfig
from apps.common.instruments.gauge_style   import GaugeStyle
from apps.common.instruments.instrument_panel import InstrumentPanel
from controllers.automotive import VehicleState


class AutomotiveDashboardWindow(tk.Frame):
    """Display vehicle telemetry as a grid of instrument gauges."""
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

        self._panel = InstrumentPanel(self, gauges=gauges, columns=3, style=self._style)
        self._panel.pack(fill=tk.BOTH, expand=True)

    def update_vehicle_state(self, state: VehicleState) -> None:
        """Render values from the latest vehicle-state snapshot."""
        self._panel.set_values(
            {
                "boost": state.boost_psi,
                "rpm": state.rpm / 1000.0 if state.rpm is not None else None,
                "speed": state.speed_mph,
                "coolant": state.coolant_temp_f,
                "throttle": state.throttle_pct,
                "voltage": state.control_voltage,
            }
        )
