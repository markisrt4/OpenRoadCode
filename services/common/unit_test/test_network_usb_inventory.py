"""Offline regression tests for read-only runtime hardware inventory."""
import tempfile
import unittest
from pathlib import Path
from services.common.network_usb_inventory import collect_inventory


class NetworkUsbInventoryTests(unittest.TestCase):
    def test_empty_sysfs_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            report = collect_inventory(sys_root=Path(directory))
            self.assertEqual(report["networks_status"], "restricted_or_unavailable")
            self.assertEqual(report["usb_sysfs"]["status"], "restricted_or_unavailable")
            self.assertEqual(report["usb_devices"], [])

    def test_inventory_reads_sysfs_without_claiming_usb_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            net = root / "class/net/eth0"
            net.mkdir(parents=True)
            (net / "operstate").write_text("up\n")
            (net / "speed").write_text("1000\n")
            usb = root / "bus/usb/devices/1-1"
            usb.mkdir(parents=True)
            (usb / "idVendor").write_text("0bda\n")
            (usb / "idProduct").write_text("8153\n")
            report = collect_inventory(sys_root=root)
            self.assertEqual(report["networks"][0]["speed_mbps"], "1000")
            self.assertEqual(report["networks"][0]["usb_backing"], "unconfirmed")
            self.assertEqual(report["usb_sysfs"]["devices"][0]["vendor_id_hex"], "0bda")


if __name__ == "__main__":
    unittest.main()
