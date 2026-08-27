# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timedelta, timezone
import unittest

from messaging.contracts.common.timestamp import encode_timestamp


class TimestampContractTest(unittest.TestCase):
    def test_epoch(self) -> None:
        self.assertEqual(
            encode_timestamp(datetime(1970, 1, 1, tzinfo=timezone.utc)),
            {"seconds": 0, "nanoseconds": 0},
        )

    def test_fractional_second_uses_nanoseconds(self) -> None:
        encoded = encode_timestamp(
            datetime(2026, 8, 21, 17, 27, 14, 123456, tzinfo=timezone.utc)
        )
        self.assertEqual(encoded["nanoseconds"], 123_456_000)
        self.assertGreater(encoded["seconds"], 0)

    def test_timezone_is_normalized_to_utc(self) -> None:
        eastern = timezone(timedelta(hours=-4))
        local = datetime(2026, 8, 21, 13, 27, 14, tzinfo=eastern)
        utc = datetime(2026, 8, 21, 17, 27, 14, tzinfo=timezone.utc)
        self.assertEqual(encode_timestamp(local), encode_timestamp(utc))

    def test_naive_datetime_is_interpreted_as_utc(self) -> None:
        naive = datetime(2026, 8, 21, 17, 27, 14)
        aware = naive.replace(tzinfo=timezone.utc)
        self.assertEqual(encode_timestamp(naive), encode_timestamp(aware))

    def test_pre_epoch_timestamp_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            encode_timestamp(
                datetime(1969, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
            )


if __name__ == "__main__":
    unittest.main()
