from __future__ import annotations

import unittest

from apps.carUi.system.volume_manager import VolumeManager
from ui.system import VolumeUiStub


class FakeAudioController:
    maximum_level = 20

    def __init__(self, level: int = 0) -> None:
        self.level = level
        self.muted = False

    def get_volume_level(self) -> int:
        return self.level

    def set_volume_level(self, level: int) -> int:
        self.level = max(0, min(self.maximum_level, level))
        return self.level

    def volume_up(self) -> int:
        return self.set_volume_level(self.level + 1)

    def volume_down(self) -> int:
        return self.set_volume_level(self.level - 1)

    def is_muted(self) -> bool:
        return self.muted

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted


class RecordingVolumeUi(VolumeUiStub):
    def __init__(self) -> None:
        self.volumes: list[float | None] = []
        self.muted_states: list[bool | None] = []

    def set_volume(self, volume_percent: float | None) -> None:
        self.volumes.append(volume_percent)

    def set_muted(self, muted: bool | None) -> None:
        self.muted_states.append(muted)


class VolumeManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.audio = FakeAudioController(level=10)
        self.volume_ui = RecordingVolumeUi()
        self.statuses: list[str] = []
        self.manager = VolumeManager(
            audio_controller=self.audio,
            volume_ui=self.volume_ui,
            set_status=self.statuses.append,
        )

    def test_refresh_publishes_normalized_volume_and_mute_state(self) -> None:
        self.manager.refresh()

        self.assertEqual(self.volume_ui.volumes, [50.0])
        self.assertEqual(self.volume_ui.muted_states, [False])

    def test_volume_requests_publish_normalized_result(self) -> None:
        self.manager.request_volume(75.0)
        self.manager.request_volume_up()

        self.assertEqual(self.audio.level, 16)
        self.assertEqual(self.volume_ui.volumes, [75.0, 80.0])

    def test_explicit_mute_request_is_idempotent(self) -> None:
        self.manager.request_mute(True)
        self.manager.request_mute(True)
        self.manager.request_mute(False)

        self.assertEqual(self.volume_ui.muted_states, [True, True, False])


if __name__ == "__main__":
    unittest.main()
