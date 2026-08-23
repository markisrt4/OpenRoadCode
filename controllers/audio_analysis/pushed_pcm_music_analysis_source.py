# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Music-analysis source for PCM supplied by an external transport."""
from __future__ import annotations
from collections import deque
from collections.abc import Callable
import io
import threading
import wave
import numpy as np
from hardware_io.audio.audio_capture_if import AudioFrame
from .audio_analysis import SpectrumAnalysisMode
from .music_analysis import MusicAnalyzer, MusicAnalysisState

class PushedPcmMusicAnalysisSource:
    def __init__(self, analyzer: MusicAnalyzer | None = None) -> None:
        self._analyzer=analyzer or MusicAnalyzer(spectrum_band_count=24);self._callback:Callable[[MusicAnalysisState],None]|None=None;self._running=False;self._recent:deque[tuple[int,np.ndarray]]=deque();self._recent_sample_count=0;self._recent_capacity_seconds=12.;self._lock=threading.RLock();self._latest:MusicAnalysisState|None=None
    @property
    def sensitivity(self)->float:return self._analyzer.sensitivity
    @property
    def calibrated(self)->bool:return self._analyzer.calibrated
    @property
    def spectrum_mode(self)->SpectrumAnalysisMode:return self._analyzer.spectrum_mode
    @property
    def buffered_audio_seconds(self)->float:
        with self._lock:return sum(samples.size/rate for rate,samples in self._recent if rate>0)
    @property
    def latest_state(self)->MusicAnalysisState|None:
        with self._lock:return self._latest
    def start(self,callback:Callable[[MusicAnalysisState],None])->None:
        with self._lock:self._callback=callback;self._running=True
    def stop(self)->None:
        with self._lock:self._running=False;self._callback=None
    def zeroize(self)->None:self._analyzer.begin_zeroize()
    def set_sensitivity(self,value:float)->None:self._analyzer.set_sensitivity(value)
    def set_spectrum_mode(self,mode:SpectrumAnalysisMode|str)->None:self._analyzer.set_spectrum_mode(mode)
    def push_frame(self,samples:tuple[float,...],sample_rate_hz:int)->MusicAnalysisState:
        if sample_rate_hz<=0:raise ValueError("sample_rate_hz must be positive")
        frame=AudioFrame(samples=samples,sample_rate_hz=sample_rate_hz);copied=np.asarray(samples,dtype=np.float64).copy();state=self._analyzer.analyze(frame)
        with self._lock:
            self._recent.append((sample_rate_hz,copied));self._recent_sample_count+=copied.size;limit=int(sample_rate_hz*self._recent_capacity_seconds)
            while self._recent and self._recent_sample_count-len(self._recent[0][1])>=limit:self._recent_sample_count-=len(self._recent.popleft()[1])
            self._latest=state;callback=self._callback if self._running else None
        if callback is not None:callback(state)
        return state
    def recent_audio_pcm16(self,seconds:float=6.0)->bytes:
        with self._lock:frames=list(self._recent)
        if not frames:return b""
        sample_rate=frames[-1][0];wanted=max(1,int(sample_rate*seconds));samples=np.concatenate([samples for _,samples in frames])[-wanted:];pcm=np.clip(samples,-1.0,1.0);return (pcm*32767.0).astype("<i2").tobytes()
    def recent_audio_wav(self,seconds:float=6.0)->bytes:
        with self._lock:frames=list(self._recent)
        if not frames:return b""
        sample_rate=frames[-1][0];pcm=self.recent_audio_pcm16(seconds);output=io.BytesIO()
        with wave.open(output,"wb") as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(sample_rate);wav.writeframes(pcm)
        return output.getvalue()
