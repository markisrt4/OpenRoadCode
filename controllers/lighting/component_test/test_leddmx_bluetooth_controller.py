from __future__ import annotations

import unittest

from controllers.lighting import (
    LightingConnectionStatus,
    RgbColor,
)
from controllers.lighting.adapters.leddmx_controller import (
    LedDmxController,
)
from hardware_io.bluetooth import BleGattState, BleGattStatus


class _Transport:
    def __init__(self) -> None:
        self.state = BleGattState()
        self.writes: list[bytes] = []

    def current_state(self) -> BleGattState:
        return self.state

    async def connect(self) -> None:
        self.state = BleGattState(
            status=BleGattStatus.CONNECTED,
            address="AA:BB:CC:DD:EE:FF",
        )

    async def disconnect(self) -> None:
        self.state = BleGattState(status=BleGattStatus.DISCONNECTED)

    async def write(self, data: bytes) -> None:
        if not self.state.connected:
            await self.connect()
        self.writes.append(data)


class LedDmxBluetoothControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = _Transport()
        self.controller = LedDmxController(self.transport)
        self.addCleanup(self.controller.close)

    def test_connect_and_write_track_transport_and_requested_state(self) -> None:
        self.controller.connect().result(timeout=1)
        self.controller.set_color(RgbColor(4, 5, 6)).result(timeout=1)

        state = self.controller.current_state()
        self.assertEqual(
            LightingConnectionStatus.CONNECTED,
            state.connection_status,
        )
        self.assertEqual("AA:BB:CC:DD:EE:FF", state.device_address)
        self.assertEqual(RgbColor(4, 5, 6), state.color)
        self.assertEqual(1, len(self.transport.writes))

    def test_transport_reconnect_state_is_mapped_without_ble_coupling(self) -> None:
        self.transport.state = BleGattState(
            status=BleGattStatus.RECONNECTING,
            last_error="Bluetooth connection was lost",
        )

        state = self.controller.current_state()

        self.assertEqual(
            LightingConnectionStatus.RECONNECTING,
            state.connection_status,
        )
        self.assertIn("lost", state.last_connection_error or "")


if __name__ == "__main__":
    unittest.main()
