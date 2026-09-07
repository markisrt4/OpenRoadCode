# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Verify ORC navigation bus delivery into the Earth geolocation bridge."""
from __future__ import annotations

import argparse
import math
import time

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from messaging.contracts.navigation import (MOTION_STATE_TOPIC, POSITION_STATE_TOPIC, decode_motion_state, decode_position_state)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=30.0)
    parser.add_argument('--endpoint', default=LOCAL_SUBSCRIBER_ENDPOINT)
    parser.add_argument('--source', default='earth-route-simulator')
    args = parser.parse_args()
    client = ChromiumDevToolsClient(port=9223)
    bridge = EarthGeolocationBridge(client)
    if not bridge.install():
        print('[earth-bus] FAIL: Earth bridge unavailable')
        return 2
    print('[earth-bus] Existing watchers:', bridge.registration_count(), flush=True)
    print('[earth-bus] Activate Earth location manually if necessary. This test never clicks or changes the camera.', flush=True)
    latest = {'position': None, 'motion': None, 'received': 0, 'pushed': 0, 'failed': 0, 'last': None}

    def position(message):
        if message.source != args.source:
            return
        data = message.data
        if data.latitude_rad is None or data.longitude_rad is None:
            return
        latest['position'] = message
        latest['received'] += 1

    def motion(message):
        if message.source == args.source:
            latest['motion'] = message

    dispatcher = MessageDispatcher(ZeroMqSubscriber(args.endpoint))
    dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, position)
    dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, motion)
    dispatcher.start()
    deadline = time.monotonic() + args.seconds
    last_report = 0.0
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            message = latest['position']
            if message is not None and message is not latest['last']:
                latest['last'] = message
                data = message.data
                motion_message = latest['motion']
                motion_data = motion_message.data if motion_message is not None else None
                heading = motion_data.course_rad if motion_data is not None else None
                speed = motion_data.ground_speed_m_s if motion_data is not None else None
                lat = math.degrees(data.latitude_rad)
                lon = math.degrees(data.longitude_rad)
                ok = bridge.push_position(lat, lon, accuracy_m=data.accuracy_m or 5.0, altitude_m=data.altitude_m, heading_deg=math.degrees(heading) if heading is not None else None, speed_m_s=speed)
                latest['pushed' if ok else 'failed'] += 1
                if now - last_report >= 1.0 or not ok:
                    print(f'[earth-bus] source={message.source} lat={lat:.6f} lon={lon:.6f} received={latest["received"]} pushed={latest["pushed"]} failed={latest["failed"]} watchers={bridge.registration_count()}', flush=True)
                    last_report = now
            time.sleep(0.02)
    except KeyboardInterrupt:
        print('\n[earth-bus] stopped', flush=True)
    finally:
        dispatcher.close()
    print(f'[earth-bus] summary received={latest["received"]} pushed={latest["pushed"]} failed={latest["failed"]}', flush=True)
    return 0 if latest['received'] and latest['pushed'] and not latest['failed'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
