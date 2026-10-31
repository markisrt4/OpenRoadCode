# SPDX-License-Identifier: MIT
"""Resolve first YouTube search result to its normal watch page."""
from __future__ import annotations

import json
import subprocess
from urllib.parse import quote_plus


def first_video_url(query: str, *, timeout: float = 12.0) -> str:
    """Return first YouTube search video, falling back to the search page.

    yt-dlp is optional. No shell, arbitrary URLs, or synchronous UI calls.
    """
    query = query.strip()
    if not query:
        raise ValueError("Song search query is empty")
    fallback = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    try:
        completed = subprocess.run(
            ["yt-dlp", "--dump-single-json", "--flat-playlist", "--playlist-end", "1",
             "--no-warnings", "--no-playlist", f"ytsearch1:{query}"],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
        payload = json.loads(completed.stdout)
        entries = payload.get("entries") or []
        video_id = entries[0].get("id") if entries else None
        if isinstance(video_id, str) and len(video_id) == 11 and all(
            char.isascii() and (char.isalnum() or char in "-_") for char in video_id
        ):
            return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        pass
    return fallback
