# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Radio source illustrations require no X11 server or radio hardware."""

import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.radio_source_icon import draw_source_scene


class RadioSourceSceneTest(unittest.TestCase):
    def test_sources_have_distinct_explanations_and_replace_old_art(self):
        theme = Mock()
        for kind, caption in (("rf", "AIRWAVES  ›  SDR  ›  AUDIO"),
                              ("stream", "INTERNET  ›  STATION  ›  AUDIO")):
            with self.subTest(kind=kind):
                canvas = Mock()
                canvas.winfo_rgb.return_value = (8192, 8192, 8192)
                draw_source_scene(canvas, icon_kind=kind, accent="#4488cc",
                                  theme=theme, width=320, height=96)
                canvas.delete.assert_called_once_with("all")
                self.assertEqual(canvas.create_text.call_args.kwargs["text"], caption)
                self.assertEqual(canvas.create_rectangle.call_count, 32)

    def test_unallocated_canvas_does_not_draw(self):
        canvas = Mock()
        draw_source_scene(canvas, icon_kind="rf", accent="#4488cc",
                          theme=Mock(), width=1, height=1)
        canvas.create_rectangle.assert_not_called()
        canvas.create_line.assert_not_called()


if __name__ == "__main__":
    unittest.main()
