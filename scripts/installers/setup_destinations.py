#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the optional Home/Work installer with the existing whiptail toolkit."""

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from common.navigation_data import navigation_data_root
from config.saved_destinations import SavedDestinationsConfig
from controllers.navigation.destination_setup_controller import DestinationSetupController
from controllers.navigation.sqlite_geocoder import SqliteGeocoder
from frontends.tui.destination_setup import run_destination_setup
from ui.navigation.destination_setup_ui_if import DestinationSetupUiIf


class WhiptailDestinationDialog(DestinationSetupUiIf):
    """Terminal presentation adapter; process execution only renders dialogs."""

    def _run(self, title, kind, prompt, arguments=()):
        result = subprocess.run(
            ["whiptail", "--output-fd", "1", "--title", title, kind, prompt,
             "20", "90", *arguments], stdout=subprocess.PIPE, text=True, check=False,
        )
        if result.returncode not in (0, 1, 255):
            raise RuntimeError("Unable to display installer dialog")
        return result

    def choose(self, title, prompt, choices):
        arguments = ["10"]
        for key, label in choices:
            arguments.extend((key, label))
        result = self._run(title, "--menu", prompt, arguments)
        return result.stdout if result.returncode == 0 else None

    def text(self, title, prompt, initial=""):
        result = self._run(title, "--inputbox", prompt, [initial])
        return result.stdout if result.returncode == 0 else None

    def confirm(self, title, prompt):
        return self._run(title, "--yesno", prompt).returncode == 0

    def notify(self, title, message):
        self._run(title, "--msgbox", message)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Configure user-owned Home/Work destinations")
    parser.add_argument("--config", type=Path, help="Override the user destinations TOML path")
    parser.add_argument("--search-db", type=Path, help="Override the local address database")
    arguments = parser.parse_args(argv)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Run address setup as the ORC user, without sudo.", file=sys.stderr)
        return 1
    if shutil.which("whiptail") is None:
        print("Address setup requires whiptail (provided by the host installer).", file=sys.stderr)
        return 1
    database = arguments.search_db or navigation_data_root() / "maps/search/openroadcode-search.sqlite"
    geocoder = None
    try:
        try:
            geocoder = SqliteGeocoder(database)
        except (OSError, sqlite3.Error):
            # Map data may be installed later; manual coordinates remain available.
            pass
        handler = DestinationSetupController(SavedDestinationsConfig(arguments.config), geocoder)
        run_destination_setup(handler, WhiptailDestinationDialog())
    finally:
        if geocoder is not None:
            geocoder.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
