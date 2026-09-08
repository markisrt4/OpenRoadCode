# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import sys

from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.streaming_radio_controller import StreamingRadioController
from hardware_io.audio.mpv_streaming_audio_player import MpvStreamingAudioPlayer


DEFAULT_LATITUDE = 42.3314
DEFAULT_LONGITUDE = -83.0458
DEFAULT_RADIUS_KM = 80.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover and play internet radio stations through Radio Browser."
    )
    parser.add_argument("--state", default="Michigan", help="State/region name")
    parser.add_argument("--country", default="US", help="Two-letter country code")
    parser.add_argument("--limit", type=int, default=25, help="Maximum stations to list")
    parser.add_argument("--latitude", type=float, default=DEFAULT_LATITUDE)
    parser.add_argument("--longitude", type=float, default=DEFAULT_LONGITUDE)
    parser.add_argument("--radius-km", type=float, default=DEFAULT_RADIUS_KM)
    parser.add_argument(
        "--regional",
        action="store_true",
        help="List the state/region instead of nearby stations",
    )
    parser.add_argument(
        "--search",
        metavar="TEXT",
        help="Search station names instead of local/regional discovery",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    directory = RadioBrowserDirectory(timeout_s=10.0)

    try:
        if args.search:
            stations = directory.search(args.search, limit=args.limit)
            discovery_label = f'name search: "{args.search}"'
        elif args.regional:
            stations = directory.stations_by_region(
                state=args.state,
                country_code=args.country,
                limit=args.limit,
            )
            discovery_label = f"regional: {args.state}, {args.country}"
        else:
            stations = directory.stations_near(
                latitude=args.latitude,
                longitude=args.longitude,
                radius_km=args.radius_km,
                state=args.state,
                country_code=args.country,
                limit=args.limit,
            )
            discovery_label = (
                f"local: {args.radius_km:g} km around "
                f"{args.latitude:.4f}, {args.longitude:.4f}"
            )
    except Exception as exc:
        print(f"Station discovery failed: {exc}", file=sys.stderr)
        return 1

    if not stations:
        print("No stations found.")
        return 1

    print()
    print("OpenRoadCode streaming radio smoke test")
    print("======================================")
    print(discovery_label)
    print()
    for index, station in enumerate(stations, start=1):
        details = []
        if station.codec:
            details.append(station.codec)
        if station.bitrate_kbps is not None:
            details.append(f"{station.bitrate_kbps} kbps")
        if station.state:
            details.append(station.state)
        if station.latitude is not None and station.longitude is not None:
            details.append(f"{station.latitude:.2f},{station.longitude:.2f}")
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"{index:2d}. {station.name}{suffix}")

    print()
    selection = input("Station number to play, or q to quit: ").strip()
    if selection.lower() in {"q", "quit", "exit"}:
        return 0

    try:
        station_index = int(selection) - 1
    except ValueError:
        print("Invalid selection.", file=sys.stderr)
        return 2

    if station_index < 0 or station_index >= len(stations):
        print("Selection is out of range.", file=sys.stderr)
        return 2

    station = stations[station_index]
    controller = StreamingRadioController(MpvStreamingAudioPlayer())

    try:
        controller.play(station)
        print(f"Playing: {station.name}")
        print("Press Enter to stop.")
        input()
    except Exception as exc:
        print(f"Playback failed: {exc}", file=sys.stderr)
        return 1
    finally:
        controller.stop()

    print("Stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
