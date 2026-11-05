# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hardware-free configuration checks for the standalone live RDS CLI."""

import unittest

from controllers.radio.component_test.native_rds_cli import build_parser, configuration, main


class NativeRdsCliTest(unittest.TestCase):
    def test_defaults_and_dry_run(self):
        parser = build_parser()
        settings = configuration(parser.parse_args([]), parser)
        self.assertEqual(settings["frequency_hz"], 104_300_000)
        self.assertEqual(settings["sample_rate_hz"], 2_400_000)
        self.assertEqual(settings["gain_db"], 30.0)
        self.assertFalse(settings["audio"])
        self.assertEqual(main(["--dry-run"]), 0)

    def test_tuner_agc_and_device(self):
        parser = build_parser()
        args = parser.parse_args(["--tuner-agc", "--device-index", "1"])
        settings = configuration(args, parser)
        self.assertIsNone(settings["gain_db"])
        self.assertEqual(settings["device_index"], 1)

    def test_invalid_config(self):
        parser = build_parser()
        for args in (["--frequency", "0"], ["--seconds", "0"],
                     ["--report-seconds", "-1"], ["--device-index", "-1"],
                     ["--rf-warmup-seconds", "-2"]):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                configuration(parser.parse_args(args), parser)


if __name__ == "__main__":
    unittest.main()
