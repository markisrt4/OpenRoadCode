#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import time

from controllers.spotify import (
    MockSpotifyController,
    SpotifyState,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mock Spotify controller component test"
    )

    parser.add_argument(
        "--refresh",
        type=float,
        default=1.0,
        help="Playback-state refresh interval in seconds",
    )

    return parser.parse_args()


def format_duration(milliseconds: int | None) -> str:
    if milliseconds is None:
        return "--:--"

    total_seconds = max(0, milliseconds // 1000)
    minutes, seconds = divmod(total_seconds, 60)

    return f"{minutes}:{seconds:02d}"


def print_state(state: SpotifyState) -> None:
    progress = format_duration(state.progress_ms)
    duration = format_duration(state.duration_ms)

    print()
    print("=" * 60)
    print(f"Status:       {state.status_message}")
    print(f"Available:    {state.is_available}")
    print(f"Playing:      {state.is_playing}")
    print(f"Track:        {state.track_name or '--'}")
    print(f"Artist:       {state.artist_name or '--'}")
    print(f"Album:        {state.album_name or '--'}")
    print(f"Device:       {state.device_name or '--'}")
    print(f"Volume:       {state.volume_percent}%")
    print(f"Progress:     {progress} / {duration}")

    if state.progress_percent is None:
        print("Progress pct: --")
    else:
        print(f"Progress pct: {state.progress_percent:.1f}%")

    print(f"Artwork URL:  {state.album_art_url or '--'}")
    print(f"Spotify URL:  {state.spotify_url or '--'}")
    print("=" * 60)


def print_commands() -> None:
    print()
    print("Commands")
    print("--------")
    print("  s            Show current state")
    print("  p            Play or pause")
    print("  n            Next track")
    print("  b            Previous track")
    print("  v <0-100>    Set volume")
    print("  j <seconds>  Seek to position")
    print("  w <seconds>  Watch playback state")
    print("  h            Show commands")
    print("  q            Quit")
    print()


def watch_state(
    controller: MockSpotifyController,
    duration_seconds: float,
    refresh_seconds: float,
) -> None:
    if duration_seconds <= 0:
        raise ValueError("watch duration must be greater than zero")

    deadline = time.monotonic() + duration_seconds

    while time.monotonic() < deadline:
        state = controller.current_state()

        progress = format_duration(state.progress_ms)
        duration = format_duration(state.duration_ms)

        print(
            f"\r"
            f"{state.status_message:<7} | "
            f"{state.track_name or '--'} | "
            f"{progress}/{duration} | "
            f"volume={state.volume_percent}%",
            end="",
            flush=True,
        )

        time.sleep(refresh_seconds)

    print()


def handle_command(
    controller: MockSpotifyController,
    command: str,
    refresh_seconds: float,
) -> bool:
    parts = command.split()

    if not parts:
        return True

    action = parts[0].lower()

    if action == "q":
        return False

    if action == "h":
        print_commands()
        return True

    if action == "s":
        print_state(controller.current_state())
        return True

    if action == "p":
        controller.play_pause()
        print_state(controller.current_state())
        return True

    if action == "n":
        controller.next_track()
        print_state(controller.current_state())
        return True

    if action == "b":
        controller.previous_track()
        print_state(controller.current_state())
        return True

    if action == "v":
        if len(parts) != 2:
            print("Usage: v <0-100>")
            return True

        try:
            volume_percent = int(parts[1])
        except ValueError:
            print("Volume must be an integer.")
            return True

        controller.set_volume_percent(volume_percent)
        print_state(controller.current_state())
        return True

    if action == "j":
        if len(parts) != 2:
            print("Usage: j <seconds>")
            return True

        try:
            seconds = float(parts[1])
        except ValueError:
            print("Seek position must be a number.")
            return True

        controller.seek_to_position_ms(
            int(seconds * 1000)
        )
        print_state(controller.current_state())
        return True

    if action == "w":
        duration_seconds = 10.0

        if len(parts) == 2:
            try:
                duration_seconds = float(parts[1])
            except ValueError:
                print("Watch duration must be a number.")
                return True

        watch_state(
            controller,
            duration_seconds=duration_seconds,
            refresh_seconds=refresh_seconds,
        )
        return True

    print(f"Unknown command: {action}")
    print("Enter 'h' to display commands.")

    return True


def main() -> None:
    args = parse_args()

    if args.refresh <= 0:
        raise SystemExit("--refresh must be greater than zero")

    controller = MockSpotifyController()

    print("Mock Spotify Controller Component Test")
    print("======================================")
    print_commands()
    print_state(controller.current_state())

    try:
        while True:
            command = input("spotify> ").strip()

            if not handle_command(
                controller,
                command,
                args.refresh,
            ):
                break

    except KeyboardInterrupt:
        print()

    except EOFError:
        print()

    print("Spotify mock component test stopped.")


if __name__ == "__main__":
    main()
