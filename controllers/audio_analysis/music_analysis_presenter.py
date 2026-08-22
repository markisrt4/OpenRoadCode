# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral presentation of music analysis state."""
from __future__ import annotations

from collections.abc import Callable

from controllers.music_lighting import MusicLightingController
from ui.music_analysis import (
    MusicAnalysisRequestHandlerIf,
    MusicAnalysisStatus,
    MusicAnalysisUiIf,
    MusicAnalysisUiState,
)

from .music_analysis import MusicAnalysisState
from .music_analysis_source_if import MusicAnalysisSourceIf


class MusicAnalysisPresenter(MusicAnalysisRequestHandlerIf):
    """Own music-analysis lifecycle and expose semantic UI state."""

    def __init__(
        self,
        source: MusicAnalysisSourceIf,
        *,
        music_lighting: MusicLightingController | None = None,
        dispatch: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._source = source
        self._music_lighting = music_lighting
        self._dispatch = dispatch or (lambda callback: callback())
        self._ui: MusicAnalysisUiIf | None = None
        self._status = MusicAnalysisStatus.STOPPED

    @property
    def source(self) -> MusicAnalysisSourceIf:
        return self._source

    def attach_ui(self, ui: MusicAnalysisUiIf) -> None:
        self._ui = ui
        self._publish_ui_state()

    def detach_ui(self) -> None:
        self._ui = None

    def start(self) -> None:
        self._status = MusicAnalysisStatus.STARTING
        self._publish_ui_state()
        try:
            self._source.start(self._on_analysis)
        except Exception as exc:
            self._status = MusicAnalysisStatus.ERROR
            self._publish_ui_state(error=str(exc))
            raise
        self._status = MusicAnalysisStatus.ACTIVE
        self._publish_ui_state()

    def stop(self) -> None:
        self._source.stop()
        self._status = MusicAnalysisStatus.STOPPED
        self._publish_ui_state()

    def request_zeroize(self) -> None:
        self._source.zeroize()
        self._status = MusicAnalysisStatus.ZEROIZING
        self._publish_ui_state()

    def request_sensitivity(self, value: float) -> None:
        self._source.set_sensitivity(value)
        self._publish_ui_state()

    def _on_analysis(self, state: MusicAnalysisState) -> None:
        if self._music_lighting is not None:
            self._music_lighting.update_analysis(state)
        if self._status is MusicAnalysisStatus.ZEROIZING and state.calibrated:
            self._status = MusicAnalysisStatus.ACTIVE
        ui = self._ui
        if ui is not None:
            self._dispatch(lambda: ui.set_analysis_state(state))
            self._dispatch(self._publish_ui_state)

    def _publish_ui_state(self, *, error: str | None = None) -> None:
        ui = self._ui
        if ui is None:
            return
        state = MusicAnalysisUiState(
            status=self._status,
            calibrated=self._source.calibrated,
            sensitivity=self._source.sensitivity,
            error=error if self._status is MusicAnalysisStatus.ERROR else None,
        )
        ui.set_analysis_ui_state(state)
