# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Music analysis source backed by any PCM ``AudioCaptureIf`` implementation."""
from __future__ import annotations
from collections import deque
from collections.abc import Callable
import io
import threading
import wave
import numpy as np
from hardware_io.audio.audio_capture_if import AudioCaptureIf, AudioFrame
from .audio_analysis import SpectrumAnalysisMode
from .music_analysis import MusicAnalyzer, MusicAnalysisState

class PcmMusicAnalysisSource:
    def __init__(self,capture:AudioCaptureIf,analyzer:MusicAnalyzer|None=None)->None:
        self._capture=capture;self._analyzer=analyzer or MusicAnalyzer(spectrum_band_count=24);self._callback:Callable[[MusicAnalysisState],None]|None=None;self._running=False;self._thread:threading.Thread|None=None;self._recent:deque[tuple[int,np.ndarray]]=deque();self._recent_sample_count=0;self._recent_capacity_seconds=12.;self._lock=threading.RLock()
    @property
    def sensitivity(self)->float:return self._analyzer.sensitivity
    @property
    def calibrated(self)->bool:return self._analyzer.calibrated
    @property
    def spectrum_mode(self)->SpectrumAnalysisMode:return self._analyzer.spectrum_mode
    @property
    def buffered_audio_seconds(self)->float:
        with self._lock:return sum(samples.size/rate for rate,samples in self._recent if rate>0)
    def start(self,callback:Callable[[MusicAnalysisState],None])->None:
        with self._lock:
            if self._running:self._callback=callback;return
            self._recent.clear();self._recent_sample_count=0;self._callback=callback;self._capture.start();self._running=True;self._thread=threading.Thread(target=self._run,name="music-analysis-source",daemon=True);self._thread.start()
    def stop(self)->None:
        with self._lock:self._running=False
        self._capture.stop();thread=self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():thread.join(timeout=1.0)
        self._thread=None
    def zeroize(self)->None:self._analyzer.begin_zeroize()
    def set_sensitivity(self,value:float)->None:self._analyzer.set_sensitivity(value)
    def set_spectrum_mode(self,mode:SpectrumAnalysisMode|str)->None:self._analyzer.set_spectrum_mode(mode)
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
    def _run(self)->None:
        try:
            while True:
                with self._lock:
                    if not self._running:return
                    callback=self._callback
                frame=self._capture.read();self._buffer_audio_frame(frame)
                state=self._analyzer.analyze(frame)
                if callback is not None:callback(state)
        finally:
            with self._lock:self._running=False
    def _buffer_audio_frame(self,frame:AudioFrame)->None:
        samples=np.asarray(frame.samples,dtype=np.float64);fresh_count=frame.new_sample_count if frame.new_sample_count is not None else samples.size;fresh=samples[-max(0,min(samples.size,fresh_count)):].copy()
        with self._lock:
            self._recent.append((frame.sample_rate_hz,fresh));self._recent_sample_count+=fresh.size;limit=int(frame.sample_rate_hz*self._recent_capacity_seconds)
            while self._recent and self._recent_sample_count-len(self._recent[0][1])>=limit:self._recent_sample_count-=len(self._recent.popleft()[1])
