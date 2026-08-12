# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op playback request handler."""

from ui.radio.playback_request_handler_if import PlaybackRequestHandlerIf


class PlaybackRequestHandlerStub(PlaybackRequestHandlerIf):
    """Ignore playback requests."""

    def request_play(self) -> None:
        pass

    def request_pause(self) -> None:
        pass
