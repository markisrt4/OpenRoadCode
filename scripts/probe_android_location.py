#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read Android Bridge location readiness without printing coordinates."""
import argparse
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


def query(url):
    try:
        with urlopen(url, timeout=3) as response:
            payload = json.load(response)
        return payload if isinstance(payload, dict) else {'error': 'non-object JSON'}
    except HTTPError as error:
        return {'http_status': error.code}
    except (URLError, OSError, ValueError):
        return {'error': 'unavailable or invalid JSON'}


def collect(base_url):
    endpoint = urlsplit(base_url)
    report = {'endpoint': f'{endpoint.scheme}://{endpoint.hostname}:{endpoint.port or (443 if endpoint.scheme == "https" else 80)}'}
    health = query(base_url.rstrip('/') + '/health')
    location = query(base_url.rstrip('/') + '/location')
    report['health'] = {key: health[key] for key in ('status', 'http_status', 'error') if key in health}
    report['location'] = {key: location[key] for key in
                          ('ready', 'provider', 'age_ms', 'timestamp_ms', 'http_status', 'error')
                          if key in location}
    report['location']['coordinates_present'] = all(
        isinstance(location.get(key), (float, int)) and not isinstance(location.get(key), bool)
        for key in ('latitude', 'longitude'))
    return report


def collect_bus(seconds=5):
    """Validate the same position contract as the UI, without printing fixes."""
    import zmq
    from messaging.contracts.navigation.position_state_codec import decode_position_state

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    messages = []
    try:
        socket.connect('tcp://127.0.0.1:5557')
        socket.setsockopt_string(zmq.SUBSCRIBE, 'openroad.navigation.position')
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and len(messages) < 3:
            if not socket.poll(250):
                continue
            try:
                payload = json.loads(socket.recv_multipart()[-1])
                message = decode_position_state(payload)
                messages.append({'valid_for_map': True, 'source': message.source,
                                 'fix_mode': message.data.fix_mode,
                                 'is_cached': message.data.is_cached})
            except (ValueError, TypeError, KeyError) as error:
                # Contract validators report field names, not coordinate values.
                messages.append({'valid_for_map': False, 'error': str(error)})
    finally:
        socket.close(linger=0)
        context.term()
    return messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.environ.get('OPENROADCODE_ANDROID_BRIDGE_URL') or 'http://127.0.0.1:8766')
    parser.add_argument('--bus', action='store_true', help='Also validate bus messages; run as python -m scripts.probe_android_location --bus')
    args = parser.parse_args()
    report = collect(args.url)
    if args.bus:
        report['position_messages'] = collect_bus()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
