# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from apps.orcUi.music_visualizer_session import MusicVisualizerSession
from controllers.audio.music_analysis.music_analysis_types import MusicAnalysisState


class _Pipeline:
    def __init__(self, callback):
        self.callback = callback
        self.is_running = False
        self.is_zeroized = False
        self.zeroize_started = False
        self.zeroize_finished = False
        self.zeroize_cleared = False

    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def start_zeroize(self):
        self.zeroize_started = True

    def finish_zeroize(self):
        self.zeroize_finished = True
        self.is_zeroized = True

    def clear_zeroize(self):
        self.zeroize_cleared = True
        self.is_zeroized = False


def test_session_translates_analysis_state_and_owns_pipeline_lifecycle():
    frames = []
    pipelines = []

    def factory(callback):
        pipeline = _Pipeline(callback)
        pipelines.append(pipeline)
        return pipeline

    session = MusicVisualizerSession(factory, frames.append)
    pipeline = pipelines[0]

    assert not session.is_running
    session.start()
    assert session.is_running

    pipeline.callback(
        MusicAnalysisState(
            level=0.75,
            bass=0.8,
            mid=0.5,
            treble=0.25,
            spectrum=(0.1, 0.2, 0.3),
        )
    )

    assert len(frames) == 1
    assert frames[0].level == 0.75
    assert frames[0].bass == 0.8
    assert frames[0].mid == 0.5
    assert frames[0].treble == 0.25
    assert frames[0].spectrum == (0.1, 0.2, 0.3)

    session.start_zeroize()
    session.finish_zeroize()
    assert pipeline.zeroize_started
    assert pipeline.zeroize_finished
    assert session.is_zeroized

    session.clear_zeroize()
    assert pipeline.zeroize_cleared
    assert not session.is_zeroized

    session.close()
    assert not session.is_running
