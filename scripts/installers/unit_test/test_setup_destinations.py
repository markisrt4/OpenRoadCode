# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import contextlib
import io

from scripts.installers.setup_destinations import WhiptailDestinationDialog, main


class SetupDestinationsInstallerTest(unittest.TestCase):
    def test_dialog_adapter_uses_output_fd_and_preserves_input(self):
        dialog = WhiptailDestinationDialog("/termux/bin/dialog")
        with patch("scripts.installers.setup_destinations.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "123 Main St")
            self.assertEqual(dialog.text("Home", "Address", "Existing"), "123 Main St")
            self.assertEqual(run.call_args.args[0][:3], ["/termux/bin/dialog", "--output-fd", "1"])

    def test_termux_selects_dialog_when_whiptail_is_missing(self):
        with patch("scripts.installers.setup_destinations.os.geteuid", return_value=1000), \
             patch("scripts.installers.setup_destinations.shutil.which", side_effect=[None, "/termux/bin/dialog"]), \
             patch("scripts.installers.setup_destinations.SqliteGeocoder") as geocoder, \
             patch("scripts.installers.setup_destinations.run_destination_setup"), \
             patch("scripts.installers.setup_destinations.WhiptailDestinationDialog") as adapter:
            self.assertEqual(main([]), 0)
            adapter.assert_called_once_with("/termux/bin/dialog")
            geocoder.return_value.close.assert_called_once()

    def test_missing_termux_dialog_has_correct_install_hint(self):
        output = io.StringIO()
        with patch("scripts.installers.setup_destinations.os.geteuid", return_value=1000), \
             patch("scripts.installers.setup_destinations.shutil.which", return_value=None), \
             patch.dict("os.environ", {"TERMUX_VERSION": "test"}), \
             contextlib.redirect_stderr(output):
            self.assertEqual(main([]), 1)
        self.assertIn("pkg install dialog", output.getvalue())

    def test_cancelled_dialog_is_not_empty_input(self):
        dialog = WhiptailDestinationDialog()
        with patch("scripts.installers.setup_destinations.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 1, "")
            self.assertIsNone(dialog.text("Home", "Address", "Existing"))
            run.return_value = subprocess.CompletedProcess([], 0, "")
            self.assertEqual(dialog.text("Home", "Address", "Existing"), "")
            self.assertEqual(run.call_args.args[0][-1], "Existing")

    def test_cancellation_with_missing_database_has_no_filesystem_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "destinations.toml"
            dialog = Mock()
            dialog.choose.return_value = None
            with patch("scripts.installers.setup_destinations.os.geteuid", return_value=1000), \
                 patch("scripts.installers.setup_destinations.shutil.which", return_value="/usr/bin/whiptail"), \
                 patch("scripts.installers.setup_destinations.WhiptailDestinationDialog", return_value=dialog):
                result = main(["--config", str(path), "--search-db", str(Path(directory) / "missing.sqlite")])
            self.assertEqual(result, 0)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_composition_closes_geocoder_when_presentation_fails(self):
        geocoder = Mock()
        with patch("scripts.installers.setup_destinations.os.geteuid", return_value=1000), \
             patch("scripts.installers.setup_destinations.shutil.which", return_value="/usr/bin/whiptail"), \
             patch("scripts.installers.setup_destinations.SqliteGeocoder", return_value=geocoder), \
             patch("scripts.installers.setup_destinations.run_destination_setup", side_effect=RuntimeError("terminal unavailable")):
            with self.assertRaises(RuntimeError):
                main([])
        geocoder.close.assert_called_once()
