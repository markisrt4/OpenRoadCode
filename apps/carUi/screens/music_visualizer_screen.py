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
from controllers.cache.persistent_cache import PersistentCache
from controllers.song_recognition import (
    AcrCloudConfig, AcrCloudSongRecognizer, SongMetadataCache,
    UnconfiguredSongRecognizer,
)
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture
from ui.screen_ui_if import ScreenId

LOGGER = logging.getLogger(__name__)


class MusicVisualizerScreen(CarUiScreen):
    """Capture Linux system audio and render the complete native music UI."""

    def __init__(self, host: TkScreenHostIf, *, create_menu_tile: MenuTileFactory, back_action) -> None:
        super().__init__(host, ScreenId("music_visualizer"), create_menu_tile)
        self._back_action = back_action
        self._capture: PipeWireAudioCapture | None = None
        self._analyzer: MusicAnalyzer | None = None
        self._panel: MusicVisualizerPanel | None = None
        self._running = False
        self._generation = 0
        self._recognition_lock = threading.Lock()
        self._recognizer = self._create_recognizer()
        self._metadata_cache = SongMetadataCache(PersistentCache(Path("~/.cache/openroadcode/song_recognition").expanduser(), suffix=".json"))

    @staticmethod
    def _create_recognizer():
        host=os.environ.get("ACRCLOUD_HOST","").strip();key=os.environ.get("ACRCLOUD_ACCESS_KEY","").strip();secret=os.environ.get("ACRCLOUD_ACCESS_SECRET","").strip()
        if host and key and secret:return AcrCloudSongRecognizer(AcrCloudConfig(host,key,secret))
        return UnconfiguredSongRecognizer()

    def show(self) -> None:
        self.prepare_screen("Music Visualizer", self._back_action)
        self._analyzer = MusicAnalyzer(spectrum_band_count=24)
        self._panel = MusicVisualizerPanel(
            self.content_frame,
            on_zeroize=self._zeroize,
            on_sensitivity=self._set_sensitivity,
            on_identify=self._identify,
        )
        self._panel.pack(fill="both", expand=True)
        if isinstance(self._recognizer,UnconfiguredSongRecognizer):self._panel.set_recognition_status("Song recognition unconfigured")
        else:self._panel.set_recognition_status("ACRCloud ready · press IDENTIFY")
        self._capture = PipeWireAudioCapture()
        try:self._capture.start()
        except Exception as exc:
            LOGGER.warning("System audio capture unavailable: %s",exc);self.set_status(f"Audio capture unavailable: {exc}");return
        self._running=True;self._generation+=1;generation=self._generation;self.set_status("Listening to Linux system audio")
        threading.Thread(target=self._capture_loop,args=(generation,),name="carui-music-visualizer",daemon=True).start()

    def hide(self) -> None:
        self._running=False;self._generation+=1;capture=self._capture;self._capture=None
        if capture is not None:
            try:capture.stop()
            except Exception:LOGGER.exception("Failed to stop visualizer capture")
        self._panel=None

    def _zeroize(self)->None:
        if self._analyzer:self._analyzer.begin_zeroize()
        self.set_status("Zeroizing vehicle / room noise · keep music off")
        if self._panel:self._panel.after(1700,lambda:self.set_status("Noise calibration active"))

    def _set_sensitivity(self,value:float)->None:
        if self._analyzer:self._analyzer.set_sensitivity(value)

    def _identify(self)->None:
        if isinstance(self._recognizer,UnconfiguredSongRecognizer):
            if self._panel:self._panel.set_recognition_status("Song recognition unconfigured")
            return
        if not self._recognition_lock.acquire(blocking=False):return
        if self._panel:self._panel.set_recognition_status("Listening for song…")
        threading.Thread(target=self._recognize_clip,name="carui-song-recognition",daemon=True).start()

    def _recognize_clip(self)->None:
        try:
            # ACRCloud accepts raw sample bytes. Capture roughly six seconds from
            # the same PipeWire monitor without involving the Tk/UI thread.
            capture=PipeWireAudioCapture();capture.start();chunks=[];sample_bytes=0
            try:
                for _ in range(280):
                    frame=capture.read();pcm=b"".join(int(max(-1,min(1,s))*32767).to_bytes(2,"little",signed=True) for s in frame.samples);chunks.append(pcm);sample_bytes+=len(pcm)
                    if sample_bytes>=44100*2*6:break
            finally:capture.stop()
            result=self._recognizer.recognize(b"".join(chunks),sample_bytes=sample_bytes)
            if result is None:self.host.schedule_ui_callback(0,lambda:self._panel and self._panel.set_recognition_status("No song identified"));return
            self._metadata_cache.put_result_ids(result)
            artist=", ".join(result.artists);album=result.album or "";provider=result.provider
            self.host.schedule_ui_callback(0,lambda:self._panel and self._panel.set_song_metadata(result.title,artist,album,provider))
        except Exception as exc:
            LOGGER.warning("Song recognition failed: %s",exc);self.host.schedule_ui_callback(0,lambda:self._panel and self._panel.set_recognition_status(f"Recognition failed: {exc}"))
        finally:self._recognition_lock.release()

    def _capture_loop(self,generation:int)->None:
        capture,analyzer=self._capture,self._analyzer
        if capture is None or analyzer is None:return
        try:
            while self._running and generation==self._generation:
                state=analyzer.analyze(capture.read());self.host.schedule_ui_callback(0,lambda s=state,g=generation:self._render(g,s))
        except Exception as exc:
            LOGGER.warning("Music visualization stopped: %s",exc);self.host.schedule_ui_callback(0,lambda:self.set_status("Music visualization stopped"))

    def _render(self,generation:int,state)->None:
        if generation!=self._generation or not self._running or self._panel is None:return
        self._panel.update_state(state)
