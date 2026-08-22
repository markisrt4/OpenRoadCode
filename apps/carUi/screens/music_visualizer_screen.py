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
from controllers.audio_analysis.pcm_music_analysis_source import PcmMusicAnalysisSource
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
        self._back_action = back_action
        self._source = None
        self._presenter = None
        self._panel = None
        self._generation = 0
        self._recognition_lock = threading.Lock()
        self._recognizer = self._create_recognizer()
        self._metadata_cache = SongMetadataCache(PersistentCache(Path("~/.cache/openroadcode/song_recognition").expanduser(), suffix=".json"))

    @staticmethod
    def _create_recognizer():
        host = os.environ.get("ACRCLOUD_HOST", "").strip()
        key = os.environ.get("ACRCLOUD_ACCESS_KEY", "").strip()
        secret = os.environ.get("ACRCLOUD_ACCESS_SECRET", "").strip()
        return AcrCloudSongRecognizer(AcrCloudConfig(host, key, secret)) if host and key and secret else UnconfiguredSongRecognizer()

    def show(self) -> None:
        self.prepare_screen("Music Visualizer", self._back_action)
        self._generation += 1
        generation = self._generation
        self._source = PcmMusicAnalysisSource(PipeWireAudioCapture(), MusicAnalyzer(spectrum_band_count=24))
        self._presenter = MusicVisualizerPresenter(self._source)
        self._panel = MusicVisualizerPanel(self.content_frame)
        self._panel.set_request_handler(self._presenter)
        self._presenter.attach_ui(self._panel)
        self._presenter.on_song_recognition_requested = self._identify
        self._panel.pack(fill="both", expand=True)
        configured = not isinstance(self._recognizer, UnconfiguredSongRecognizer)
        self._panel.set_song_recognition_state(SongRecognitionUiState(configured=configured, provider="ACRCloud" if configured else None))
        self._panel.set_status("Listening to Linux system audio")
        try:
            self._source.start(lambda state, g=generation: self.host.schedule_ui_callback(0, lambda s=state: self._render(g, s)))
        except Exception as exc:
            LOGGER.warning("System audio source unavailable: %s", exc)
            self._panel.set_status(f"Audio source unavailable: {exc}")

    def hide(self) -> None:
        self._generation += 1
        presenter = self._presenter
        self._presenter = None
        self._source = None
        if presenter is not None:
            try:
                presenter.stop()
            except Exception:
                LOGGER.exception("Failed to stop music analysis source")
        self._panel = None

    def _identify(self) -> None:
        panel = self._panel
        if panel is None:
            return
        if isinstance(self._recognizer, UnconfiguredSongRecognizer):
            panel.set_song_recognition_state(SongRecognitionUiState(configured=False))
            return
        if not self._recognition_lock.acquire(blocking=False):
            return
        panel.set_song_recognition_state(SongRecognitionUiState(configured=True, recognizing=True, provider="ACRCloud"))
        threading.Thread(target=self._recognize_clip, name="carui-song-recognition", daemon=True).start()

    def _recognize_clip(self) -> None:
        try:
            source = self._source
            audio = source.recent_audio_pcm16(6.0) if source is not None else b""
            if not audio:
                raise RuntimeError("No recent audio is available yet")
            result = self._recognizer.recognize(audio, sample_bytes=len(audio))
            if result is not None:
                self._metadata_cache.put_result_ids(result)
            self.host.schedule_ui_callback(0, lambda r=result: self._finish_recognition(r))
        except Exception as exc:
            LOGGER.warning("Song recognition failed: %s", exc)
            self.host.schedule_ui_callback(0, lambda: self._recognition_failed(str(exc)))
        finally:
            self._recognition_lock.release()

    def _finish_recognition(self, result) -> None:
        if self._panel is None:
            return
        self._panel.set_song(result)
        self._panel.set_song_recognition_state(SongRecognitionUiState(configured=True, provider="ACRCloud"))

    def _recognition_failed(self, message: str) -> None:
        if self._panel:
            self._panel.set_status(f"Recognition failed: {message}")
            self._panel.set_song_recognition_state(SongRecognitionUiState(configured=True, provider="ACRCloud"))

    def _render(self, generation: int, state) -> None:
        if generation != self._generation or self._presenter is None:
            return
        self._presenter.present_analysis(state)
