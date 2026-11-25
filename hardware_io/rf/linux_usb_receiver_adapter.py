"""Discover supported RTL-SDR USB devices without opening them."""

from pathlib import Path

from hardware_io.rf.receiver_discovery_if import ReceiverDevice

RTL_USB_IDS = frozenset({("0bda", "2832"), ("0bda", "2838")})


class LinuxUsbReceiverAdapter:
    def __init__(self, root: Path = Path("/sys/bus/usb/devices")) -> None:
        self._root = root

    def discover(self) -> tuple[ReceiverDevice, ...]:
        devices = []
        if not self._root.exists():
            return ()
        for path in sorted(self._root.iterdir()):
            try:
                vendor = (path / "idVendor").read_text().strip().lower()
                product = (path / "idProduct").read_text().strip().lower()
                if (vendor, product) not in RTL_USB_IDS:
                    continue
                try:
                    serial = (path / "serial").read_text().strip()
                except OSError:
                    serial = ""
                devices.append(ReceiverDevice(vendor, product, serial, path.name))
            except OSError:
                # USB devices can disappear while enumerating.
                continue
        return tuple(devices)
