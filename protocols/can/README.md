# CAN Protocol Models

The `protocols.can` package provides transport-independent CAN frame models and
parsers that can be reused by ELM327, SocketCAN, and future CAN hardware.

```python
from protocols.can import parse_compact_can_frame


frame = parse_compact_can_frame("7E804410C09D2")

assert frame.arbitration_id == 0x7E8
assert frame.data == bytes.fromhex("410C09D2")
```

`CanFrame` supports 11-bit and 29-bit identifiers, Classical CAN payloads, and
CAN FD payloads. Transport-specific status text and OBD-II interpretation do
not belong in this package.

## Component Test

Run the dependency-free frame parsing component test from the project root:

```bash
python3 -m protocols.can.component_test.can_frame_component_test
```

It displays parsed standard and extended identifiers, payload lengths, and data
bytes. It also verifies whitespace-tolerant input and rejection of an incorrect
data length.
