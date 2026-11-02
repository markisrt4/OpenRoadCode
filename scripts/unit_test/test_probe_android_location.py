# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import patch

from scripts.probe_android_location import collect


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
