# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import patch
import json

from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation.position_state_codec import encode_position_state

from scripts.probe_android_location import collect, collect_bus


def test_reports_fix_readiness_without_coordinates_or_url_secrets():
    with patch('scripts.probe_android_location.query', side_effect=[
        {'status': 'ready'}, {'ready': True, 'latitude': 42.5, 'longitude': -83.2,
                             'provider': 'fused', 'age_ms': 250, 'timestamp_ms': 1000}]):
        report = collect('http://user:secret@127.0.0.1:8766')
    assert report['endpoint'] == 'http://127.0.0.1:8766'
    assert report['location'] == dict(ready=True, provider='fused', age_ms=250,
                                      timestamp_ms=1000, coordinates_present=True)
    assert 'secret' not in str(report)
    assert 'latitude' not in str(report)
    assert 'longitude' not in str(report)


def test_reports_bridge_ready_but_location_unavailable():
    with patch('scripts.probe_android_location.query', side_effect=[
        {'status': 'ready'}, {'http_status': 503}]):
        report = collect('http://127.0.0.1:8766')
    assert report['health']['status'] == 'ready'
    assert report['location'] == {'http_status': 503, 'coordinates_present': False}


def test_bus_probe_checks_full_schema_and_omits_coordinates():
    payload = encode_position_state(PositionState(latitude_deg=42.5, longitude_deg=-83.2,
                                                  fix_mode=3, source='android-gps'))
    incompatible = {**payload, 'data': {**payload['data'], 'legacy_motion': 1}}
    with patch('zmq.Context') as context:
        socket = context.return_value.socket.return_value
        socket.poll.return_value = True
        socket.recv_multipart.side_effect = [[b'openroad.navigation.position', json.dumps(p).encode()]
                                             for p in (payload, incompatible, payload)]
        report = collect_bus()
    assert report[0]['valid_for_map'] is True
    assert report[1] == {'valid_for_map': False, 'error': 'position data has missing or unknown fields'}
    assert report[2]['valid_for_map'] is True
    assert '42.5' not in str(report)
    assert 'latitude' not in str(report)
    socket.close.assert_called_once_with(linger=0)
    context.return_value.term.assert_called_once_with()
