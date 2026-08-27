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
from apps.carUi.vehicle_gauge_presenter import VehicleGaugePresenter


DEFAULT_LAYOUT_PATH = Path.home() / ".config/openroadcode/vehicle_gauges.json"


class VehicleGaugesScreen(CarUiScreen):
    """Render headless vehicle-gauge application state with Tk widgets."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        create_menu_tile: MenuTileFactory,
        back_action,
        config_path: str | Path = DEFAULT_LAYOUT_PATH,
        presenter: VehicleGaugePresenter | None = None,
    ) -> None:
        super().__init__(host, ScreenId("vehicle_gauges"), create_menu_tile)
        self._back_action = back_action
        self._config_path = config_path
        self._presenter = presenter or VehicleGaugePresenter()
        self._panel: VehicleGaugePanel | None = None

    def show(self) -> None:
        self.prepare_screen("Vehicle Gauges", self._back_action)
        self._panel = VehicleGaugePanel(
            self.content_frame,
            config_path=self._config_path,
            columns=4,
        )
        self._panel.pack(fill="both", expand=True)
        self._render_latest()

    def hide(self) -> None:
        self._panel = None

    def set_vehicle_message(self, message: VehicleStateMessage) -> None:
        self._presenter.set_vehicle_message(message)
        self._render_latest()

    def set_vehicle_error(self, topic: str, error: Exception) -> None:
        self._presenter.set_vehicle_error(topic, error)
        self._render_latest()

    def _render_latest(self) -> None:
        panel = self._panel
        if panel is None:
            return

        snapshot = self._presenter.snapshot()
        if snapshot.error is not None:
            panel.set_connection_state(VehicleConnectionState.ERROR)
            self.set_status(snapshot.status)
            return

        message = snapshot.vehicle
        if message is None:
            panel.set_connection_state(VehicleConnectionState.DISCONNECTED)
            self.set_status(snapshot.status)
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
        self.set_status(snapshot.status)
