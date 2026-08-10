"""Tests for pactl development-host audio control."""

import unittest
from unittest.mock import patch

from controllers.audio import PactlAudioController


class PactlAudioControllerTest(unittest.TestCase):
    def test_parses_default_sink_volume(self) -> None:
        controller = PactlAudioController(steps=20)
        with patch.object(
            controller,
            "_run",
            return_value="Volume: front-left: 41263 / 63% / -12.06 dB",
        ):
            self.assertEqual(13, controller.get_volume_level())

    def test_sets_normalized_default_sink_volume(self) -> None:
        controller = PactlAudioController(steps=20)
        with patch.object(controller, "_run") as run:
            self.assertEqual(13, controller.set_volume_level(13))
        run.assert_called_once_with(
            ["set-sink-volume", "@DEFAULT_SINK@", "65%"]
        )


if __name__ == "__main__":
    unittest.main()
