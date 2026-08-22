# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Car UI music visualizer destination."""
from __future__ import annotations

import logging

from apps.carUi.runtime.music_visualizer_runtime_factory import MusicVisualizerRuntime
from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from controllers.audio_analysis.music_analysis_presenter import MusicAnalysisPresenter
from controllers.audio_analysis.music_visualizer_presenter import MusicVisualizerPresenter
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId

LOGGER = logging.getLogger(__name__)


class MusicVisualizerScreen(CarUiScreen):
    """Bind injected music services to the native Tk visualizer."""

    def __init__(self,host:TkScreenHostIf,*,runtime:MusicVisualizerRuntime,create_menu_tile:MenuTileFactory,back_action,configure_lighting_action=None)->None:
        super().__init__(host,ScreenId("music_visualizer"),create_menu_tile)
        self._back_action=back_action
        self._runtime=runtime
        self._configure_lighting_action=configure_lighting_action
        self._analysis_presenter=None
        self._visualizer_presenter=None
        self._panel=None

    def show(self)->None:
        self.prepare_screen("Music Visualizer",self._back_action)
        panel=MusicVisualizerPanel(self.content_frame)
        dispatch=lambda callback:self.host.schedule_ui_callback(0,callback)
        analysis=MusicAnalysisPresenter(
            self._runtime.analysis_source,
            music_lighting=self._runtime.music_lighting,
            dispatch=dispatch,
        )
        visualizer=MusicVisualizerPresenter(
            self._runtime.song_recognition,
            dispatch=dispatch,
        )
        panel.set_music_analysis_request_handler(analysis)
        panel.set_request_handler(visualizer)
        panel.set_music_lighting_request_handler(self._runtime.music_lighting)
        panel.set_configure_lighting_action(self._configure_lighting_action)
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

    def hide(self)->None:
        analysis,visualizer,panel=self._analysis_presenter,self._visualizer_presenter,self._panel
        self._analysis_presenter=None
        self._visualizer_presenter=None
        self._panel=None
        if panel is not None:
            self._runtime.music_lighting.detach_ui(panel)
        if visualizer is not None:
            visualizer.detach_ui()
        if analysis is not None:
            try:
                analysis.stop()
            except Exception:
                LOGGER.exception("Failed to stop music analysis source")
            analysis.detach_ui()
