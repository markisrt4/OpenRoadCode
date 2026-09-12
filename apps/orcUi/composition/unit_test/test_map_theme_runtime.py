# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for ORC MapLibre theme generation."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.orcUi.map_theme_runtime import _default_data_root, install_map_style
from ui.theme import ThemeMode


class MapThemeRuntimeTest(unittest.TestCase):
    @patch.dict(os.environ, {"OPENROADCODE_DATA_ROOT": "/tmp/orc-map-data"}, clear=False)
    def test_explicit_data_root_environment_wins(self) -> None:
        self.assertEqual(_default_data_root(), Path("/tmp/orc-map-data"))

    @patch.dict(os.environ, {}, clear=True)
    @patch("apps.orcUi.map_theme_runtime.Path.is_dir", return_value=True)
    def test_deployed_linux_data_root_is_preferred(self, _is_dir) -> None:
        self.assertEqual(_default_data_root(), Path("/srv/openroadcode"))

    def test_dark_style_uses_known_good_semantic_palette(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            (data_root / "maps" / "styles").mkdir(parents=True)

            destination = install_map_style(ThemeMode.DARK, data_root)

            self.assertEqual(destination, data_root / "maps" / "styles" / "openroadcode.json")
            style = destination.read_text(encoding="utf-8")
            self.assertIn('"background-color":"#0b151b"', style)
            self.assertIn('"farmland","#2d3f35"', style)
            self.assertIn('"fill-color":"#103f56"', style)
            self.assertIn('"line-color":"#4c8297"', style)
            self.assertIn('"commercial","#493044"', style)
            self.assertIn('"hospital","#542f42"', style)
            self.assertIn('"school","#564d29"', style)
            self.assertIn('"poi-results":{"type":"geojson"', style)
            self.assertIn('"id":"poi-results-glow"', style)
            self.assertIn('"id":"poi-results-icon"', style)
            self.assertIn('"id":"poi-results-label"', style)


if __name__ == "__main__":
    unittest.main()
