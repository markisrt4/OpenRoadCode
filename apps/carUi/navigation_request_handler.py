# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI command adapter for navigation-estimator requests."""

from __future__ import annotations

from controllers.navigation import NavigationControllerIf
from ui.navigation import NavigationRequestHandlerIf


class NavigationRequestHandler(NavigationRequestHandlerIf):
    """Forward explicit user commands to the configured navigation controller.

    Navigation telemetry is deliberately not read here. Public state reaches
    Car UI through the message bus; this adapter exists only for imperative
    operations that mutate estimator state.
    """

    def __init__(self, controller: NavigationControllerIf) -> None:
        self._controller = controller

    def request_stationary_calibration(self) -> None:
        """Calibrate the estimator's stationary sensor biases."""
        self._controller.calibrate_stationary()

    def request_heading_reset(self) -> None:
        """Reset the estimator's relative heading reference."""
        self._controller.reset_heading()
