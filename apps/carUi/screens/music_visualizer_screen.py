# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Car UI music visualizer destination."""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from controllers.audio_analysis.music_analysis import MusicAnalyzer
from controllers.audio_analysis.music_visualizer_presenter import MusicVisualizerPresenter
from controllers.cache.persistent_cache import PersistentCache
from controllers.song_recognition import AcrCloudConfig, AcrCloudSongRecognizer, SongMetadataCache, UnconfiguredSongRecognizer
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture
from ui.music_visualizer import SongRecognitionUiState
from ui.screen_ui_if import ScreenId

LOGGER = logging.getLogger(__name__)


class MusicVisualizerScreen(CarUiScreen):
    """Compose native music services around toolkit-neutral UI contracts."""

    def __init__(self, host: TkScreenHostIf, *, create_menu_tile: MenuTileFactory, back_action) -> None:
        super().__init__(host, ScreenId("music_visualizer"), create_menu_tile)
        self._back_action=back_action;self._capture=None;self._analyzer=None;self._presenter=None;self._panel=None;self._running=False;self._generation=0
        self._recognition_lock=threading.Lock();self._recognizer=self._create_recognizer()
        self._metadata_cache=SongMetadataCache(PersistentCache(Path("~/.cache/openroadcode/song_recognition").expanduser(),suffix=".json"))

    @staticmethod
    def _create_recognizer():
        host=os.environ.get("ACRCLOUD_HOST","").strip();key=os.environ.get("ACRCLOUD_ACCESS_KEY","").strip();secret=os.environ.get("ACRCLOUD_ACCESS_SECRET","").strip()
        return AcrCloudSongRecognizer(AcrCloudConfig(host,key,secret)) if host and key and secret else UnconfiguredSongRecognizer()

    def show(self)->None:
        self.prepare_screen("Music Visualizer",self._back_action)
        self._analyzer=MusicAnalyzer(spectrum_band_count=24);self._presenter=MusicVisualizerPresenter(self._analyzer);self._panel=MusicVisualizerPanel(self.content_frame)
        self._panel.set_request_handler(self._presenter);self._presenter.attach_ui(self._panel);self._presenter.on_song_recognition_requested=self._identify
        self._panel.pack(fill="both",expand=True)
        configured=not isinstance(self._recognizer,UnconfiguredSongRecognizer);provider="ACRCloud" if configured else None
        self._panel.set_song_recognition_state(SongRecognitionUiState(configured=configured,provider=provider))
        self._capture=PipeWireAudioCapture()
        try:self._capture.start()
        except Exception as exc:LOGGER.warning("System audio capture unavailable: %s",exc);self._panel.set_status(f"Audio capture unavailable: {exc}");return
        self._running=True;self._generation+=1;generation=self._generation;self._panel.set_status("Listening to Linux system audio")
        threading.Thread(target=self._capture_loop,args=(generation,),name="carui-music-visualizer",daemon=True).start()

    def hide(self)->None:
        self._running=False;self._generation+=1;capture=self._capture;self._capture=None
        if capture is not None:
            try:capture.stop()
            except Exception:LOGGER.exception("Failed to stop visualizer capture")
        self._panel=None;self._presenter=None

    def _identify(self)->None:
        panel=self._panel
        if panel is None:return
        if isinstance(self._recognizer,UnconfiguredSongRecognizer):panel.set_song_recognition_state(SongRecognitionUiState(configured=False));return
        if not self._recognition_lock.acquire(blocking=False):return
        panel.set_song_recognition_state(SongRecognitionUiState(configured=True,recognizing=True,provider="ACRCloud"))
        threading.Thread(target=self._recognize_clip,name="carui-song-recognition",daemon=True).start()

    def _recognize_clip(self)->None:
        try:
            capture=PipeWireAudioCapture();capture.start();chunks=[];sample_bytes=0
            try:
                for _ in range(280):
                    frame=capture.read();pcm=b"".join(int(max(-1,min(1,s))*32767).to_bytes(2,"little",signed=True) for s in frame.samples);chunks.append(pcm);sample_bytes+=len(pcm)
                    if sample_bytes>=44100*2*6:break
            finally:capture.stop()
            result=self._recognizer.recognize(b"".join(chunks),sample_bytes=sample_bytes)
            if result is not None:self._metadata_cache.put_result_ids(result)
            self.host.schedule_ui_callback(0,lambda r=result:self._finish_recognition(r))
        except Exception as exc:
            LOGGER.warning("Song recognition failed: %s",exc);self.host.schedule_ui_callback(0,lambda:self._recognition_failed(str(exc)))
        finally:self._recognition_lock.release()

    def _finish_recognition(self,result)->None:
        if self._panel is None:return
        self._panel.set_song(result);self._panel.set_song_recognition_state(SongRecognitionUiState(configured=True,provider="ACRCloud"))

    def _recognition_failed(self,message:str)->None:
        if self._panel:self._panel.set_status(f"Recognition failed: {message}");self._panel.set_song_recognition_state(SongRecognitionUiState(configured=True,provider="ACRCloud"))

    def _capture_loop(self,generation:int)->None:
        capture,analyzer=self._capture,self._analyzer
        if capture is None or analyzer is None:return
        try:
            while self._running and generation==self._generation:
                state=analyzer.analyze(capture.read());self.host.schedule_ui_callback(0,lambda s=state,g=generation:self._render(g,s))
        except Exception as exc:LOGGER.warning("Music visualization stopped: %s",exc);self.host.schedule_ui_callback(0,lambda:self._panel and self._panel.set_status("Music visualization stopped"))

    def _render(self,generation:int,state)->None:
        if generation!=self._generation or not self._running or self._presenter is None:return
        self._presenter.present_analysis(state)
