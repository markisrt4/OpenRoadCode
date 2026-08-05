from __future__ import annotations

import unittest

from apps.carUi.system.volume_manager import VolumeManager


class FakeAudioController:
    maximum_level = 20

    def __init__(self, level: int = 0) -> None:
        self.level = level
        self.muted = False

    def get_volume_level(self) -> int:
        return self.level

    def volume_up(self) -> int:
        self.level = min(self.maximum_level, self.level + 1)
        return self.level

    def volume_down(self) -> int:
        self.level = max(0, self.level - 1)
        return self.level

    def is_muted(self) -> bool:
        return self.muted

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted


class VolumeManagerTest(unittest.TestCase):
    def test_maps_twenty_audio_levels_to_eight_indicator_bars(self) -> None:
        expected = {
            0: 0,
            1: 1,
            5: 2,
            10: 4,
            15: 6,
            20: 8,
        }

        for audio_level, indicator_level in expected.items():
            with self.subTest(audio_level=audio_level):
                self.assertEqual(
                    indicator_level,
                    VolumeManager.indicator_level(
                        audio_level,
                        maximum_level=20,
                        indicator_steps=8,
                    ),
                )

    def test_volume_change_publishes_mapped_indicator_level(self) -> None:
        audio = FakeAudioController(level=9)
        displayed: list[int] = []
        statuses: list[str] = []
        manager = VolumeManager(
            audio_controller=audio,
            indicator_steps=8,
            set_volume_level=displayed.append,
            set_muted=lambda _muted: None,
            set_status=statuses.append,
        )

        manager.volume_up()

        self.assertEqual(10, audio.level)
        self.assertEqual([4], displayed)
        self.assertEqual(["Volume up"], statuses)

    def test_get_indicator_level_maps_current_audio_level(self) -> None:
        manager = VolumeManager(
            audio_controller=FakeAudioController(level=20),
            indicator_steps=8,
            set_volume_level=lambda _level: None,
            set_muted=lambda _muted: None,
            set_status=lambda _status: None,
        )

        self.assertEqual(8, manager.get_indicator_level())

    def test_toggle_mute_publishes_state_and_status(self) -> None:
        audio = FakeAudioController()
        muted_states: list[bool] = []
        statuses: list[str] = []
        manager = VolumeManager(
            audio_controller=audio,
            indicator_steps=8,
            set_volume_level=lambda _level: None,
            set_muted=muted_states.append,
            set_status=statuses.append,
        )

        manager.toggle_mute()
        manager.toggle_mute()

        self.assertEqual([True, False], muted_states)
        self.assertEqual(["Volume muted", "Volume unmuted"], statuses)


if __name__ == "__main__":
    unittest.main()
