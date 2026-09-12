# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic SAE J1979 adapter for tests without vehicle hardware."""

from __future__ import annotations

import math

from protocols.obd2.obd2_adapter_if import Obd2AdapterIf
from protocols.obd2.obd2_request import Obd2Request
from protocols.obd2.obd2_response import Obd2Response


class SimulatedObd2Adapter(Obd2AdapterIf):
    """Return configurable raw PID payloads through the production adapter API."""

    def __init__(self, responses: dict[int, bytes] | None = None) -> None:
        self._connected = False
        self._responses = dict(responses or self.default_responses())
        self.requests: list[Obd2Request] = []
        self._phase = 0.0

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def advance(self, step_radians: float = 0.12) -> None:
        """Advance the simulated vehicle and update raw Mode 01 PID bytes."""
        self._phase += step_radians
        wave = (math.sin(self._phase) + 1.0) / 2.0

        rpm = 900.0 + 3600.0 * wave
        speed_kph = round(20.0 + 120.0 * wave)
        throttle_pct = 8.0 + 72.0 * wave
        pedal_pct = 5.0 + 68.0 * wave
        load_pct = 20.0 + 70.0 * wave
        map_kpa = round(45.0 + 110.0 * wave)
        maf_gps = 3.0 + 35.0 * wave
        coolant_c = round(88.0 + 4.0 * math.sin(self._phase * 0.2))
        intake_c = round(30.0 + 8.0 * math.sin(self._phase * 0.4))
        fuel_pct = max(5.0, 75.0 - self._phase * 0.05)
        voltage_v = 13.8 + 0.15 * math.sin(self._phase * 0.5)
        fuel_rate_lph = 2.0 + 10.0 * wave
        equivalence_ratio = 1.0 - 0.15 * max(0.0, (wave - 0.7) / 0.3)
        measured_equivalence_ratio = equivalence_ratio + 0.01 * math.sin(self._phase * 1.7)
        short_term_trim_pct = 4.0 * math.sin(self._phase * 1.3)
        long_term_trim_pct = -1.5 + 0.8 * math.sin(self._phase * 0.15)
        ignition_advance_deg = 8.0 + 26.0 * (1.0 - wave)
        absolute_load_pct = min(130.0, load_pct * 1.12)
        commanded_throttle_pct = max(0.0, min(100.0, throttle_pct + 3.0 * math.sin(self._phase * 0.9)))
        fuel_rail_pressure_kpa = 3000.0 + 10_000.0 * wave
        fuel_system_status = 0x04 if wave > 0.82 else 0x02

        rpm_raw = max(0, min(0xFFFF, round(rpm * 4.0)))
        maf_raw = max(0, min(0xFFFF, round(maf_gps * 100.0)))
        voltage_raw = max(0, min(0xFFFF, round(voltage_v * 1000.0)))
        fuel_rate_raw = max(0, min(0xFFFF, round(fuel_rate_lph * 20.0)))
        equivalence_raw = max(0, min(0xFFFF, round(equivalence_ratio * 32768.0)))
        measured_equivalence_raw = max(
            0,
            min(0xFFFF, round(measured_equivalence_ratio * 32768.0)),
        )
        fuel_rail_raw = max(
            0,
            min(0xFFFF, round(fuel_rail_pressure_kpa / 10.0)),
        )
        absolute_load_raw = max(
            0,
            min(0xFFFF, round(absolute_load_pct * 2.55)),
        )

        self._responses.update(
            {
                0x03: bytes([fuel_system_status, 0x00]),
                0x04: bytes([_percent_byte(load_pct)]),
                0x05: bytes([max(0, min(255, coolant_c + 40))]),
                0x06: bytes([_fuel_trim_byte(short_term_trim_pct)]),
                0x07: bytes([_fuel_trim_byte(long_term_trim_pct)]),
                0x0B: bytes([max(0, min(255, map_kpa))]),
                0x0C: rpm_raw.to_bytes(2, "big"),
                0x0D: bytes([max(0, min(255, speed_kph))]),
                0x0E: bytes([_timing_advance_byte(ignition_advance_deg)]),
                0x0F: bytes([max(0, min(255, intake_c + 40))]),
                0x10: maf_raw.to_bytes(2, "big"),
                0x11: bytes([_percent_byte(throttle_pct)]),
                0x23: fuel_rail_raw.to_bytes(2, "big"),
                0x2F: bytes([_percent_byte(fuel_pct)]),
                0x33: bytes([101]),
                0x34: measured_equivalence_raw.to_bytes(2, "big"),
                0x42: voltage_raw.to_bytes(2, "big"),
                0x43: absolute_load_raw.to_bytes(2, "big"),
                0x44: equivalence_raw.to_bytes(2, "big"),
                0x49: bytes([_percent_byte(pedal_pct)]),
                0x4C: bytes([_percent_byte(commanded_throttle_pct)]),
                0x5E: fuel_rate_raw.to_bytes(2, "big"),
            }
        )

    def request(self, request: Obd2Request) -> tuple[Obd2Response, ...]:
        if not self._connected:
            raise RuntimeError("simulated OBD-II adapter is not connected")
        self.requests.append(request)
        if request.mode != 0x01 or request.pid is None:
            return ()
        data = self._responses.get(request.pid)
        if data is None:
            return ()
        return (Obd2Response(mode=0x41, pid=request.pid, data=data, ecu_id=0x7E8),)

    @staticmethod
    def default_responses() -> dict[int, bytes]:
        """Return a realistic deterministic Mode 01 response set."""
        return {
            0x00: bytes.fromhex("3E3F8001"),  # 03,04,05,06,07,0B..11,20
            0x20: bytes.fromhex("20023001"),  # 23,2F,33,34,40
            0x40: bytes.fromhex("70900004"),  # 42,43,44,49,4C,5E
            0x03: bytes([0x02, 0x00]),        # closed-loop fuel control
            0x04: bytes([128]),               # ~50.2 % load
            0x05: bytes([130]),               # 90 C
            0x06: bytes([128]),               # 0 % STFT
            0x07: bytes([126]),               # ~-1.6 % LTFT
            0x0B: bytes([135]),               # 135 kPa MAP
            0x0C: bytes.fromhex("2EE0"),      # 3000 rpm
            0x0D: bytes([100]),               # 100 km/h
            0x0E: bytes([152]),               # 12 deg timing advance
            0x0F: bytes([75]),                # 35 C
            0x10: bytes.fromhex("09C4"),      # 25.00 g/s
            0x11: bytes([102]),               # 40 % throttle
            0x23: bytes.fromhex("0138"),        # 3120 kPa rail pressure
            0x2F: bytes([191]),               # ~74.9 % fuel
            0x33: bytes([101]),               # 101 kPa baro
            0x34: bytes.fromhex("80A4"),        # ~1.005 measured lambda
            0x42: bytes.fromhex("35E8"),      # 13.800 V
            0x43: bytes.fromhex("00E6"),       # ~90.2 % absolute load
            0x44: bytes.fromhex("8000"),      # 1.0 commanded equivalence
            0x49: bytes([89]),                 # ~34.9 % pedal
            0x4C: bytes([107]),                # ~42 % commanded throttle
            0x5E: bytes.fromhex("00A0"),       # 8.0 L/h fuel rate
        }


def _percent_byte(percent: float) -> int:
    return max(0, min(255, round(percent * 255.0 / 100.0)))


def _fuel_trim_byte(percent: float) -> int:
    return max(0, min(255, round((percent + 100.0) * 1.28)))


def _timing_advance_byte(degrees: float) -> int:
    return max(0, min(255, round((degrees + 64.0) * 2.0)))
