# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Linux system-audio adapter for the shared music-analysis subsystem."""
from __future__ import annotations
from dataclasses import asdict
import threading,time
from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.audio_analysis.music_analysis_presenter import MusicAnalysisPresenter
from controllers.audio_analysis.pcm_music_analysis_source import PcmMusicAnalysisSource
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture
from ui.music_analysis import MusicAnalysisUiIf,MusicAnalysisUiState
class WebLinuxAudioAnalysisSession(MusicAnalysisUiIf):
 def __init__(self,source:PcmMusicAnalysisSource|None=None)->None:
  self.source=source or PcmMusicAnalysisSource(PipeWireAudioCapture());self._lock=threading.RLock();self._state=None;self._ui_state=None;self._running=False;self._error=None;self.presenter=MusicAnalysisPresenter(self.source);self.presenter.attach_ui(self)
 def set_analysis_state(self,state:MusicAnalysisState)->None:
  with self._lock:self._state=state
 def set_analysis_ui_state(self,state:MusicAnalysisUiState)->None:
  with self._lock:self._ui_state=state
 def start(self)->dict[str,object]:
  with self._lock:
   if self._running:return self.state()
   self._error=None
  try:self.presenter.start();self._running=True
  except Exception as exc:self._error=str(exc);raise
  return self.state()
 def stop(self)->dict[str,object]:self.presenter.stop();self._running=False;return self.state()
 def zeroize(self)->dict[str,object]:self.presenter.request_zeroize();return self.state()
 def set_sensitivity(self,value:float)->dict[str,object]:self.presenter.request_sensitivity(value);return self.state()
 def set_spectrum_mode(self,value:str)->dict[str,object]:self.source.set_spectrum_mode(value);return self.state()
 def state(self)->dict[str,object]:
  with self._lock:state=self._state;ui=self._ui_state;running=self._running;error=self._error
  data={"audio":{"level":0.0,"peak":0.0,"bass":0.0,"mid":0.0,"treble":0.0,"spectrum":[]},"percussion":{"kick":0.0,"snare":0.0,"tom_low":0.0,"tom_mid":0.0,"tom_high":0.0,"cymbal":0.0},"calibrated":self.source.calibrated,"sensitivity":self.source.sensitivity} if state is None else asdict(state)
  if state is not None:data["audio"]["spectrum"]=list(state.audio.spectrum)
  data["spectrum_mode"]=self.source.spectrum_mode.value
  if ui is not None:data["ui"]={"status":ui.status.value,"calibrated":ui.calibrated,"sensitivity":ui.sensitivity,"error":ui.error}
  data.update(running=running,source="linux-pipewire",error=error,timestamp=time.time());return data
