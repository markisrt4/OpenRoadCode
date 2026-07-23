from attr import dataclass


@dataclass(frozen=True)
class BleDeviceInfo:
    """Describe a Bluetooth Low Energy discovery result."""
    address: str
    name: str | None
    rssi: int | None
    service_uuids: tuple[str, ...]
