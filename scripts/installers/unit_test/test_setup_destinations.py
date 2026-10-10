# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.installers.setup_destinations import WhiptailDestinationDialog, main


class SetupDestinationsInstallerTest(unittest.TestCase):
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
