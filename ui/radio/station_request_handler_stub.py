# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op station request handler."""

from ui.radio.station_request_handler_if import StationRequestHandlerIf


class StationRequestHandlerStub(StationRequestHandlerIf):
    """Ignore station-navigation requests."""

    def request_next_station(self) -> None:
        pass

    def request_previous_station(self) -> None:
        pass
