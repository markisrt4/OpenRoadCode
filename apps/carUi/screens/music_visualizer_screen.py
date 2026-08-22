# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Car UI music visualizer destination."""
from __future__ import annotations

import logging

from apps.carUi.runtime.music_visualizer_runtime_factory import MusicVisualizerRuntime
from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from controllers.audio_analysis.music_visualizer_presenter import MusicVisualizerPresenter
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId

LOGGER = logging.getLogger(__name__)


class MusicVisualizerScreen(CarUiScreen):
    """Bind injected music services to the native Tk visualizer."""

    def __init__(self, host: TkScreenHostIf, *, runtime: MusicVisualizerRuntime, create_menu_tile: MenuTileFactory, back_action) -> None:
        super().__init__(host, ScreenId("music_visualizer"), create_menu_tile)
        self._back_action = back_action
        self._runtime = runtime
        self._presenter: MusicVisualizerPresenter | None = None
        self._panel: MusicVisualizerPanel | None = None

    def show(self) -> None:
        self.prepare_screen("Music Visualizer", self._back_action)
        self._panel = MusicVisualizerPanel(self.content_frame)
        self._presenter = MusicVisualizerPresenter(
            self._runtime.analysis_source,
            self._runtime.song_recognition,
            music_lighting=self._runtime.music_lighting,
            dispatch=lambda callback: self.host.schedule_ui_callback(0, callback),
        )
        self._panel.set_request_handler(self._presenter)
        self._presenter.attach_ui(self._panel)
        if hasattr(self._panel, "set_music_lighting_state"):
            self._runtime.music_lighting.attach_ui(self._panel)
        self._panel.pack(fill="both", expand=True)
        self._panel.set_status("Listening to configured music source")
        try:
            self._presenter.start()
        except Exception as exc:
            LOGGER.warning("Music source unavailable: %s", exc)
            self._panel.set_status(f"Audio source unavailable: {exc}")

    def hide(self) -> None:
        presenter = self._presenter
        panel = self._panel
        self._presenter = None
        self._panel = None
        if panel is not None and hasattr(panel, "set_music_lighting_state"):
            self._runtime.music_lighting.detach_ui(panel)
        if presenter is not None:
            try:
                presenter.stop()
            except Exception:
                LOGGER.exception("Failed to stop music analysis source")
