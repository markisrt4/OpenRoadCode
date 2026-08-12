#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


import time

from hardware_io.gps import GpsData, GpsReader


_last_status: str | None = None


def gps_data_received(data: GpsData) -> None:
    global _last_status

    if not data.has_fix:
        visible = _display_count(data.satellites_visible)
        used = _display_count(data.satellites_used)
        status = (
            "Waiting for GPS fix... "
            f"satellites visible={visible}, used={used}, mode={data.mode or 1}"
        )

        if status != _last_status:
            print(status)
            _last_status = status
        return

    _last_status = "fix"
    fix_type = "3D" if data.mode == 3 else "2D"
    print(
        f"{fix_type} fix: "
        f"lat={data.latitude} "
        f"lon={data.longitude} "
        f"alt={data.altitude} "
        f"speed={data.speed} "
        f"track={data.track} "
        f"satellites_used={_display_count(data.satellites_used)}"
    )


def _display_count(value: int | None) -> str:
    return "unknown" if value is None else str(value)


def main() -> None:
    reader = GpsReader(callback=gps_data_received)

    print("Connecting to gpsd at 127.0.0.1:2947...")

    try:
        reader.start()

        print("Connected. Waiting for GPS reports.")
        print("A first fix may take several minutes, especially indoors.")
        print("Press Ctrl+C to exit.\n")

        while True:
            time.sleep(1)

    except ConnectionRefusedError:
        print("Unable to connect to gpsd at 127.0.0.1:2947.")
        print("Start gpsd first with component_test/start_gpsd.sh.")
        raise SystemExit(1)

    except OSError as error:
        print(f"Unable to connect to gpsd: {error}")
        raise SystemExit(1)

    except KeyboardInterrupt:
        print("\nStopping GPS reader...")

    finally:
        reader.stop()


if __name__ == "__main__":
    main()
