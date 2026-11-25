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
        """!
        @brief Derive a persistent USB identity from the device descriptor.
        @return Vendor, product and serial identity, or None when serial is missing.
        """
        if not self.serial:
            return None
        return f"{self.vendor_id}:{self.product_id}:{self.serial}"


class ReceiverDiscoveryIf(Protocol):
    def discover(self) -> tuple[ReceiverDevice, ...]:
        """!
        @brief Discover connected RF receivers visible to the platform.
        @return A snapshot of connected devices, including ambiguous identities.
        """
        ...
