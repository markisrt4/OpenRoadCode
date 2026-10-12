# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Vehicle presentation wire compatibility and invalid motion checks."""

from unittest.mock import Mock

import pytest

from protocols.map_renderer.map_renderer_client import MapRendererClient


def test_legacy_position_payload_stays_immediate_and_directionless():
    publisher = Mock()
    client = MapRendererClient(publisher)
    client.set_position(42, -83)
    assert publisher.publish.call_args.args[1] == {
        "command": "set_position", "latitude": 42, "longitude": -83,
    }


def test_vehicle_motion_payload_carries_direction_separately_from_prediction():
    publisher = Mock()
    client = MapRendererClient(publisher)
    client.set_position(42, -83, heading_deg=80, course_deg=90, speed_m_s=10, smooth=True)
    assert publisher.publish.call_args.args[1] == {
        "command": "set_position", "latitude": 42, "longitude": -83,
        "heading": 80, "course": 90, "speed_m_s": 10, "smooth": True,
    }


@pytest.mark.parametrize("field,value", [
    ("heading_deg", float("nan")), ("course_deg", float("inf")),
    ("speed_m_s", -1), ("speed_m_s", float("nan")),
])
def test_invalid_motion_is_rejected_before_publication(field, value):
    publisher = Mock()
    client = MapRendererClient(publisher)
    with pytest.raises(ValueError):
        client.set_position(42, -83, **{field: value})
    publisher.publish.assert_not_called()


def test_follow_is_explicit_and_can_be_disabled_without_a_camera_jump():
    publisher = Mock()
    client = MapRendererClient(publisher)
    client.set_camera(42, -83, 16, follow_position=True)
    assert publisher.publish.call_args.args[1]["follow_position"] is True
    client.set_follow(False)
    assert publisher.publish.call_args.args[1] == {"command": "set_follow", "enabled": False}
