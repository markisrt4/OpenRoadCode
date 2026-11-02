#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read Android Bridge location readiness without printing coordinates."""
import argparse
import json
import os
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.environ.get('OPENROADCODE_ANDROID_BRIDGE_URL') or 'http://127.0.0.1:8766')
    args = parser.parse_args()
    print(json.dumps(collect(args.url), indent=2))


if __name__ == '__main__':
    main()
