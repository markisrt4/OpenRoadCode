from __future__ import annotations

import inspect
import unittest

from controllers.lighting.adapters import leddmx_controller
from hardware_io.bluetooth.ble_gatt_transport_if import BleGattTransportIf


class LightingLayerBoundaryTest(unittest.TestCase):
    def test_leddmx_controller_depends_on_transport_contract_not_bleak(self) -> None:
        source = inspect.getsource(leddmx_controller)

        self.assertIn("BleGattTransportIf", source)
        self.assertNotIn("from bleak", source)
        self.assertNotIn("BleakClient", source)
        self.assertNotIn("BleakScanner", source)

    def test_transport_contract_is_runtime_checkable(self) -> None:
        class Transport:
            def current_state(self):
                return None

            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def write(self, data: bytes) -> None:
                pass

        self.assertIsInstance(Transport(), BleGattTransportIf)


if __name__ == "__main__":
    unittest.main()
