"""Tests for toolkit-independent radio session configuration."""

import unittest

from apps.carUi.radio.radio_session_config import RadioSessionConfig


class RadioSessionConfigTest(unittest.TestCase):
    def test_valid_configuration_is_preserved(self) -> None:
        config = RadioSessionConfig("fm", "FM Radio", 100_000)

        self.assertEqual(config.key, "fm")
        self.assertEqual(config.title, "FM Radio")
        self.assertEqual(config.default_step_hz, 100_000)

    def test_invalid_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RadioSessionConfig("", "FM Radio", 100_000)
        with self.assertRaises(ValueError):
            RadioSessionConfig("fm", "", 100_000)
        with self.assertRaises(ValueError):
            RadioSessionConfig("fm", "FM Radio", 0)


if __name__ == "__main__":
    unittest.main()
