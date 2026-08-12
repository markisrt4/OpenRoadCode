# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for adapting media volume to system audio."""

import unittest
from unittest.mock import Mock

from controllers.audio import MediaVolumeHandler


class MediaVolumeHandlerTest(unittest.TestCase):
    def test_normalized_volume_is_mapped_to_audio_levels(self) -> None:
        audio = Mock()
        audio.maximum_level = 20
        handler = MediaVolumeHandler(audio)

        handler.request_volume(65)

        audio.set_volume_level.assert_called_once_with(13)


if __name__ == "__main__":
    unittest.main()
