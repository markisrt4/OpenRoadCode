# SPDX-License-Identifier: MIT
"""Hardware-free renderer configuration tests."""

import unittest

from ui.radio.radio_visualization_config import (
    RadioRenderer,
    RadioVisualizationConfig,
    select_renderer,
)


class RadioVisualizationConfigTest(unittest.TestCase):
    def test_auto_uses_tk_when_opengl_unavailable(self):
        self.assertEqual(
            select_renderer(RadioVisualizationConfig(), opengl_available=False),
            RadioRenderer.TK,
        )

    def test_auto_prefers_opengl_when_available(self):
        self.assertEqual(
            select_renderer(RadioVisualizationConfig(), opengl_available=True),
            RadioRenderer.OPENGL,
        )

    def test_explicit_tk_remains_tk(self):
        self.assertEqual(
            select_renderer(
                RadioVisualizationConfig(renderer=RadioRenderer.TK), opengl_available=True
            ),
            RadioRenderer.TK,
        )

    def test_explicit_opengl_reports_unavailable(self):
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            select_renderer(
                RadioVisualizationConfig(renderer=RadioRenderer.OPENGL), opengl_available=False
            )

    def test_invalid_config_rejected(self):
        for options in (
            {"max_fps": 0},
            {"max_fps": 61},
            {"waterfall_rows": 29},
            {"waterfall_rows": 1025},
            {"palette": "invalid"},
        ):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    RadioVisualizationConfig(**options)


if __name__ == "__main__":
    unittest.main()
