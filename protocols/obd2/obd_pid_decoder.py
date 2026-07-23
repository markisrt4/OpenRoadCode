from __future__ import annotations

from typing import Protocol, TypeVar


T_co = TypeVar("T_co", covariant=True)


class ObdPidDecoder(Protocol[T_co]):
    """Decoder contract for a standardized OBD-II PID.

    Decoders return values in the canonical units defined by SAE J1979.
    Display-unit conversion belongs in the application or presentation layer.
    """

    @property
    def mode(self) -> int:
        """Return the SAE J1979 service mode."""
        ...

    @property
    def pid(self) -> int:
        """Return the parameter identifier."""
        ...

    @property
    def unit(self) -> str:
        """Return the canonical unit of the decoded value."""
        ...

    def decode(self, data: bytes) -> T_co | None:
        """Decode response payload bytes.

        @param data PID payload excluding mode and PID bytes.
        @return Decoded value, or ``None`` when payload bytes are insufficient.
        """
        ...


def byte_at(data: bytes, index: int) -> int:
    """Return a required response byte.

    @param data OBD-II payload bytes.
    @param index Zero-based byte index.
    @raises ValueError if the requested byte is absent.
    """
    try:
        return data[index]
    except IndexError:
        raise ValueError(f"OBD-II response does not contain byte {index}") from None
