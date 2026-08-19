# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Server-rendered Spotify screen for the browser frontend."""

from __future__ import annotations

import json
from typing import Any

from flask import render_template_string
from markupsafe import Markup


_TEMPLATE = """
<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{{ style }}</style>
<style>
.lyrics { max-height: 38vh; overflow-y: auto; white-space: normal; scroll-behavior: smooth; }
.lyric-line { padding: .35rem .2rem; opacity: .55; transition: opacity .15s, transform .15s; }
.lyric-line.active { opacity: 1; font-weight: 700; transform: scale(1.02); }
</style>
<header><div class="bar"><a class="back" href="{{ back }}">‹</a><div class="heading"><div class="title">Spotify</div><div class="subtitle">OpenRoadCode media controls</div></div></div></header>
<main id="spotify-app" data-initial-state='{{ initial_state }}'>
  <div id="spotify-status" class="notice">{{ state.status_message or state.availability }}</div>
  {% if state.artwork_uri %}<img id="spotify-art" class="spotify-art" src="{{ state.artwork_uri }}" alt="Album artwork">{% else %}<img id="spotify-art" class="spotify-art" alt="Album artwork" hidden>{% endif %}
  <div id="spotify-track" class="spotify-track">{{ state.title or "Nothing playing" }}</div>
  <div id="spotify-artist" class="spotify-artist">{{ [state.artist, state.album] | select | join(" · ") }}</div>
  <input id="spotify-progress" class="spotify-progress" type="range" min="0" max="1000" value="{{ progress_value }}">
  <div class="spotify-meta"><span id="spotify-position">{{ position_text }}</span><span id="spotify-duration">{{ duration_text }}</span></div>
  <div class="controls"><button id="spotify-previous">◀◀</button><button id="spotify-play" class="primary">{{ "❚❚" if state.playback == "playing" else "▶" }}</button><button id="spotify-next">▶▶</button></div>
  <div class="card"><label>Volume <span id="spotify-volume-label">{{ volume_text }}</span></label><input id="spotify-volume" type="range" min="0" max="100" value="{{ state.volume_percent if state.volume_percent is not none else 50 }}"><div id="spotify-volume-note" class="subtitle"></div></div>
  <div class="controls"><button id="lyrics-button">LYRICS</button><button id="video-button">VIDEO</button></div>
  <div id="spotify-error" class="card" hidden></div>
  <div id="lyrics-card" class="card" hidden><b>Lyrics</b><div id="lyrics" class="lyrics">Loading…</div></div>
</main>
<script src="/web-assets/media/spotify.js"></script>
"""


def _format_time(seconds: object) -> str:
    try:
        total_seconds = max(0, int(float(seconds or 0)))
    except (TypeError, ValueError):
        total_seconds = 0
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes}:{remaining:02d}"


def render_spotify_screen(*, style: str, back: str, state: dict[str, Any]) -> str:
    duration = float(state.get("duration_s") or 0.0)
    position = float(state.get("position_s") or 0.0)
    progress_value = round(position / duration * 1000) if duration > 0 else 0
    volume = state.get("volume_percent")
    initial_state = Markup.escape(json.dumps(state, separators=(",", ":")))
    return render_template_string(
        _TEMPLATE, style=style, back=back, state=state, initial_state=initial_state,
        progress_value=max(0, min(1000, progress_value)), position_text=_format_time(position),
        duration_text=_format_time(duration), volume_text=f"{volume}%" if volume is not None else "--",
    )
