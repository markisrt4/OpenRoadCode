# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op preset request handler."""

from ui.radio.preset_request_handler_if import PresetRequestHandlerIf


class PresetRequestHandlerStub(PresetRequestHandlerIf):
    """Ignore preset requests."""

    def request_preset(self, preset_index: int) -> None:
        pass
