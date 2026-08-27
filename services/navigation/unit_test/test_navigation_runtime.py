# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for navigation runtime ownership and telemetry publication."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteRequest,
    RouteResult,
)
from messaging.contracts.route_guidance import ROUTE_GUIDANCE_STATE_TOPIC
from services.navigation.navigation_runtime import NavigationRuntime


def _route() -> RouteResult:
    return RouteResult(
        1.0,
        120.0,
        (GeoPoint(42.0, -83.0), GeoPoint(42.0, -82.99)),
        (RouteManeuver("Continue", None, 1.0, 120.0, 0, 1),),
    )


def test_runtime_rejects_nonpositive_rate():
    with pytest.raises(ValueError):
        NavigationRuntime(Mock(), Mock(), source="test", rate_hz=0.0)


def test_runtime_uses_supplied_controller_for_command_service():
    controller = Mock()
    publisher = Mock()
    runtime = NavigationRuntime(
        controller,
        publisher,
        source="test-navigation",
        command_endpoint="inproc://navigation-runtime-unit-test",
    )
    try:
        assert runtime._command_server._service._controller is controller
    finally:
        runtime.close()


def test_route_start_creates_active_session_from_planned_route():
    route = _route()
    route_planner = Mock()
    route_planner.calculate_route.return_value = route
    runtime = NavigationRuntime(
        Mock(),
        Mock(),
        source="test-navigation",
        command_endpoint="inproc://navigation-runtime-route-start-test",
        route_planning_controller=route_planner,
    )
    request = RouteRequest(
        GeoPoint(42.0, -83.0),
        GeoPoint(42.1, -82.9),
    )

    try:
        runtime._activate_route(request, route)

        assert runtime._guidance_controller is not None
        assert runtime._session_controller is not None
        assert runtime._session_controller.state is not None
        assert runtime._session_controller.state.route is route
        assert runtime._session_controller.state.destination == request.destination
    finally:
        runtime.close()


def test_valid_gps_fix_advances_guidance_and_session():
    route = _route()
    route_planner = Mock()
    route_planner.calculate_route.return_value = route
    publisher = Mock()
    runtime = NavigationRuntime(
        Mock(),
        publisher,
        source="test-navigation",
        command_endpoint="inproc://navigation-runtime-guidance-test",
        route_planning_controller=route_planner,
    )
    request = RouteRequest(
        GeoPoint(42.0, -83.0),
        GeoPoint(42.1, -82.9),
    )

    try:
        runtime._activate_route(request, route)
        session = runtime._session_controller
        assert session is not None
        session.update = Mock(wraps=session.update)
        state = SimpleNamespace(
            gps=SimpleNamespace(
                has_fix=True,
                latitude_deg=42.0,
                longitude_deg=-82.995,
            )
        )

        runtime._update_guidance(state)

        session.update.assert_called_once()
        position, guidance = session.update.call_args.args
        assert position == GeoPoint(42.0, -82.995)
        assert guidance.distance_along_route_miles > 0.0
        publisher.publish.assert_called_once()
        topic, payload = publisher.publish.call_args.args
        assert topic == ROUTE_GUIDANCE_STATE_TOPIC
        assert isinstance(payload, bytes)
    finally:
        runtime.close()


def test_cancel_clears_active_session_state():
    route = _route()
    route_planner = Mock()
    runtime = NavigationRuntime(
        Mock(),
        Mock(),
        source="test-navigation",
        command_endpoint="inproc://navigation-runtime-cancel-test",
        route_planning_controller=route_planner,
    )
    request = RouteRequest(GeoPoint(42.0, -83.0), GeoPoint(42.1, -82.9))

    try:
        runtime._activate_route(request, route)
        runtime._cancel_route()

        assert runtime._session_controller is not None
        assert runtime._session_controller.state is None
    finally:
        runtime.close()
