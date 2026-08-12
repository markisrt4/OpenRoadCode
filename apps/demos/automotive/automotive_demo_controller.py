# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Simulated SI data source for the automotive UI demonstration."""

from __future__ import annotations

import math
import time
from threading import Event, Thread

from ui.automotive import (
    DiagnosticSeverity,
    DiagnosticStatus,
    DiagnosticTroubleCode,
    DiagnosticsRequestHandlerIf,
    ExteriorLight,
    Gear,
    SeatPosition,
    TirePosition,
    VehicleBodyUiIf,
    VehicleConnectionState,
    VehicleConnectionUiIf,
    VehicleDiagnosticsUiIf,
    VehicleOpening,
    VehicleTireUiIf,
    VehicleTripUiIf,
    VehicleUiIf,
)


class AutomotiveDemoController(DiagnosticsRequestHandlerIf):
    """Drive automotive UI contracts with deterministic simulated values."""

    def __init__(
        self,
        vehicle_ui: VehicleUiIf,
        trip_ui: VehicleTripUiIf,
        tire_ui: VehicleTireUiIf,
        body_ui: VehicleBodyUiIf,
        diagnostics_ui: VehicleDiagnosticsUiIf,
        connection_ui: VehicleConnectionUiIf,
    ) -> None:
        self._vehicle_ui = vehicle_ui
        self._trip_ui = trip_ui
        self._tire_ui = tire_ui
        self._body_ui = body_ui
        self._diagnostics_ui = diagnostics_ui
        self._connection_ui = connection_ui
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._started_at = 0.0
        self._diagnostic_active = True

    def start(self) -> None:
        """Start producing simulated updates."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = time.monotonic()
        self._diagnostics_ui.set_diagnostics_request_handler(self)
        self._connection_ui.set_connection_state(VehicleConnectionState.CONNECTING)
        self._seed_slow_state()
        self._thread = Thread(target=self._run, name="automotive-demo", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop producing updates and disconnect the request handler."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._diagnostics_ui.set_diagnostics_request_handler(None)
        self._connection_ui.set_connection_state(VehicleConnectionState.DISCONNECTED)

    def request_clear_diagnostics(self) -> None:
        """Clear the simulated diagnostic condition."""
        self._diagnostic_active = False
        self._diagnostics_ui.set_malfunction_indicator(False)
        self._diagnostics_ui.set_trouble_codes(())

    def _seed_slow_state(self) -> None:
        self._vehicle_ui.set_fuel_level(0.68)
        self._vehicle_ui.set_ambient_temperature(294.15)
        self._vehicle_ui.set_control_voltage(14.2)
        self._vehicle_ui.set_engine_oil_pressure(310_000.0)
        self._vehicle_ui.set_transmission_temperature(343.15)
        self._trip_ui.set_odometer(186_420_000.0)
        self._trip_ui.set_trip_distance(42_300.0)
        self._trip_ui.set_estimated_range(465_000.0)
        self._trip_ui.set_average_fuel_consumption(8.7e-8)
        self._trip_ui.set_fuel_used(0.0037)
        for index, position in enumerate(TirePosition):
            self._tire_ui.set_tire_pressure(position, 224_000.0 + index * 1_000.0)
            self._tire_ui.set_tire_temperature(position, 300.15 + index)
            self._tire_ui.set_tire_pressure_warning(position, False)
        self._body_ui.set_opening_state(VehicleOpening.FRONT_LEFT_DOOR, False)
        self._body_ui.set_seat_belt_state(SeatPosition.DRIVER, True)
        self._body_ui.set_exterior_light_state(ExteriorLight.HEADLIGHTS, True)
        self._body_ui.set_parking_brake(False)
        self._diagnostics_ui.set_emissions_readiness(True)
        self._publish_diagnostics()

    def _publish_diagnostics(self) -> None:
        self._diagnostics_ui.set_malfunction_indicator(self._diagnostic_active)
        if self._diagnostic_active:
            self._diagnostics_ui.set_trouble_codes((
                DiagnosticTroubleCode(
                    code="P0456",
                    status=DiagnosticStatus.CONFIRMED,
                    severity=DiagnosticSeverity.WARNING,
                    description="Small evaporative emissions leak",
                ),
            ))
        else:
            self._diagnostics_ui.set_trouble_codes(())

    def _run(self) -> None:
        self._connection_ui.set_connection_state(VehicleConnectionState.CONNECTED)
        last_slow_update = 0.0
        while not self._stop_event.is_set():
            elapsed = time.monotonic() - self._started_at
            speed_mps = 22.0 + 7.0 * math.sin(elapsed * 0.35)
            engine_rpm = 2_400.0 + 1_300.0 * math.sin(elapsed * 0.8)
            throttle = 0.35 + 0.22 * math.sin(elapsed * 0.8)
            boost_pa = max(0.0, throttle - 0.38) * 145_000.0

            self._vehicle_ui.set_vehicle_speed(speed_mps)
            self._vehicle_ui.set_engine_speed(engine_rpm / 9.549297)
            self._vehicle_ui.set_gear(self._gear_for_speed(speed_mps))
            self._vehicle_ui.set_throttle_position(throttle)
            self._vehicle_ui.set_accelerator_position(throttle * 0.94)
            self._vehicle_ui.set_engine_load(min(1.0, throttle + 0.12))
            self._vehicle_ui.set_boost_pressure(boost_pa)
            self._vehicle_ui.set_manifold_pressure(101_325.0 + boost_pa)
            self._vehicle_ui.set_mass_air_flow(0.018 + throttle * 0.075)
            self._trip_ui.set_instantaneous_fuel_consumption(
                6.5e-8 + throttle * 5.0e-8,
            )

            if elapsed - last_slow_update >= 1.0:
                self._vehicle_ui.set_coolant_temperature(365.15 + math.sin(elapsed / 8.0))
                self._vehicle_ui.set_intake_air_temperature(306.15 + boost_pa / 20_000.0)
                self._vehicle_ui.set_engine_oil_temperature(371.15 + math.sin(elapsed / 10.0))
                self._vehicle_ui.set_barometric_pressure(101_325.0)
                last_slow_update = elapsed
            self._stop_event.wait(0.1)

    @staticmethod
    def _gear_for_speed(speed_mps: float) -> Gear:
        if speed_mps < 5.0:
            return Gear.FIRST
        if speed_mps < 10.0:
            return Gear.SECOND
        if speed_mps < 16.0:
            return Gear.THIRD
        if speed_mps < 22.0:
            return Gear.FOURTH
        if speed_mps < 28.0:
            return Gear.FIFTH
        return Gear.SIXTH
