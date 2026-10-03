# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Verify correlation across navigation replies and map bus commands."""

import json
import logging
from unittest.mock import Mock

from common.logging.structured import JsonFormatter, current_operation, validate_event
from controllers.route_planning.route_map_presenter import present_route
from controllers.route_planning.route_planning_types import GeoPoint, RouteRequest
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.map_renderer.map_renderer_client import MapRendererClient
from services.navigation.navigation_command_client import NavigationCommandClient
from services.navigation.navigation_command_service import NavigationCommandService


def test_route_id_survives_service_reply_and_map_publication(caplog):
    caplog.set_level(logging.INFO)
    backend = Mock()
    backend.route.return_value = {
        "trip": {
            "summary": {"length": 1.5, "time": 60},
            "legs": [{"shape": "_izlhA~rlgdF_{geC~ywl@"}],
        }
    }
    controller = ValhallaRoutePlanningController(backend)
    route = controller.calculate_route(RouteRequest(GeoPoint(42, -83), GeoPoint(43, -84)))
    # Simulate the JSON boundary between the navigation service and the UI.
    reply = json.loads(json.dumps(NavigationCommandService._route_data(route)))
    decoded = NavigationCommandClient._decode_route(reply)
    publisher = Mock()
    present_route(decoded, MapRendererClient(publisher))
    operation_id = route.operation_id
    assert operation_id and decoded.operation_id == operation_id
    for call in publisher.publish.call_args_list:
        assert call.args[1]["operation_id"] == operation_id
    emitted = [
        json.loads(JsonFormatter().format(record))
        for record in caplog.records
        if record.name in {"navigation.routing", "map_renderer.client"}
    ]
    assert {item["event"] for item in emitted} >= {
        "route.requested",
        "route.calculated",
        "command.published",
    }
    assert all(item["operation_id"] == operation_id for item in emitted)
    assert all(
        "latitude" not in item and "longitude" not in item and "geojson" not in item
        for item in emitted
    )
    for item in emitted:
        validate_event(item)
    assert current_operation() is None


def test_route_failure_logs_type_without_destination_or_payload(caplog):
    caplog.set_level(logging.INFO)
    backend = Mock()
    backend.route.side_effect = RuntimeError("secret route payload latitude=42 longitude=-83")
    controller = ValhallaRoutePlanningController(backend)
    import pytest

    with pytest.raises(RuntimeError):
        controller.calculate_route(RouteRequest(GeoPoint(42, -83), GeoPoint(43, -84)))
    failure = next(
        json.loads(JsonFormatter().format(record))
        for record in caplog.records
        if getattr(record, "event", None) == "route.failed"
    )
    assert failure["exception_type"] == "RuntimeError"
    assert "secret" not in json.dumps(failure)
    assert failure["operation_id"]
    assert current_operation() is None
