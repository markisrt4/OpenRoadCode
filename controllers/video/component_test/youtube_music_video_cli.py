# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import time

from controllers.video.music_video_types import MusicVideo, MusicVideoQuery
from controllers.video.youtube_music_video import YouTubeMusicVideo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search for and play a YouTube music video."
    )
    parser.add_argument("--artist", help="Track artist.")
    parser.add_argument("--title", help="Track title.")
    parser.add_argument("--album", help="Optional album title.")
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--video-id", help="Skip search and play a known video ID.")
    parser.add_argument("--position-ms", type=int, default=0)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--port", type=int, default=8768)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.position_ms < 0:
        raise ValueError("--position-ms cannot be negative")
    if args.video_id is None and (not args.artist or not args.title):
        raise ValueError("Provide --video-id, or both --artist and --title")

    with YouTubeMusicVideo(fullscreen=args.fullscreen, port=args.port) as service:
        if args.video_id is not None:
            video = MusicVideo(
                video_id=args.video_id,
                title=args.title or args.video_id,
                channel_name="Direct component test",
            )
        else:
            query = MusicVideoQuery(
                artist=args.artist,
                title=args.title,
                album=args.album,
                duration_ms=args.duration_ms,
            )
            print(f"Searching YouTube for: {query.artist} - {query.title}")
            video = service.find_video(query)
            if video is None:
                print("No matching video was found.")
                return 1

        print(f"Selected: {video.title}")
        print(f"Channel: {video.channel_name}")
        print(f"Video ID: {video.video_id}")
        print(f"Official candidate: {video.is_official}")
        service.play_video(video, position_ms=args.position_ms)
        print("Video player started. Press Ctrl+C to stop.")

        try:
            while service.is_video_active():
                time.sleep(0.25)
        except KeyboardInterrupt:
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
