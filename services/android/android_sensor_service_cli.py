# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the Android hardware bridge to ZeroMQ publisher."""

from __future__ import annotations

from hardware_io.android import AndroidSensorBridgeClient
from messaging.zeromq.publisher import ZeroMqPublisher

from .android_sensor_service import AndroidSensorService


def main() -> int:
    client = AndroidSensorBridgeClient()
    if not client.is_available:
        print("[!] Android sensor bridge is unavailable at http://127.0.0.1:8766")
        return 1

    publisher = ZeroMqPublisher()
    service = AndroidSensorService(client, publisher)
    print("[*] Android sensor bridge ready")
    print("[*] Streaming android.imu to OpenRoadCode ZeroMQ")
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
