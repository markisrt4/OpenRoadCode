# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op system volume request handler."""

from ui.system.volume_request_handler_if import VolumeRequestHandlerIf


class VolumeRequestHandlerStub(VolumeRequestHandlerIf):
    """Ignore system volume requests."""

    def request_volume(self, volume_percent: float) -> None:
        pass

    def request_volume_up(self) -> None:
        pass

    def request_volume_down(self) -> None:
        pass

    def request_mute(self, muted: bool) -> None:
        pass
