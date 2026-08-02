import unittest

from protocols.can import CanFrame, parse_compact_can_frame


class CanFrameTests(unittest.TestCase):
    def test_parses_standard_frame_with_data_length(self) -> None:
        frame = parse_compact_can_frame("7E804410C09D2")

        self.assertEqual(frame.arbitration_id, 0x7E8)
        self.assertEqual(frame.data, bytes.fromhex("410C09D2"))
        self.assertFalse(frame.is_extended_id)

    def test_parser_ignores_whitespace(self) -> None:
        frame = parse_compact_can_frame("7E8 04 41 0C 09 D2")

        self.assertEqual(frame, CanFrame(0x7E8, bytes.fromhex("410C09D2")))

    def test_parses_extended_frame(self) -> None:
        frame = parse_compact_can_frame(
            "18DAF110034100BE",
            extended_id=True,
        )

        self.assertEqual(frame.arbitration_id, 0x18DAF110)
        self.assertEqual(frame.data, bytes.fromhex("4100BE"))
        self.assertTrue(frame.is_extended_id)

    def test_rejects_incorrect_declared_length(self) -> None:
        with self.assertRaises(ValueError):
            parse_compact_can_frame("7E806410C09D2")

    def test_validates_standard_identifier_range(self) -> None:
        with self.assertRaises(ValueError):
            CanFrame(0x800, b"")

    def test_validates_classical_can_payload_length(self) -> None:
        with self.assertRaises(ValueError):
            CanFrame(0x123, bytes(9))


if __name__ == "__main__":
    unittest.main()
