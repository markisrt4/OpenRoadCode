#!/usr/bin/env python3

from __future__ import annotations

import argparse
import time

from controllers.spotify import (
    SpotifyState,
    SpotifyWebApiController,
)
from protocols.spotify import (
    SpotifyAuth,
    SpotifyTokenStore,
    SpotifyWebApiClient,
    load_spotify_config_from_secrets,
)
from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spotify Web API controller component test"
    )

    parser.add_argument(
        "--refresh",
        type=float,
        default=2.0,
        help="Playback-state refresh interval in seconds",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Read playback state once and exit",
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
    print("=" * 72)
    print(f"Status:       {state.status_message}")
    print(f"Available:    {state.is_available}")
    print(f"Playing:      {state.is_playing}")
    print(f"Track:        {state.track_name or '--'}")
    print(f"Artist:       {state.artist_name or '--'}")
    print(f"Album:        {state.album_name or '--'}")
    print(f"Device:       {state.device_name or '--'}")
    print(f"Volume:       {state.volume_percent if state.volume_percent is not None else '--'}")
    print(f"Progress:     {progress} / {duration}")

    if state.progress_percent is None:
        print("Progress pct: --")
    else:
        print(f"Progress pct: {state.progress_percent:.1f}%")

    print(f"Artwork URL:  {state.album_art_url or '--'}")
    print(f"Spotify URL:  {state.spotify_url or '--'}")
    print("=" * 72)


def create_controller() -> SpotifyWebApiController:
    config = load_spotify_config_from_secrets(
        EnvironmentVariableSecretManager()
    )
    if config is None:
        raise RuntimeError(
            "Spotify is not configured. Expected secret: "
            "SPOTIFY_CLIENT_ID"
        )
    token_store = SpotifyTokenStore()

    auth = SpotifyAuth(
        config=config,
        token_store=token_store,
    )

    client = SpotifyWebApiClient(auth)

    return SpotifyWebApiController(client)


def main() -> None:
    args = parse_args()

    if args.refresh <= 0:
        raise SystemExit("--refresh must be greater than zero")

    controller = create_controller()

    print("Spotify Web API Controller Component Test")
    print("=========================================")
    print()
    print("Reading current Spotify playback state...")

    try:
        while True:
            state = controller.current_state()
            print_state(state)

            if args.once:
                break

            time.sleep(args.refresh)

    except KeyboardInterrupt:
        print("\nSpotify component test stopped.")

    except Exception as exc:
        print(f"\nSpotify component test failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
