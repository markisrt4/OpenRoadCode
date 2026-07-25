from __future__ import annotations

from protocols.can import CanFrame, parse_compact_can_frame


def main() -> None:
    standard_input = "7E8 04 41 0C 09 D2"
    standard = parse_compact_can_frame(standard_input)
    assert standard == CanFrame(
        arbitration_id=0x7E8,
        data=bytes.fromhex("410C09D2"),
    )

    extended_input = "18DAF110 03 41 00 BE"
    extended = parse_compact_can_frame(
        extended_input,
        extended_id=True,
    )
    assert extended.arbitration_id == 0x18DAF110
    assert extended.data == bytes.fromhex("4100BE")
    assert extended.is_extended_id

    try:
        parse_compact_can_frame("7E806410C09D2")
    except ValueError:
        pass
    else:
        raise AssertionError("incorrect CAN data length was accepted")

    print("CAN frame component test")
    print()
    print(f"Input:          {standard_input}")
    print(f"Identifier:     0x{standard.arbitration_id:03X}")
    print("Identifier type: standard (11-bit)")
    print(f"Data length:    {len(standard.data)}")
    print(f"Data:           {standard.data.hex(' ').upper()}")
    print()
    print(f"Input:          {extended_input}")
    print(f"Identifier:     0x{extended.arbitration_id:08X}")
    print("Identifier type: extended (29-bit)")
    print(f"Data length:    {len(extended.data)}")
    print(f"Data:           {extended.data.hex(' ').upper()}")
    print()
    print("Invalid data-length rejection: PASS")
    print("CAN frame component test: PASS")


if __name__ == "__main__":
    main()
