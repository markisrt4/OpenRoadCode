# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op navigation request handler."""

from ui.navigation.navigation_request_handler_if import NavigationRequestHandlerIf


class NavigationRequestHandlerStub(NavigationRequestHandlerIf):
    """Ignore navigation-estimation requests."""

    def request_stationary_calibration(self) -> None:
        pass

    def request_heading_reset(self) -> None:
        pass
