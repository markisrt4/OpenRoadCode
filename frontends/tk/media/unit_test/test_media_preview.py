# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import queue
import unittest
from unittest.mock import Mock, patch
from frontends.tk.media.media_preview import MediaPreview
from ui.media import MediaState


class MediaPreviewTest(unittest.TestCase):
    def preview(self):
        view = object.__new__(MediaPreview)
        view._closed = False
        view._url = "new"
        view._photo = None
        view._results = queue.SimpleQueue()
        view._handler = Mock()
        view._handler.read_state.return_value = MediaState(title="Current", artwork_uri="new")
        view._title, view._artist, view._caption, view._art = Mock(), Mock(), Mock(), Mock()
        view.after = Mock(return_value="timer")
        view.after_cancel = Mock()
        view._after = "timer"
        return view

    def test_stale_artwork_is_ignored(self):
        view = self.preview()
        view._results.put(("old", b"old png"))
        with patch("frontends.tk.media.media_preview.Image.open") as decode:
            view._refresh()
            decode.assert_not_called()
        view._title.configure.assert_called_once_with(text="Current")

    def test_hide_cancels_polling_and_stops_state_reads(self):
        view = self.preview()
        view.stop()
        view.stop()
        view._refresh()
        view.after_cancel.assert_called_once_with("timer")
        view._handler.read_state.assert_not_called()
