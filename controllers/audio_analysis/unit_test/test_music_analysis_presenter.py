# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.audio_analysis.audio_analysis import SpectrumAnalysisMode
from controllers.audio_analysis.music_analysis_presenter import MusicAnalysisPresenter
from controllers.audio_analysis.audio_analysis import AudioAnalysisState
from controllers.audio_analysis.music_analysis import MusicAnalysisState, PercussionState


class FakeSource:
    def __init__(self):
        self.sensitivity=1.0;self.calibrated=False;self.spectrum_mode=SpectrumAnalysisMode.HYBRID;self.callback=None
    def start(self,callback):self.callback=callback
    def stop(self):pass
    def zeroize(self):self.calibrated=False
    def set_sensitivity(self,value):self.sensitivity=value
    def set_spectrum_mode(self,mode):self.spectrum_mode=mode if isinstance(mode,SpectrumAnalysisMode) else SpectrumAnalysisMode(mode)
    def recent_audio_pcm16(self,seconds=6.0):return b''


class FakeUi:
    def __init__(self):self.analysis=[];self.states=[]
    def set_analysis_state(self,state):self.analysis.append(state)
    def set_analysis_ui_state(self,state):self.states.append(state)


def test_presenter_publishes_spectrum_mode_changes():
    source=FakeSource();ui=FakeUi();presenter=MusicAnalysisPresenter(source);presenter.attach_ui(ui)
    presenter.request_spectrum_mode(SpectrumAnalysisMode.NATIVE)
    assert source.spectrum_mode is SpectrumAnalysisMode.NATIVE
    assert ui.states[-1].spectrum_mode is SpectrumAnalysisMode.NATIVE


def test_presenter_publishes_sensitivity_changes():
    source=FakeSource();ui=FakeUi();presenter=MusicAnalysisPresenter(source);presenter.attach_ui(ui)
    presenter.request_sensitivity(1.35)
    assert source.sensitivity == 1.35
    assert ui.states[-1].sensitivity == 1.35


def test_zeroize_enters_semantic_zeroizing_state():
    source=FakeSource();ui=FakeUi();presenter=MusicAnalysisPresenter(source);presenter.attach_ui(ui);presenter.start()
    presenter.request_zeroize()
    assert ui.states[-1].status.value == 'zeroizing'
    assert ui.states[-1].calibrated is False


def test_audio_frames_are_coalesced_while_ui_update_is_pending():
    source=FakeSource();ui=FakeUi();pending=[];presenter=MusicAnalysisPresenter(source,dispatch=pending.append);presenter.attach_ui(ui);presenter.start()
    first=MusicAnalysisState(AudioAnalysisState(.1,.1,.1,.1,.1),PercussionState(),False,1.)
    latest=MusicAnalysisState(AudioAnalysisState(.8,.8,.8,.8,.8),PercussionState(),False,1.)
    source.callback(first);source.callback(latest)
    assert len(pending) == 1
    pending.pop()()
    assert ui.analysis == [latest]


def test_zeroize_completion_survives_coalesced_frames():
    source=FakeSource();ui=FakeUi();pending=[];presenter=MusicAnalysisPresenter(source,dispatch=pending.append);presenter.attach_ui(ui);presenter.start();presenter.request_zeroize()
    before=MusicAnalysisState(AudioAnalysisState(.1,.1,.1,.1,.1),PercussionState(),False,1.)
    calibrated=MusicAnalysisState(AudioAnalysisState(.1,.1,.1,.1,.1),PercussionState(),True,1.)
    source.callback(before);source.callback(calibrated);pending.pop()()
    assert ui.states[-1].status.value == "active"
