# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from controllers.audio.music_analysis.music_analysis_types import (
    MusicAnalysisState,
    PercussionActivity,
)
from controllers.lighting.dummy_lighting_controller import DummyLightingController
from controllers.lighting.lighting_types import RgbColor
from controllers.lighting.music_reactive_lighting import (
    MusicReactiveLighting,
    MusicReactiveLightingMapper,
)


def test_mapper_uses_summary_bands_for_color_and_level_for_brightness() -> None:
    mapped = MusicReactiveLightingMapper().map(
        MusicAnalysisState(level=0.42, bass=1.0, mid=0.5, treble=0.25)
    )

    assert mapped.color == RgbColor(255, 128, 64)
    assert mapped.brightness_percent == 42


def test_mapper_percussion_can_drive_each_color_channel() -> None:
    mapped = MusicReactiveLightingMapper().map(
        MusicAnalysisState(
            level=1.0,
            percussion=PercussionActivity(kick=0.25, snare=0.5, cymbal=1.0),
        )
    )

    assert mapped.color == RgbColor(64, 128, 255)
    assert mapped.brightness_percent == 100


def test_mapper_clamps_values_and_maps_silence_to_black() -> None:
    mapper = MusicReactiveLightingMapper()

    silent = mapper.map(MusicAnalysisState())
    loud = mapper.map(MusicAnalysisState(level=2.0, bass=2.0, mid=-1.0))

    assert silent.color == RgbColor(0, 0, 0)
    assert silent.brightness_percent == 0
    assert loud.color == RgbColor(255, 0, 0)
    assert loud.brightness_percent == 100


def test_update_ignores_frames_while_controller_is_disconnected() -> None:
    controller = DummyLightingController()
    reactive = MusicReactiveLighting(controller, update_interval_seconds=0.0)

    commands = reactive.update(MusicAnalysisState(level=1.0, bass=1.0))

    assert commands == ()
    assert controller.current_state().color == RgbColor(255, 255, 255)


def test_update_applies_color_and_brightness_to_connected_controller() -> None:
    controller = DummyLightingController()
    controller.connect().result()
    reactive = MusicReactiveLighting(controller, update_interval_seconds=0.0)

    commands = reactive.update(MusicAnalysisState(level=0.6, treble=1.0))
    for command in commands:
        command.result()

    assert len(commands) == 2
    assert controller.current_state().color == RgbColor(0, 0, 255)
    assert controller.current_state().brightness_percent == 60


def test_update_rate_limits_transport_commands() -> None:
    now = [10.0]
    controller = DummyLightingController()
    controller.connect().result()
    reactive = MusicReactiveLighting(
        controller,
        update_interval_seconds=0.05,
        clock=lambda: now[0],
    )

    assert len(reactive.update(MusicAnalysisState(level=0.2, bass=1.0))) == 2
    now[0] = 10.02
    assert reactive.update(MusicAnalysisState(level=0.8, treble=1.0)) == ()
    assert controller.current_state().color == RgbColor(255, 0, 0)

    now[0] = 10.06
    assert len(reactive.update(MusicAnalysisState(level=0.8, treble=1.0))) == 2
    assert controller.current_state().color == RgbColor(0, 0, 255)


def test_update_skips_unchanged_output() -> None:
    controller = DummyLightingController()
    controller.connect().result()
    reactive = MusicReactiveLighting(controller, update_interval_seconds=0.0)
    analysis = MusicAnalysisState(level=0.5, mid=1.0)

    assert len(reactive.update(analysis)) == 2
    assert reactive.update(analysis) == ()


def test_reset_allows_same_output_to_be_reapplied() -> None:
    controller = DummyLightingController()
    controller.connect().result()
    reactive = MusicReactiveLighting(controller, update_interval_seconds=10.0)
    analysis = MusicAnalysisState(level=0.5, mid=1.0)

    assert len(reactive.update(analysis)) == 2
    reactive.reset()
    assert len(reactive.update(analysis)) == 2
