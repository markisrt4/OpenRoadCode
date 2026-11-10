# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hardware-free CLI configuration checks for stereo and RDS."""

import unittest

from controllers.radio.component_test.native_radio_cli import build_parser, configuration, main


class NativeRadioRdsCliTest(unittest.TestCase):
    def test_rds_requires_stereo(self):
        parser = build_parser()
        with self.assertRaises(SystemExit) as context:
            configuration(parser.parse_args(["--rds"]), parser)
        self.assertEqual(context.exception.code, 2)

    def test_rds_stereo_configuration(self):
        parser = build_parser()
        receiver, center, listen = configuration(
            parser.parse_args(["--stereo", "--rds"]), parser)
        self.assertEqual(center, 104_300_000)
        self.assertEqual(listen, "fm")
        self.assertIn("fm", receiver.rds_status)

    def test_dry_run_needs_no_sdr(self):
        self.assertEqual(main(["--stereo", "--rds", "--dry-run"]), 0)


if __name__ == "__main__":
    unittest.main()
