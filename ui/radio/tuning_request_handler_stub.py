# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op tuning request handler."""

from ui.radio.tuning_request_handler_if import TuningRequestHandlerIf


class TuningRequestHandlerStub(TuningRequestHandlerIf):
    """Ignore frequency-tuning requests."""

    def request_tune_up(self) -> None:
        pass

    def request_tune_down(self) -> None:
        pass
