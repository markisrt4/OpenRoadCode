# SPDX-License-Identifier: MIT
"""Resolve first YouTube search result to its normal watch page."""

from __future__ import annotations

import json
import subprocess
from urllib.parse import quote_plus, urlencode
from urllib.request import urlopen


def first_video_url(query: str, *, api_key: str | None = None, timeout: float = 12.0) -> str:
    """Return first YouTube search video, falling back to the search page.

    Use the configured Data API key first, then optional yt-dlp.
    """
    query = query.strip()
    if not query:
        raise ValueError("Song search query is empty")
    fallback = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    if api_key:
        parameters = urlencode(
            {"part": "id", "type": "video", "maxResults": 1, "q": query, "key": api_key}
        )
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?{parameters}"
            with urlopen(url, timeout=5) as response:
                payload = json.load(response)
            match = _watch_url(payload["items"][0]["id"]["videoId"])
            if match:
                return match
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            pass
    try:
        completed = subprocess.run(
            [
                "yt-dlp",
                "--dump-single-json",
                "--flat-playlist",
                "--playlist-end",
                "1",
                "--no-warnings",
                "--no-playlist",
                f"ytsearch1:{query}",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        payload = json.loads(completed.stdout)
        entries = payload.get("entries") or []
        if entries:
            match = _watch_url(entries[0].get("id"))
            if match:
                return match
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        pass
    return fallback


def _watch_url(video_id: object) -> str | None:
    if (
        isinstance(video_id, str)
        and len(video_id) == 11
        and all(char.isascii() and (char.isalnum() or char in "-_") for char in video_id)
    ):
        return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
    return None
