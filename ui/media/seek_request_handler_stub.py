# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op media seek request handler."""

from ui.media.seek_request_handler_if import SeekRequestHandlerIf


class SeekRequestHandlerStub(SeekRequestHandlerIf):
    """Ignore relative and absolute media seek requests."""

    def request_rewind(self, seconds: float) -> None:
        pass

    def request_forward(self, seconds: float) -> None:
        pass

    def request_seek(self, position_s: float) -> None:
        pass
