# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native radio CLI validation tests, requiring no SDR or audio device."""

import contextlib
import io
import json
import unittest

from controllers.radio.component_test.native_radio_cli import (
    build_parser, channel_arg, configuration, main
)


class NativeRadioCliTest(unittest.TestCase):
    def test_dry_run_default_without_hardware(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--dry-run"]), 0)
        config = json.loads(output.getvalue())
        self.assertEqual(config["channels"][0]["mode"], "WFM")
        self.assertEqual(config["center_hz"], 104_300_000)

    def test_two_virtual_channels(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main([
                "--dry-run", "--center", "104300000",
                "--channel", "a:104100000:wfm",
                "--channel", "b:104500000:nfm",
                "--listen", "b",
            ]), 0)
        config = json.loads(output.getvalue())
        self.assertEqual(len(config["channels"]), 2)
        self.assertEqual(config["listen"], "b")

    def test_out_of_span_rejected(self):
        parser = build_parser()
        args = parser.parse_args([
            "--center", "104300000",
            "--channel", "outside:107000000:wfm",
        ])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                configuration(args, parser)

    def test_duplicate_channel_rejected(self):
        parser = build_parser()
        args = parser.parse_args([
            "--channel", "fm:104300000:wfm",
            "--channel", "fm:104500000:am",
        ])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                configuration(args, parser)

    def test_bad_channel_mode_rejected(self):
        with self.assertRaises(Exception):
            channel_arg("fm:104300000:ssb")


if __name__ == "__main__":
    unittest.main()
