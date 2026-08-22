# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Car UI music visualizer destination."""
from __future__ import annotations
import logging
import threading
from apps.carUi.runtime.music_visualizer_runtime_factory import MusicVisualizerRuntime
from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from controllers.audio_analysis.music_visualizer_presenter import MusicVisualizerPresenter
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.music_visualizer import SongRecognitionUiState
from ui.screen_ui_if import ScreenId
LOGGER=logging.getLogger(__name__)
class MusicVisualizerScreen(CarUiScreen):
    """Bind injected music services to the native Tk visualizer."""
    def __init__(self,host:TkScreenHostIf,*,runtime:MusicVisualizerRuntime,create_menu_tile:MenuTileFactory,back_action)->None:
        super().__init__(host,ScreenId("music_visualizer"),create_menu_tile);self._back_action=back_action;self._runtime=runtime;self._presenter=None;self._panel=None;self._generation=0;self._recognition_lock=threading.Lock()
    def show(self)->None:
        self.prepare_screen("Music Visualizer",self._back_action);self._generation+=1;generation=self._generation;self._presenter=MusicVisualizerPresenter(self._runtime.analysis_source);self._panel=MusicVisualizerPanel(self.content_frame);self._panel.set_request_handler(self._presenter);self._presenter.attach_ui(self._panel);self._presenter.on_song_recognition_requested=self._identify;self._panel.pack(fill="both",expand=True);r=self._runtime.recognizer;self._panel.set_song_recognition_state(SongRecognitionUiState(configured=r.is_configured,provider=r.provider_name));self._panel.set_status("Listening to configured music source")
        try:self._runtime.analysis_source.start(lambda state,g=generation:self.host.schedule_ui_callback(0,lambda s=state:self._render(g,s)))
        except Exception as exc:LOGGER.warning("Music source unavailable: %s",exc);self._panel.set_status(f"Audio source unavailable: {exc}")
    def hide(self)->None:
        self._generation+=1
        try:self._runtime.analysis_source.stop()
        except Exception:LOGGER.exception("Failed to stop music analysis source")
        self._presenter=None;self._panel=None
    def _identify(self)->None:
        p=self._panel;r=self._runtime.recognizer
        if p is None:return
        if not r.is_configured:p.set_song_recognition_state(SongRecognitionUiState(configured=False));return
        if not self._recognition_lock.acquire(blocking=False):return
        p.set_song_recognition_state(SongRecognitionUiState(configured=True,recognizing=True,provider=r.provider_name));threading.Thread(target=self._recognize_clip,name="carui-song-recognition",daemon=True).start()
    def _recognize_clip(self)->None:
        try:
            audio=self._runtime.analysis_source.recent_audio_pcm16(6.0)
            if not audio:raise RuntimeError("No recent audio is available yet")
            result=self._runtime.recognizer.recognize(audio,sample_bytes=len(audio))
            if result is not None:self._runtime.metadata_cache.put_result_ids(result)
            self.host.schedule_ui_callback(0,lambda r=result:self._finish_recognition(r))
        except Exception as exc:LOGGER.warning("Song recognition failed: %s",exc);self.host.schedule_ui_callback(0,lambda:self._recognition_failed(str(exc)))
        finally:self._recognition_lock.release()
    def _finish_recognition(self,result)->None:
        if self._panel is None:return
        r=self._runtime.recognizer;self._panel.set_song(result);self._panel.set_song_recognition_state(SongRecognitionUiState(configured=r.is_configured,provider=r.provider_name))
    def _recognition_failed(self,message:str)->None:
        if self._panel is None:return
        r=self._runtime.recognizer;self._panel.set_status(f"Recognition failed: {message}");self._panel.set_song_recognition_state(SongRecognitionUiState(configured=r.is_configured,provider=r.provider_name))
    def _render(self,generation:int,state)->None:
        if generation!=self._generation or self._presenter is None:return
        self._presenter.present_analysis(state)
