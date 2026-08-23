# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Car UI music visualizer destination."""
from __future__ import annotations

import logging
import os
import socket
import subprocess
import shutil
import sys
import threading
import time
from pathlib import Path

from apps.carUi.runtime.music_visualizer_runtime_factory import MusicVisualizerRuntime
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from controllers.audio_analysis.music_analysis_presenter import MusicAnalysisPresenter
from controllers.audio_analysis.music_visualizer_presenter import MusicVisualizerPresenter
from config.runtime_target import RuntimeTarget, detect_runtime_target
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId

LOGGER = logging.getLogger(__name__)
_VISUALIZER_EXIT_SIGNAL=Path("/tmp/openroadcode-visualizer-exit")


class MusicVisualizerScreen(CarUiScreen):
    """Bind injected music services to the native Tk visualizer."""

    def __init__(self,host:TkScreenHostIf,*,runtime:MusicVisualizerRuntime,create_menu_tile:MenuTileFactory,back_action,configure_lighting_action=None,artwork_provider=None,spotify_controller=None,show_spotify_action=None)->None:
        super().__init__(host,ScreenId("music_visualizer"),create_menu_tile)
        self._back_action=back_action
        self._runtime=runtime
        self._configure_lighting_action=configure_lighting_action
        self._artwork_provider=artwork_provider
        self._spotify_controller=spotify_controller
        self._show_spotify_action=show_spotify_action
        self._analysis_presenter=None
        self._visualizer_presenter=None
        self._panel=None
        self._web_process=None
        self._runtime_target=detect_runtime_target()
        browser_arguments=["--new-window","--autoplay-policy=no-user-gesture-required","--no-first-run"]
        if self._runtime_target is RuntimeTarget.LINUX_DEV:
            browser_arguments.extend(("--use-angle=swiftshader","--enable-unsafe-swiftshader","--disable-features=VaapiVideoDecoder,VaapiVideoEncoder"))
        self._web_launcher=BrowserKioskLauncher(
            url=os.environ.get("CARUI_VISUALIZER_WEB_URL","http://127.0.0.1:5000/visualizer/fullscreen?visualizer=prismatic"),
            process_pattern="openroadcode-music-visualizer",
            log_file="/tmp/openroadcode-carui-browser.log",
            startup_grace_seconds=1.0,
            extra_arguments=tuple(browser_arguments),
        )

    def show(self)->None:
        self.prepare_screen("Music Visualizer",self._back_action)
        panel=MusicVisualizerPanel(self.content_frame,self._artwork_provider)
        dispatch=lambda callback:self.host.schedule_ui_callback(0,callback)
        visualizer=MusicVisualizerPresenter(
            self._runtime.song_recognition,
            dispatch=dispatch,
        )
        analysis=MusicAnalysisPresenter(
            self._runtime.analysis_source,
            music_lighting=self._runtime.music_lighting,
            analysis_observer=visualizer.audio_buffer_updated,
            dispatch=dispatch,
        )
        panel.set_music_analysis_request_handler(analysis)
        panel.set_request_handler(visualizer)
        panel.set_music_lighting_request_handler(self._runtime.music_lighting)
        panel.set_configure_lighting_action(self._configure_lighting_action)
        panel.set_fullscreen_action(self._open_web_visualizer)
        panel.set_play_song_action(self._play_in_spotify)
        analysis.attach_ui(panel)
        visualizer.attach_ui(panel)
        self._runtime.music_lighting.attach_ui(panel)
        panel.pack(fill="both",expand=True)
        self._panel=panel
        self._analysis_presenter=analysis
        self._visualizer_presenter=visualizer
        try:
            analysis.start()
        except Exception as exc:
            LOGGER.warning("Music source unavailable: %s",exc)

    def _play_in_spotify(self,song)->None:
        if self._spotify_controller is None or not song.spotify_uri:return
        def worker():
            try:
                self._spotify_controller.play_uri(song.spotify_uri)
            except Exception:
                LOGGER.exception("Failed to play recognized song in Spotify")
                return
            if self._show_spotify_action is not None:self.host.schedule_ui_callback(0,self._show_spotify_action)
        threading.Thread(target=worker,name="recognized-song-playback",daemon=True).start()

    def hide(self)->None:
        analysis,visualizer,panel=self._analysis_presenter,self._visualizer_presenter,self._panel
        self._analysis_presenter=None
        self._visualizer_presenter=None
        self._panel=None
        if panel is not None:
            panel.close()
            self._runtime.music_lighting.detach_ui(panel)
        if visualizer is not None:
            visualizer.detach_ui()
        if analysis is not None:
            try:
                analysis.stop()
            except Exception:
                LOGGER.exception("Failed to stop music analysis source")
            analysis.detach_ui()

    def _open_web_visualizer(self)->None:
        """Open the shared GPU renderer, starting WebUI locally when needed."""
        _VISUALIZER_EXIT_SIGNAL.unlink(missing_ok=True)
        host="127.0.0.1";port=int(os.environ.get("OPENROADCODE_WEB_PORT","5000"))
        try:
            with socket.create_connection((host,port),timeout=.15):pass
        except OSError:
            if self._web_process is None or self._web_process.poll() is not None:
                environment=dict(os.environ);environment.setdefault("OPENROADCODE_WEB_HOST",host);environment["OPENROADCODE_WEB_PORT"]=str(port);environment["OPENROADCODE_WEB_DEBUG"]="0"
                interpreter=os.environ.get("CARUI_WEB_PYTHON") or (shutil.which("python3") if self._runtime_target is RuntimeTarget.LINUX_DEV else sys.executable)
                if interpreter is None:self._set_web_visualizer_error("python3 was not found");return
                log=open("/tmp/openroadcode-carui-webui.log","a",encoding="utf-8")
                try:self._web_process=subprocess.Popen([interpreter,"-m","apps.webUi.main"],env=environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                finally:log.close()
        if self._panel is not None:self._panel.set_fullscreen_status("STARTING WEBGL…")
        root=self._panel.winfo_toplevel() if self._panel is not None else None
        if root is not None:root.lower()
        threading.Thread(target=self._wait_for_web_visualizer,args=(host,port),daemon=True).start()

    def _wait_for_web_visualizer(self,host:str,port:int)->None:
        error="WebUI did not become ready"
        for _ in range(50):
            try:
                with socket.create_connection((host,port),timeout=.1):pass
                self._launch_web_visualizer();return
            except OSError as exc:
                error=str(exc);time.sleep(.1)
        self.host.schedule_ui_callback(0,lambda:self._launch_failed(error))

    def _launch_web_visualizer(self)->None:
        try:
            self._web_launcher.launch(os.environ.get("DISPLAY",":0"))
            self.host.schedule_ui_callback(0,self._watch_for_visualizer_exit)
        except Exception as exc:
            LOGGER.exception("Failed to launch fullscreen WebGL visualizer")
            error=str(exc);self.host.schedule_ui_callback(0,lambda error=error:self._launch_failed(error))

    def _launch_failed(self,error:str)->None:
        if self._panel is not None:self._panel.winfo_toplevel().lift()
        self._set_web_visualizer_error(error)

    def _watch_for_visualizer_exit(self)->None:
        if _VISUALIZER_EXIT_SIGNAL.exists():
            _VISUALIZER_EXIT_SIGNAL.unlink(missing_ok=True)
            try:self._web_launcher.stop(os.environ.get("DISPLAY",":0"))
            finally:
                if self._panel is not None:self._panel.winfo_toplevel().lift();self._panel.set_fullscreen_status(None)
            return
        self.host.schedule_ui_callback(200,self._watch_for_visualizer_exit)

    def _set_web_visualizer_error(self,error:str)->None:
        if self._panel is not None:self._panel.set_fullscreen_status(f"WEBGL ERROR: {error}")
