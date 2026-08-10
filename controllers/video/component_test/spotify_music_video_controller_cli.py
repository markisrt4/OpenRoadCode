from __future__ import annotations

import argparse
import time

from controllers.spotify.mock_spotify_controller import (
    MockSpotifyController,
)
from controllers.video.music_video_controller import MusicVideoController
from controllers.video.youtube_music_video import YouTubeMusicVideo
from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test Spotify-to-YouTube music-video coordination "
            "using the OpenRoadCode mock Spotify controller."
        )
    )

    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Launch Chromium fullscreen.",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8766,
        help="Local HTTP port used by the YouTube player.",
    )

    parser.add_argument(
        "--start-paused",
        action="store_true",
        help=(
            "Start the mock Spotify controller paused to verify that "
            "returning from video playback preserves the paused state."
        ),
    )

    return parser.parse_args()


def print_spotify_state(
    label: str,
    spotify_controller: MockSpotifyController,
) -> None:
    state = spotify_controller.current_state()

    print()
    print(label)
    print("-" * len(label))
    print(
        f"Track: {state.artist_name or 'Unknown artist'} - "
        f"{state.track_name or 'Unknown track'}"
    )
    print(f"Album: {state.album_name or 'Unknown album'}")
    print(f"Playing: {state.is_playing}")
    print(f"Position: {state.progress_ms or 0} ms")


def main() -> int:
    args = parse_args()

    spotify_controller = MockSpotifyController()

    if args.start_paused:
        spotify_controller.pause()

    secret_manager = EnvironmentVariableSecretManager()

    youtube_music_video = YouTubeMusicVideo(
        secret_manager=secret_manager,
        api_key_secret_name="YOUTUBE_API_KEY",
        fullscreen=args.fullscreen,
        port=args.port,
    )

    controller = MusicVideoController(
        spotify_controller=spotify_controller,
        music_video=youtube_music_video,
    )

    print()
    print("Starting Spotify music-video component test")
    print("-------------------------------------------")

    print_spotify_state(
        "Initial Spotify state",
        spotify_controller,
    )

    try:
        print()
        print("Finding and starting music video...")

        if not controller.watch_current_track():
            print("No suitable music video was found or started.")
            return 1

        print_spotify_state(
            "Spotify state while video is active",
            spotify_controller,
        )

        print()
        print("Music video started.")
        print("Press Enter to return to Spotify.")
        print("Press Ctrl+C to stop without resuming Spotify.")

        while controller.is_video_active():
            try:
                user_input = input()

                if user_input == "":
                    controller.return_to_spotify()
                    break

            except EOFError:
                controller.return_to_spotify()
                break

            time.sleep(0.1)

        print_spotify_state(
            "Spotify state after returning",
            spotify_controller,
        )

    except KeyboardInterrupt:
        print()
        print("Stopping music video without returning to Spotify.")
        controller.stop_video()

    finally:
        if controller.is_video_active():
            controller.stop_video()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
