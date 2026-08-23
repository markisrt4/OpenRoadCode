# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.audio_analysis.audio_analysis import AudioAnalysisState
from controllers.audio_analysis.music_analysis import MusicAnalysisState, PercussionState
from controllers.music_lighting import MusicLightingController, MusicLightingPatternId


def _analysis() -> MusicAnalysisState:
    return MusicAnalysisState(
        audio=AudioAnalysisState(level=.7, peak=.8, bass=.9, mid=.5, treble=.3, spectrum=(.2,.8,.4)),
        percussion=PercussionState(kick=.9, snare=.4),
        calibrated=True,
        sensitivity=1.0,
    )


def test_enabled_callback_tracks_controller_state():
    enabled=[]
    controller=MusicLightingController(enabled_callback=enabled.append)
    controller.request_enabled(True)
    controller.request_enabled(False)
    assert enabled == [True, False]
    assert controller.state.enabled is False


def test_disabled_controller_does_not_emit_output():
    outputs=[]
    controller=MusicLightingController(output_callback=outputs.append)
    controller.update_analysis(_analysis())
    assert outputs == []


def test_enabled_controller_emits_pattern_output():
    outputs=[]
    controller=MusicLightingController(output_callback=outputs.append)
    controller.request_pattern(MusicLightingPatternId.BEAT_PULSE)
    controller.request_enabled(True)
    controller.update_analysis(_analysis())
    assert len(outputs) == 1
    assert 0.0 <= outputs[0].brightness <= 1.0


def test_brightness_limit_caps_rendered_output():
    outputs=[]
    controller=MusicLightingController(output_callback=outputs.append)
    controller.request_enabled(True)
    controller.request_brightness_limit(25)
    controller.update_analysis(_analysis())
    assert outputs
    assert outputs[-1].brightness <= .25
