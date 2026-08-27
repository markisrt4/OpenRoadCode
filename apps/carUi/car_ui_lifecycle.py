# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime lifecycle coordination for the Car UI."""

from __future__ import annotations

from apps.carUi.runtime.car_ui_input_runtime import CarUiInputRuntime
from messaging.message_dispatcher import MessageDispatcher


class CarUiLifecycle:
    """Start and stop frontend-adjacent background activity."""

    def __init__(
        self,
        input_runtime: CarUiInputRuntime,
        message_dispatcher: MessageDispatcher,
    ) -> None:
        self._input_runtime = input_runtime
        self._message_dispatcher = message_dispatcher
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._input_runtime.start()
        self._message_dispatcher.start()
        self._started = True

    def stop(self) -> None:
        try:
            self._input_runtime.stop()
        finally:
            self._message_dispatcher.close()
            self._started = False
