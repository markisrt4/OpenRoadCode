from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CanFrame:
    """A transport-independent Classical CAN or CAN FD data frame."""

    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    is_fd: bool = False

    def __post_init__(self) -> None:
        maximum_id = 0x1FFFFFFF if self.is_extended_id else 0x7FF
        if not 0 <= self.arbitration_id <= maximum_id:
            id_kind = "29-bit" if self.is_extended_id else "11-bit"
            raise ValueError(
                f"arbitration_id is outside the {id_kind} CAN range"
            )
        if not isinstance(self.data, bytes):
            raise TypeError("data must be bytes")

        maximum_length = 64 if self.is_fd else 8
        if len(self.data) > maximum_length:
            frame_kind = "CAN FD" if self.is_fd else "Classical CAN"
            raise ValueError(
                f"{frame_kind} payload cannot exceed {maximum_length} bytes"
            )

