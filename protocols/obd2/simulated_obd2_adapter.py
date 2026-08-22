# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic SAE J1979 adapter for tests without vehicle hardware."""

from __future__ import annotations

from protocols.obd2.obd2_adapter_if import Obd2AdapterIf
from protocols.obd2.obd2_request import Obd2Request
from protocols.obd2.obd2_response import Obd2Response


class SimulatedObd2Adapter(Obd2AdapterIf):
    """Return configured raw PID payloads through the production adapter API."""

    def __init__(self, responses: dict[int, bytes] | None = None) -> None:
        self._connected = False
        self._responses = dict(responses or self.default_responses())
        self.requests: list[Obd2Request] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

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
        # Supported-PID bitmaps include the next range marker where required.
        return {
            0x00: bytes.fromhex("183A8013"),  # 04,05,0B,0C,0D,0F,10,11,20
            0x20: bytes.fromhex("00020001"),  # 2F,40
            0x40: bytes.fromhex("40800000"),  # 42,49
            0x04: bytes([128]),               # ~50.2 % load
            0x05: bytes([130]),               # 90 C
            0x0B: bytes([135]),               # 135 kPa MAP
            0x0C: bytes.fromhex("2EE0"),      # 3000 rpm
            0x0D: bytes([100]),               # 100 km/h
            0x0F: bytes([75]),                # 35 C
            0x10: bytes.fromhex("09C4"),      # 25.00 g/s
            0x11: bytes([102]),               # 40 % throttle
            0x2F: bytes([191]),               # ~74.9 % fuel
            0x33: bytes([101]),               # 101 kPa baro
            0x42: bytes.fromhex("35E8"),      # 13.800 V
            0x49: bytes([89]),                 # ~34.9 % pedal
        }
