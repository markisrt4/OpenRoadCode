from __future__ import annotations

from dataclasses import dataclass

try:
    from bleak import BleakScanner
except ImportError:  # pragma: no cover
    BleakScanner = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class BleDeviceInfo:
    """
    Information reported for a discovered Bluetooth Low Energy device.
    """

    address: str
    name: str | None
    local_name: str | None
    rssi: int | None
    service_uuids: tuple[str, ...]
    manufacturer_data: dict[int, bytes]

    @property
    def display_name(self) -> str:
        """
        Return the best available device name.
        """
        return self.name or self.local_name or "Unknown"


class BleScanner:
    """
    Scans for nearby Bluetooth Low Energy devices.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        if BleakScanner is None:
            raise RuntimeError(
                "bleak is not installed. "
                "Install it using: python3 -m pip install bleak"
            )

        self._timeout_seconds = timeout_seconds

    @property
    def timeout_seconds(self) -> float:
        """Return the configured discovery timeout.

        @return Discovery timeout in seconds.
        """
        return self._timeout_seconds

    async def scan(self) -> list[BleDeviceInfo]:
        """
        Scan for nearby BLE devices.

        Returns:
            Discovered devices ordered from strongest to weakest signal.
        """
        if BleakScanner is None:
            raise RuntimeError("bleak is not installed")

        discovered = await BleakScanner.discover(
            timeout=self._timeout_seconds,
            return_adv=True,
        )

        devices: list[BleDeviceInfo] = []

        for device, advertisement in discovered.values():
            devices.append(
                BleDeviceInfo(
                    address=device.address,
                    name=device.name,
                    local_name=advertisement.local_name,
                    rssi=getattr(advertisement, "rssi", None),
                    service_uuids=tuple(
                        advertisement.service_uuids or ()
                    ),
                    manufacturer_data=dict(
                        advertisement.manufacturer_data or {}
                    ),
                )
            )

        devices.sort(
            key=lambda device: (
                device.rssi is not None,
                device.rssi if device.rssi is not None else -999,
            ),
            reverse=True,
        )

        return devices
