# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the Android hardware bridge to ZeroMQ publisher."""

from __future__ import annotations

import argparse

from hardware_io.android import AndroidSensorBridgeClient
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT
from messaging.zeromq.publisher import ZeroMqPublisher

from .android_sensor_service import AndroidSensorService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish Android sensors onto the OpenRoadCode bus")
    parser.add_argument(
        "--publisher-endpoint",
        default=LOCAL_PUBLISHER_ENDPOINT,
        help="ZeroMQ broker publisher endpoint (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    client = AndroidSensorBridgeClient()
    if not client.is_available:
        print("[!] Android sensor bridge is unavailable at http://127.0.0.1:8766")
        return 1

    publisher = ZeroMqPublisher(endpoint=args.publisher_endpoint)
    service = AndroidSensorService(client, publisher)
    print("[*] Android sensor bridge ready")
    print(f"[*] Publishing Android sensors to {args.publisher_endpoint}")
    print("[*] Topics: IMU, magnetic field, barometric state")
    print("[*] Press Ctrl+C to stop")
    try:
        service.run()
    except KeyboardInterrupt:
        print("\n[*] Stopping Android sensor service...")
    finally:
        publisher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
