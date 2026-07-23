from __future__ import annotations

import string

from protocols.can.can_frame import CanFrame


def parse_compact_can_frame(
    value: str,
    *,
    extended_id: bool = False,
    includes_data_length: bool = True,
) -> CanFrame:
    """Parse a compact hexadecimal CAN frame.

    Standard frames use three identifier digits and extended frames use eight.
    When ``includes_data_length`` is true, the identifier is followed by a
    one-byte payload length. Whitespace is ignored.

    Examples: ``7E804410C09D2`` and ``18DAF110034100BE``.
    """

    compact = "".join(value.split()).upper()
    identifier_width = 8 if extended_id else 3
    minimum_width = identifier_width + (2 if includes_data_length else 0)

    if len(compact) < minimum_width or any(
        character not in string.hexdigits for character in compact
    ):
        raise ValueError(f"Malformed compact CAN frame: {value!r}")

    payload_hex = compact[identifier_width:]
    declared_length: int | None = None
    if includes_data_length:
        declared_length = int(payload_hex[:2], 16)
        payload_hex = payload_hex[2:]

    if len(payload_hex) % 2:
        raise ValueError(f"CAN payload has an incomplete byte: {value!r}")

    data = bytes.fromhex(payload_hex)
    if declared_length is not None and declared_length != len(data):
        raise ValueError(
            f"CAN frame declares {declared_length} data bytes but contains "
            f"{len(data)}: {value!r}"
        )

    return CanFrame(
        arbitration_id=int(compact[:identifier_width], 16),
        data=data,
        is_extended_id=extended_id,
    )

