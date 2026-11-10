# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import unittest
from threading import Event, get_ident
from unittest.mock import Mock
from controllers.spotify.media_preview_controller import MediaPreviewController
from ui.media import MediaState


class MediaPreviewControllerTest(unittest.TestCase):
    def test_snapshot_does_not_load_artwork(self):
        artwork = Mock()
        state = MediaState(title="Track")
        controller = MediaPreviewController(lambda: state, artwork)
        try:
            self.assertIs(controller.read_state(), state)
            artwork.assert_not_called()
        finally:
            controller.close()

    def test_artwork_runs_on_worker_and_returns_bytes(self):
        main = get_ident()
        finished = Event()
        result = []
        def load(url):
            self.assertNotEqual(get_ident(), main)
            return b"png"
        controller = MediaPreviewController(MediaState, load)
        try:
            controller.request_artwork("cover", lambda data: (result.append(data), finished.set()))
            self.assertTrue(finished.wait(2))
            self.assertEqual(result, [b"png"])
        finally:
            controller.close()

    def test_offline_artwork_does_not_access_loader(self):
        artwork = Mock()
        finished = Event()
        results = []
        controller = MediaPreviewController(MediaState, artwork, online_allowed=lambda: False)
        try:
            controller.request_artwork("cover", lambda data: (results.append(data), finished.set()))
            self.assertTrue(finished.wait(2))
            self.assertEqual(results, [None])
            artwork.assert_not_called()
        finally:
            controller.close()

    def test_new_track_discards_old_completion(self):
        started, release, finished = Event(), Event(), Event()
        results = []
        def load(url):
            if url == "old":
                started.set()
                release.wait(2)
            return url.encode()
        controller = MediaPreviewController(MediaState, load)
        try:
            controller.request_artwork("old", results.append)
            self.assertTrue(started.wait(2))
            controller.request_artwork("new", lambda data: (results.append(data), finished.set()))
            release.set()
            self.assertTrue(finished.wait(2))
            self.assertEqual(results, [b"new"])
        finally:
            release.set()
            controller.close()
        callback = Mock()
        controller.request_artwork("closed", callback)
        callback.assert_not_called()
