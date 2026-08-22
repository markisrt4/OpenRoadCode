# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from services.navigation import (
    CALIBRATE_STATIONARY_COMMAND,
    RESET_HEADING_COMMAND,
    NavigationCommandService,
)


def test_stationary_calibration_is_forwarded_to_controller():
    controller = Mock()
    service = NavigationCommandService(controller)

    result = service.execute(
        CALIBRATE_STATIONARY_COMMAND,
        {"sample_count": 25, "sample_interval_s": 0.02},
    )

    assert result.ok
    controller.calibrate_stationary.assert_called_once_with(
        sample_count=25,
        sample_interval_s=0.02,
    )


def test_heading_reset_is_forwarded_to_controller():
    controller = Mock()
    service = NavigationCommandService(controller)

    result = service.execute(RESET_HEADING_COMMAND, {"heading_deg": 12.5})

    assert result.ok
    controller.reset_heading.assert_called_once_with(12.5)


def test_unknown_command_is_rejected_without_touching_controller():
    controller = Mock()
    service = NavigationCommandService(controller)

    result = service.execute("navigation.make_coffee")

    assert not result.ok
    assert "Unknown navigation command" in result.message
    controller.calibrate_stationary.assert_not_called()
    controller.reset_heading.assert_not_called()
