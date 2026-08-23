# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for ownership and cleanup of assembled Car UI dependencies."""

import unittest

from apps.carUi.car_ui_dependencies import CarUiDependencies


class RecordingResource:
    def __init__(self, name: str, events: list[str], fail: bool = False) -> None:
        self.name = name
        self.events = events
        self.fail = fail

    def close(self) -> None:
        self.events.append(f"close:{self.name}")
        if self.fail:
            raise RuntimeError(self.name)

    def stop(self) -> None:
        self.events.append(f"stop:{self.name}")
        if self.fail:
            raise RuntimeError(self.name)

    def stop_video(self) -> None:
        self.stop()


class CarUiDependenciesTest(unittest.TestCase):
    def test_close_releases_owned_resources_in_order_and_only_once(self) -> None:
        events: list[str] = []
        dependencies = CarUiDependencies(
            runtime=RecordingResource("runtime", events),  # type: ignore[arg-type]
            position_source=RecordingResource("position", events),  # type: ignore[arg-type]
            audio_controller=object(),  # type: ignore[arg-type]
            spotify_controller=object(),  # type: ignore[arg-type]
            spotify_image_cache=object(),  # type: ignore[arg-type]
            spotify_lyrics_client=object(),  # type: ignore[arg-type]
            spotify_music_video_controller=RecordingResource(
                "music-video", events
            ),  # type: ignore[arg-type]
            netflix_player=RecordingResource(
                "netflix", events
            ),  # type: ignore[arg-type]
            youtube_player=RecordingResource(
                "youtube", events
            ),  # type: ignore[arg-type]
            lighting_controller=RecordingResource("lighting", events),  # type: ignore[arg-type]
            rotary_encoders=(
                RecordingResource("encoder-0", events),  # type: ignore[arg-type]
                RecordingResource("encoder-1", events),  # type: ignore[arg-type]
            ),
            volume_encoder_index=0,
            music_visualizer=RecordingResource(
                "music-visualizer", events
            ),  # type: ignore[arg-type]
        )

        dependencies.close()
        dependencies.close()

        self.assertEqual(
            events,
            [
                "stop:encoder-0",
                "stop:encoder-1",
                "close:music-visualizer",
                "close:runtime",
                "stop:music-video",
                "stop:netflix",
                "stop:youtube",
                "close:lighting",
                "stop:position",
            ],
        )

    def test_cleanup_continues_after_one_resource_fails(self) -> None:
        events: list[str] = []
        dependencies = CarUiDependencies(
            runtime=RecordingResource("runtime", events),  # type: ignore[arg-type]
            position_source=RecordingResource("position", events),  # type: ignore[arg-type]
            audio_controller=object(),  # type: ignore[arg-type]
            spotify_controller=object(),  # type: ignore[arg-type]
            spotify_image_cache=object(),  # type: ignore[arg-type]
            spotify_lyrics_client=object(),  # type: ignore[arg-type]
            spotify_music_video_controller=RecordingResource(
                "music-video", events
            ),  # type: ignore[arg-type]
            netflix_player=RecordingResource(
                "netflix", events
            ),  # type: ignore[arg-type]
            youtube_player=RecordingResource(
                "youtube", events
            ),  # type: ignore[arg-type]
            lighting_controller=RecordingResource("lighting", events),  # type: ignore[arg-type]
            rotary_encoders=(
                RecordingResource("encoder", events, fail=True),  # type: ignore[arg-type]
            ),
            volume_encoder_index=0,
            music_visualizer=RecordingResource(
                "music-visualizer", events
            ),  # type: ignore[arg-type]
        )

        with self.assertLogs(
            "apps.carUi.car_ui_dependencies", level="ERROR"
        ):
            dependencies.close()

        self.assertIn("close:runtime", events)
        self.assertIn("close:lighting", events)
        self.assertIn("stop:position", events)


if __name__ == "__main__":
    unittest.main()
