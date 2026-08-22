# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Music analysis source backed by any PCM ``AudioCaptureIf`` implementation."""
from __future__ import annotations
from collections import deque
from collections.abc import Callable
import threading
import numpy as np
from hardware_io.audio.audio_capture_if import AudioCaptureIf
from .audio_analysis import SpectrumAnalysisMode
from .music_analysis import MusicAnalyzer, MusicAnalysisState

class PcmMusicAnalysisSource:
    def __init__(self,capture:AudioCaptureIf,analyzer:MusicAnalyzer|None=None)->None:
        self._capture=capture;self._analyzer=analyzer or MusicAnalyzer(spectrum_band_count=24);self._callback:Callable[[MusicAnalysisState],None]|None=None;self._running=False;self._thread:threading.Thread|None=None;self._recent:deque[tuple[int,np.ndarray]]=deque(maxlen=512);self._lock=threading.RLock()
    @property
    def sensitivity(self)->float:return self._analyzer.sensitivity
    @property
    def calibrated(self)->bool:return self._analyzer.calibrated
    @property
    def spectrum_mode(self)->SpectrumAnalysisMode:return self._analyzer.spectrum_mode
    def start(self,callback:Callable[[MusicAnalysisState],None])->None:
        with self._lock:
            if self._running:self._callback=callback;return
            self._callback=callback;self._capture.start();self._running=True;self._thread=threading.Thread(target=self._run,name="music-analysis-source",daemon=True);self._thread.start()
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
    def _run(self)->None:
        try:
            while True:
                with self._lock:
                    if not self._running:return
                    callback=self._callback
                frame=self._capture.read();samples=np.asarray(frame.samples,dtype=np.float64).copy()
                with self._lock:self._recent.append((frame.sample_rate_hz,samples))
                state=self._analyzer.analyze(frame)
                if callback is not None:callback(state)
        finally:
            with self._lock:self._running=False
