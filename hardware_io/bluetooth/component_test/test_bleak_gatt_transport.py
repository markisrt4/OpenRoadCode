# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
import importlib
import unittest
from unittest.mock import patch

from hardware_io.bluetooth import BleGattStatus

_module = importlib.import_module("hardware_io.bluetooth.bleak_gatt_transport")


class _Device:
    def __init__(self, address: str) -> None:
        self.address = address
        self.name = "test-device"


class _Advertisement:
    local_name = "test-device"
    rssi = -40
    service_uuids: tuple[str, ...] = ()


class _Characteristic:
    uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"


class _Service:
    characteristics = (_Characteristic(),)


class _Scanner:
    device = _Device("AA:BB:CC:DD:EE:FF")

    @classmethod
    async def discover(cls, **_options):
        return {"target": (cls.device, _Advertisement())}

    @classmethod
    async def find_device_by_address(cls, address: str, **_options):
        return _Device(address)


class _Client:
    instances: list["_Client"] = []

    def __init__(self, device: _Device, **options) -> None:
        self.device = device
        self.is_connected = False
        self.services = (_Service(),)
        self.callback = options["disconnected_callback"]
        self.writes: list[bytes] = []
        self.instances.append(self)

    async def connect(self) -> None:
        self.is_connected = True

    async def disconnect(self) -> None:
        self.is_connected = False
        self.callback(self)

    async def write_gatt_char(self, _uuid: str, data: bytes, *, response: bool) -> None:
        self.writes.append(data)


class BleakGattTransportTest(unittest.TestCase):
    def setUp(self) -> None:
        _Client.instances.clear()
        self.client_patch = patch.object(_module, "BleakClient", _Client)
        self.scanner_patch = patch.object(_module, "BleakScanner", _Scanner)
        self.client_patch.start()
        self.scanner_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.addCleanup(self.scanner_patch.stop)

    def test_discovers_connects_and_writes_one_characteristic(self) -> None:
        transport = _module.BleakGattTransport(
            characteristic_uuid=_Characteristic.uuid,
            command_delay_seconds=0,
        )

        async def exercise() -> None:
            await transport.connect()
            await transport.write(b"lighting-command")

        asyncio.run(exercise())
        self.assertEqual(BleGattStatus.CONNECTED, transport.current_state().status)
        self.assertEqual([b"lighting-command"], _Client.instances[0].writes)

    def test_disconnect_only_closes_transport_owned_client(self) -> None:
        unrelated_client = _Client(
            _Device("11:22:33:44:55:66"),
            disconnected_callback=lambda _client: None,
        )
        unrelated_client.is_connected = True
        transport = _module.BleakGattTransport(
            characteristic_uuid=_Characteristic.uuid,
            command_delay_seconds=0,
        )

        async def exercise() -> None:
            await transport.connect()
            await transport.disconnect()

        asyncio.run(exercise())
        self.assertTrue(unrelated_client.is_connected)
        self.assertEqual(BleGattStatus.DISCONNECTED, transport.current_state().status)


if __name__ == "__main__":
    unittest.main()
