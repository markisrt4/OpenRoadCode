"""Tests for the barometric sensor component-test CLI."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from hardware_io.environmental.component_test.barometric_cli import (
    parse_args,
    print_sample,
)


class _Sensor:
    def get_pressure_pa(self) -> float:
        return 101325.0

    def get_temperature_c(self) -> float:
        return 20.0


class BarometricCliTest(unittest.TestCase):
    def test_metric_units_are_the_default(self) -> None:
        args = parse_args([])

        self.assertFalse(args.imperial)

    def test_imperial_option_is_parsed(self) -> None:
        args = parse_args(["--imperial"])

        self.assertTrue(args.imperial)

    def test_imperial_sample_converts_pressure_and_temperature(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            print_sample(_Sensor(), imperial=True)

        self.assertEqual(
            "Pressure:  29.921 inHg  Temperature:  68.00 °F\n",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
