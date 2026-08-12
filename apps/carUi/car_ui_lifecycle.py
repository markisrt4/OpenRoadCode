# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime lifecycle coordination for the Car UI."""

from __future__ import annotations

from apps.carUi.position_status_presenter import PositionStatusPresenter
from apps.carUi.runtime.car_ui_input_runtime import CarUiInputRuntime


class CarUiLifecycle:
    """Start and stop frontend-adjacent background activity."""

    def __init__(
        self,
        position_presenter: PositionStatusPresenter,
        input_runtime: CarUiInputRuntime,
    ) -> None:
        self._position_presenter = position_presenter
        self._input_runtime = input_runtime
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._input_runtime.start()
        self._position_presenter.start()
        self._started = True

    def stop(self) -> None:
        # Both components are expected to tolerate stop-before-start. Keeping
        # the calls unconditional also cleans up a partially completed start.
        try:
            self._input_runtime.stop()
        finally:
            self._position_presenter.stop()
            self._started = False
