# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest

from protocols.can.elm_monitor_parser import parse_elm_monitor_output


class ElmMonitorParserTest(unittest.TestCase):
    def test_accepts_complete_spaced_frames(self):
        result = parse_elm_monitor_output(
            "153 20 00 00 FF 00 FF C0 DE\r"
            "2C0 00 00 00 00 00 00 00 00\r"
        )
        self.assertEqual([f.arbitration_id for f in result.frames], [0x153, 0x2C0])
        self.assertEqual(result.frames[0].data, bytes.fromhex("20 00 00 FF 00 FF C0 DE"))

    def test_rejects_corrupt_and_truncated_records(self):
        result = parse_elm_monitor_output(
            "165 FE D7 7F 00 00 00 01 57 <DATA ERROR\r"
            "BUFFER FULL\r"
            "080 00 23 3A 0C 0D 0C 0C B2\r"
            "153 20 00 00 FF"
        )
        self.assertEqual(len(result.frames), 1)
        self.assertEqual(result.data_error_count, 1)
        self.assertEqual(result.buffer_full_count, 1)
        self.assertEqual(result.malformed_count, 1)

    def test_rejects_invalid_payload(self):
        result = parse_elm_monitor_output("153 20 GG\r153 0\r")
        self.assertEqual(len(result.frames), 0)
        self.assertEqual(result.malformed_count, 2)


if __name__ == "__main__":
    unittest.main()
