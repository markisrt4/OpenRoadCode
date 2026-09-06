# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime
from unittest.mock import Mock

from controllers.navigation.geocoding import GeocodedLocation
from controllers.navigation.navigation_state import NavigationState, PositionState
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteResult,
    TravelMode,
)
from hardware_io.imu import Vector3
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


def _route_result():
    return RouteResult(
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


def _navigation_state(position: PositionState | None) -> NavigationState:
    zero = Vector3(0.0, 0.0, 0.0)
    return NavigationState(
        timestamp=datetime.now(),
        heading_deg=0.0,
        pitch_deg=0.0,
        roll_deg=0.0,
        acceleration_mps2=zero,
        linear_acceleration_mps2=zero,
        angular_velocity_rad_s=zero,
        position=position,
    )


def test_route_calculation_is_forwarded_to_route_planner():
    controller = Mock()
    route_planner = Mock()
    route_planner.calculate_route.return_value = _route_result()
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


def test_route_uses_current_position_when_origin_is_omitted():
    controller = Mock()
    controller.read_state.return_value = _navigation_state(
        PositionState(
            latitude_deg=42.8028,
            longitude_deg=-83.0127,
            fix_mode=3,
            source="test",
        )
    )
    route_planner = Mock()
    route_planner.calculate_route.return_value = _route_result()
    service = NavigationCommandService(controller, route_planner)

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {"destination": {"latitude": 42.3314, "longitude": -83.0458}},
    )

    assert result.ok
    controller.read_state.assert_called_once_with()
    request = route_planner.calculate_route.call_args.args[0]
    assert request.origin == GeoPoint(42.8028, -83.0127)


def test_route_without_origin_is_rejected_when_current_position_has_no_fix():
    controller = Mock()
    controller.read_state.return_value = _navigation_state(
        PositionState(latitude_deg=42.8028, longitude_deg=-83.0127, fix_mode=1)
    )
    route_planner = Mock()
    service = NavigationCommandService(controller, route_planner)

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {"destination": {"latitude": 42.3314, "longitude": -83.0458}},
    )

    assert not result.ok
    assert "current navigation position is unavailable" in result.message
    route_planner.calculate_route.assert_not_called()


def test_text_destination_is_geocoded_before_route_calculation():
    controller = Mock()
    route_planner = Mock()
    route_planner.calculate_route.return_value = _route_result()
    geocoder = Mock()
    geocoder.geocode.return_value = GeocodedLocation(
        formatted_address="100 Example Avenue, Testville, MI",
        latitude_deg=42.3314,
        longitude_deg=-83.0458,
    )
    service = NavigationCommandService(
        controller,
        route_planner,
        geocoder=geocoder,
    )

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {
            "origin": {"latitude": 42.8028, "longitude": -83.0127},
            "destination": "100 Example Avenue, Testville, MI",
            "travel_mode": "AUTO",
        },
    )

    assert result.ok
    geocoder.geocode.assert_called_once_with("100 Example Avenue, Testville, MI")
    request = route_planner.calculate_route.call_args.args[0]
    assert request.destination == GeoPoint(42.3314, -83.0458)


def test_unresolved_text_destination_is_rejected_before_route_calculation():
    route_planner = Mock()
    geocoder = Mock()
    geocoder.geocode.return_value = None
    service = NavigationCommandService(Mock(), route_planner, geocoder=geocoder)

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {
            "origin": {"latitude": 42.8028, "longitude": -83.0127},
            "destination": "Definitely Not A Real Place",
        },
    )

    assert not result.ok
    assert "could not be resolved" in result.message
    geocoder.geocode.assert_called_once_with("Definitely Not A Real Place")
    route_planner.calculate_route.assert_not_called()


def test_text_destination_is_rejected_when_geocoding_not_configured():
    route_planner = Mock()
    service = NavigationCommandService(Mock(), route_planner)

    result = service.execute(
        CALCULATE_ROUTE_COMMAND,
        {
            "origin": {"latitude": 42.8028, "longitude": -83.0127},
            "destination": "Testville",
        },
    )

    assert not result.ok
    assert "geocoding" in result.message
    route_planner.calculate_route.assert_not_called()


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
