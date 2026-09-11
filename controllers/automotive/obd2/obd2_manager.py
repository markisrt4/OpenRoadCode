# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import math
from datetime import datetime
from typing import TypeVar

from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.obd2.obd2_poll_scheduler import Obd2PollScheduler
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf
from protocols.obd2 import Obd2AdapterIf, Obd2Error, Obd2Request
from protocols.obd2.obd_pid_decoder import ObdPidDecoder
from protocols.obd2.obd_pids import (
    AcceleratorPedalPositionPid,
    BarometricPressurePid,
    CommandedEquivalenceRatioPid,
    ControlModuleVoltagePid,
    CoolantTempPid,
    EngineLoadPid,
    EngineFuelRatePid,
    EngineRpmPid,
    FuelLevelPid,
    IntakeAirTempPid,
    IntakeManifoldPressurePid,
    MassAirFlowPid,
    ThrottlePositionPid,
)

T = TypeVar("T")


class Obd2Manager(VehicleStateSourceIf):
    """Poll OBD-II PIDs and assemble SI-normalized vehicle snapshots."""

    def __init__(self, adapter: Obd2AdapterIf) -> None:
        self._adapter = adapter
        self._supported_pids: set[int] | None = None
        self._scheduler: Obd2PollScheduler | None = None

        self._rpm_pid = EngineRpmPid()
        self._map_pid = IntakeManifoldPressurePid()
        self._baro_pid = BarometricPressurePid()
        self._throttle_pid = ThrottlePositionPid()
        self._accelerator_pedal_pid = AcceleratorPedalPositionPid()
        self._engine_load_pid = EngineLoadPid()
        self._coolant_pid = CoolantTempPid()
        self._intake_temp_pid = IntakeAirTempPid()
        self._maf_pid = MassAirFlowPid()
        self._fuel_level_pid = FuelLevelPid()
        self._equivalence_ratio_pid = CommandedEquivalenceRatioPid()
        self._fuel_rate_pid = EngineFuelRatePid()
        self._voltage_pid = ControlModuleVoltagePid()

        self._rpm: float | None = None
        self._map_kpa: int | None = None
        self._throttle_pct: float | None = None
        self._accelerator_pedal_pct: float | None = None
        self._engine_load_pct: float | None = None
        self._commanded_equivalence_ratio: float | None = None
        self._fuel_rate_lph: float | None = None
        self._baro_kpa: int | None = None
        self._maf_gps: float | None = None
        self._coolant_temp_c: int | None = None
        self._intake_temp_c: int | None = None
        self._fuel_level_pct: float | None = None
        self._control_voltage: float | None = None

    def connect(self) -> None:
        self._adapter.connect()
        self._supported_pids = self._discover_supported_pids()
        self._scheduler = Obd2PollScheduler(
            rpm=self._rpm_pid,
            manifold_pressure=self._map_pid,
            standard=(
                self._throttle_pid,
                self._engine_load_pid,
                self._equivalence_ratio_pid,
                self._fuel_rate_pid,
                self._maf_pid,
            ),
            slow=(
                self._accelerator_pedal_pid,
                self._baro_pid,
                self._coolant_pid,
                self._intake_temp_pid,
                self._fuel_level_pid,
                self._voltage_pid,
            ),
            supported_pids=self._supported_pids,
        )

    def disconnect(self) -> None:
        self._adapter.disconnect()

    @property
    def supported_pids(self) -> frozenset[int] | None:
        """Return the Mode 01 PID set discovered at connect time."""
        return (
            None
            if self._supported_pids is None
            else frozenset(self._supported_pids)
        )

    def read_state(self) -> VehicleState:
        """Perform at most one physical PID request and return cached state."""
        scheduler = self._scheduler
        if scheduler is None:
            scheduler = Obd2PollScheduler(
                rpm=self._rpm_pid,
                manifold_pressure=self._map_pid,
                standard=(
                    self._throttle_pid,
                    self._engine_load_pid,
                    self._equivalence_ratio_pid,
                    self._fuel_rate_pid,
                    self._maf_pid,
                ),
                slow=(
                    self._accelerator_pedal_pid,
                    self._baro_pid,
                    self._coolant_pid,
                    self._intake_temp_pid,
                    self._fuel_level_pid,
                    self._voltage_pid,
                ),
                supported_pids=self._supported_pids,
            )
            self._scheduler = scheduler

        decoder = scheduler.next_decoder()
        if decoder is not None:
            self._update_cached_value(decoder)

        return VehicleState(
            timestamp=datetime.now(),
            engine_speed_rad_s=self._rpm_to_rad_s(self._rpm),
            vehicle_speed_m_s=None,
            throttle_position=self._percent_to_fraction(self._throttle_pct),
            accelerator_pedal_position=self._percent_to_fraction(
                self._accelerator_pedal_pct
            ),
            engine_load=self._percent_to_fraction(self._engine_load_pct),
            intake_manifold_pressure_pa=self._kpa_to_pa(self._map_kpa),
            barometric_pressure_pa=self._kpa_to_pa(self._baro_kpa),
            boost_pressure_pa=self._calculate_boost_pa(
                self._map_kpa,
                self._baro_kpa,
            ),
            mass_air_flow_kg_s=self._gps_to_kg_s(self._maf_gps),
            coolant_temperature_k=self._celsius_to_kelvin(self._coolant_temp_c),
            intake_air_temperature_k=self._celsius_to_kelvin(
                self._intake_temp_c
            ),
            fuel_level=self._percent_to_fraction(self._fuel_level_pct),
            commanded_equivalence_ratio=self._commanded_equivalence_ratio,
            engine_fuel_rate_m3_s=self._lph_to_m3_s(self._fuel_rate_lph),
            control_voltage_v=self._control_voltage,
        )

    def _update_cached_value(self, decoder: ObdPidDecoder) -> None:
        value = self._read(decoder)
        pid = decoder.pid
        if pid == self._rpm_pid.pid:
            self._rpm = value
        elif pid == self._map_pid.pid:
            self._map_kpa = value
        elif pid == self._throttle_pid.pid:
            self._throttle_pct = value
        elif pid == self._accelerator_pedal_pid.pid:
            self._accelerator_pedal_pct = value
        elif pid == self._engine_load_pid.pid:
            self._engine_load_pct = value
        elif pid == self._equivalence_ratio_pid.pid:
            self._commanded_equivalence_ratio = value
        elif pid == self._fuel_rate_pid.pid:
            self._fuel_rate_lph = value
        elif pid == self._maf_pid.pid:
            self._maf_gps = value
        elif pid == self._baro_pid.pid:
            self._baro_kpa = value
        elif pid == self._coolant_pid.pid:
            self._coolant_temp_c = value
        elif pid == self._intake_temp_pid.pid:
            self._intake_temp_c = value
        elif pid == self._fuel_level_pid.pid:
            self._fuel_level_pct = value
        elif pid == self._voltage_pid.pid:
            self._control_voltage = value

    def _read(self, pid_decoder: ObdPidDecoder[T]) -> T | None:
        if self._supported_pids is not None and pid_decoder.pid not in self._supported_pids:
            return None
        responses = self._adapter.request(Obd2Request(mode=0x01, pid=pid_decoder.pid))
        if not responses:
            return None
        return pid_decoder.decode(responses[0].data)

    def _discover_supported_pids(self) -> set[int] | None:
        supported: set[int] = set()
        found_response = False
        range_start = 0x00
        try:
            while range_start <= 0xE0:
                responses = self._adapter.request(Obd2Request(mode=0x01, pid=range_start))
                if not responses:
                    break
                range_pids: set[int] = set()
                for response in responses:
                    if len(response.data) < 4:
                        continue
                    found_response = True
                    range_pids.update(self._decode_supported_pid_bitmap(range_start, response.data[:4]))
                supported.update(range_pids)
                next_range = range_start + 0x20
                if next_range not in range_pids:
                    break
                range_start = next_range
        except Obd2Error:
            return None
        return supported if found_response else None

    @staticmethod
    def _decode_supported_pid_bitmap(range_start: int, bitmap: bytes) -> set[int]:
        supported: set[int] = set()
        for byte_index, value in enumerate(bitmap):
            for bit_index in range(8):
                if value & (0x80 >> bit_index):
                    supported.add(range_start + byte_index * 8 + bit_index + 1)
        return supported

    @staticmethod
    def _rpm_to_rad_s(value: float | None) -> float | None:
        return None if value is None else value * 2.0 * math.pi / 60.0

    @staticmethod
    def _percent_to_fraction(value: float | None) -> float | None:
        return None if value is None else value / 100.0

    @staticmethod
    def _kpa_to_pa(value: int | None) -> float | None:
        return None if value is None else value * 1000.0

    @staticmethod
    def _gps_to_kg_s(value: float | None) -> float | None:
        return None if value is None else value / 1000.0

    @staticmethod
    def _lph_to_m3_s(value: float | None) -> float | None:
        return None if value is None else value / 1000.0 / 3600.0

    @staticmethod
    def _celsius_to_kelvin(value: int | None) -> float | None:
        return None if value is None else value + 273.15

    @staticmethod
    def _calculate_boost_pa(map_kpa: int | None, baro_kpa: int | None) -> float | None:
        if map_kpa is None or baro_kpa is None:
            return None
        return (map_kpa - baro_kpa) * 1000.0
