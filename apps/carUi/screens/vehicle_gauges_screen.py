# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI destination hosting the reusable vehicle gauges."""

from __future__ import annotations

from pathlib import Path

from frontends.tk.automotive import VehicleGaugePanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from messaging.contracts.automotive import VehicleStateMessage
from ui.automotive import VehicleConnectionState
from ui.screen_ui_if import ScreenId

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory


DEFAULT_LAYOUT_PATH = Path.home() / ".config/openroadcode/vehicle_gauges.json"


class VehicleGaugesScreen(CarUiScreen):
    """Display the latest vehicle-state contract delivered by the message bus."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        create_menu_tile: MenuTileFactory,
        back_action,
        config_path: str | Path = DEFAULT_LAYOUT_PATH,
    ) -> None:
        super().__init__(host, ScreenId("vehicle_gauges"), create_menu_tile)
        self._back_action = back_action
        self._config_path = config_path
        self._panel: VehicleGaugePanel | None = None
        self._latest_message: VehicleStateMessage | None = None
        self._received_count = 0

    def show(self) -> None:
        """Build the gauge panel and render the latest bus state, if available."""
        self.prepare_screen("Vehicle Gauges", self._back_action)
        self._panel = VehicleGaugePanel(
            self.content_frame,
            config_path=self._config_path,
            columns=4,
        )
        self._panel.pack(fill="both", expand=True)
        self._render_latest()

    def hide(self) -> None:
        """Release references to widgets destroyed by screen navigation."""
        self._panel = None

    def set_vehicle_message(self, message: VehicleStateMessage) -> None:
        """Accept one decoded vehicle-state message on the Tk UI thread."""
        self._latest_message = message
        self._received_count += 1
        self._render_latest()

    def set_vehicle_error(self, topic: str, error: Exception) -> None:
        """Expose a vehicle message decode/dispatch failure when visible."""
        if self._panel is not None:
            self._panel.set_connection_state(VehicleConnectionState.ERROR)
            self.set_status(
                f"Vehicle telemetry error: {type(error).__name__}"
            )

    def _render_latest(self) -> None:
        panel = self._panel
        if panel is None:
            return

        message = self._latest_message
        if message is None:
            panel.set_connection_state(VehicleConnectionState.DISCONNECTED)
            self.set_status("Waiting for vehicle telemetry")
            return

        data = message.data
        panel.set_connection_state(VehicleConnectionState.CONNECTED)
        panel.set_engine_speed(data.engine_speed_rad_s)
        panel.set_vehicle_speed(data.vehicle_speed_m_s)
        panel.set_throttle_position(data.throttle_position)
        panel.set_accelerator_position(data.accelerator_pedal_position)
        panel.set_engine_load(data.engine_load)
        panel.set_manifold_pressure(data.intake_manifold_pressure_pa)
        panel.set_barometric_pressure(data.barometric_pressure_pa)
        panel.set_boost_pressure(data.boost_pressure_pa)
        panel.set_mass_air_flow(data.mass_air_flow_kg_s)
        panel.set_coolant_temperature(data.coolant_temperature_k)
        panel.set_intake_air_temperature(data.intake_air_temperature_k)
        panel.set_fuel_level(data.fuel_level)
        panel.set_control_voltage(data.control_voltage_v)
        self.set_status(
            f"Vehicle telemetry: {message.source} · {self._received_count} messages"
        )
