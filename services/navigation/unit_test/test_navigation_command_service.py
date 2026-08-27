# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteResult,
    TravelMode,
)
from services.navigation import (
    CALCULATE_ROUTE_COMMAND,
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


def test_route_calculation_is_forwarded_to_route_planner():
    controller = Mock()
    route_planner = Mock()
    route_planner.calculate_route.return_value = RouteResult(
        distance_miles=10.5,
        duration_seconds=900.0,
        shape=(
            GeoPoint(42.8028, -83.0127),
            GeoPoint(42.3314, -83.0458),
        ),
        maneuvers=(
            RouteManeuver(
                instruction="Head south",
                verbal_instruction="Head south",
                distance_miles=10.5,
                duration_seconds=900.0,
                begin_shape_index=0,
                end_shape_index=1,
            ),
        ),
    )
    service = NavigationCommandService(controller, route_planner)

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {
            "origin": {"latitude": 42.8028, "longitude": -83.0127},
            "destination": {"latitude": 42.3314, "longitude": -83.0458},
            "travel_mode": "AUTO",
        },
    )

    assert result.ok
    assert result.data is not None
    assert result.data["distance_miles"] == 10.5
    request = route_planner.calculate_route.call_args.args[0]
    assert request.origin == GeoPoint(42.8028, -83.0127)
    assert request.destination == GeoPoint(42.3314, -83.0458)
    assert request.travel_mode is TravelMode.AUTO


def test_route_calculation_rejected_when_route_planning_not_configured():
    controller = Mock()
    service = NavigationCommandService(controller)

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {
            "origin": {"latitude": 42.8028, "longitude": -83.0127},
            "destination": {"latitude": 42.3314, "longitude": -83.0458},
        },
    )

    assert not result.ok
    assert "not configured" in result.message


def test_unknown_command_is_rejected_without_touching_controller():
    controller = Mock()
    service = NavigationCommandService(controller)

    result = service.execute("navigation.make_coffee")

    assert not result.ok
    assert "Unknown navigation command" in result.message
    controller.calibrate_stationary.assert_not_called()
    controller.reset_heading.assert_not_called()
