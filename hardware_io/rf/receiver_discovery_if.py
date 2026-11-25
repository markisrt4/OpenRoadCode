"""Hardware-only receiver inventory contract."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReceiverDevice:
    vendor_id: str
    product_id: str
    serial: str
    usb_path: str

    @property
    def identity(self) -> str | None:
        if not self.serial:
            return None
        return f"{self.vendor_id}:{self.product_id}:{self.serial}"


class ReceiverDiscoveryIf(Protocol):
    def discover(self) -> tuple[ReceiverDevice, ...]: ...
