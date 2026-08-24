# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
import tempfile
import unittest

from tools.map_builder.builder.style import install_style
from tools.map_builder.builder.validate import validate_style

TEMPLATE = Path(__file__).parents[1] / "templates/openroadcode-style.json"

class StyleTests(unittest.TestCase):
    def test_style_round_trip_and_required_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "style.json"
            install_style(TEMPLATE, destination)
            validate_style(destination)

if __name__ == "__main__": unittest.main()
