# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Server-rendered Spotify screen for the browser frontend."""

from __future__ import annotations

from typing import Any

from flask import render_template_string


_TEMPLATE = """
<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{{ style }}</style>
<header>
  <div class="bar">
    <a class="back" href="{{ back }}">‹</a>
    <div class="heading">
      <div class="title">Spotify</div>
      <div class="subtitle">OpenRoadCode media controls</div>
    </div>
  </div>
</header>
<main>
  <div id="spotify-status" class="notice">{{ state.status_message or state.availability }}</div>

  {% if state.artwork_uri %}
    <img id="spotify-art" class="spotify-art" src="{{ state.artwork_uri }}" alt="Album artwork">
  {% else %}
    <img id="spotify-art" class="spotify-art" alt="Album artwork" hidden>
  {% endif %}

  <div id="spotify-track" class="spotify-track">{{ state.title or "Nothing playing" }}</div>
  <div id="spotify-artist" class="spotify-artist">
    {{ [state.artist, state.album] | select | join(" · ") }}
  </div>

  <input id="spotify-progress" class="spotify-progress" type="range" min="0" max="1000"
         value="{{ progress_value }}">
  <div class="spotify-meta">
    <span id="spotify-position">{{ position_text }}</span>
    <span id="spotify-duration">{{ duration_text }}</span>
  </div>

  <div class="controls">
    <button id="spotify-previous">◀◀</button>
    <button id="spotify-play" class="primary">{{ "❚❚" if state.playback == "playing" else "▶" }}</button>
    <button id="spotify-next">▶▶</button>
  </div>

  <div class="card">
    <label>Volume <span id="spotify-volume-label">{{ volume_text }}</span></label>
    <input id="spotify-volume" type="range" min="0" max="100" value="{{ state.volume_percent if state.volume_percent is not none else 50 }}">
  </div>

  <div class="controls">
    <button id="lyrics-button">LYRICS</button>
    <button disabled title="Video controller integration comes next">VIDEO</button>
  </div>

  <div id="spotify-error" class="card" hidden></div>
  <div id="lyrics-card" class="card" hidden>
    <b>Lyrics</b>
    <div id="lyrics" class="lyrics">Loading…</div>
  </div>
</main>

<script>
(() => {
  let state = {{ state | tojson }};
  let seeking = false;

  const byId = (id) => document.getElementById(id);
  const fmt = (seconds) => {
    const value = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
  };

  function showError(message) {
    const box = byId('spotify-error');
    box.textContent = message;
    box.hidden = false;
  }

  function render(nextState) {
    state = nextState;
    byId('spotify-status').textContent = nextState.status_message || nextState.availability || 'Spotify';
    byId('spotify-track').textContent = nextState.title || 'Nothing playing';
    byId('spotify-artist').textContent = [nextState.artist, nextState.album].filter(Boolean).join(' · ');

    const art = byId('spotify-art');
    if (nextState.artwork_uri) {
      if (art.src !== nextState.artwork_uri) art.src = nextState.artwork_uri;
      art.hidden = false;
    } else {
      art.hidden = true;
    }

    byId('spotify-play').textContent = nextState.playback === 'playing' ? '❚❚' : '▶';
    byId('spotify-position').textContent = fmt(nextState.position_s);
    byId('spotify-duration').textContent = fmt(nextState.duration_s);

    if (!seeking) {
      const duration = Number(nextState.duration_s) || 0;
      byId('spotify-progress').value = duration
        ? Math.round((Number(nextState.position_s) || 0) / duration * 1000)
        : 0;
    }

    if (nextState.volume_percent != null) {
      byId('spotify-volume').value = nextState.volume_percent;
      byId('spotify-volume-label').textContent = `${nextState.volume_percent}%`;
    }
  }

  async function readJson(response) {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  async function command(name, value = null) {
    try {
      const response = await fetch('/api/media/spotify/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: name, value}),
      });
      render(await readJson(response));
    } catch (error) {
      showError(`Spotify command failed: ${error.message}`);
    }
  }

  async function refresh() {
    try {
      const response = await fetch('/api/media/spotify/state', {cache: 'no-store'});
      render(await readJson(response));
    } catch (error) {
      showError(`Spotify refresh failed: ${error.message}`);
    }
  }

  byId('spotify-previous').addEventListener('click', () => command('previous'));
  byId('spotify-next').addEventListener('click', () => command('next'));
  byId('spotify-play').addEventListener('click', () => command(state.playback === 'playing' ? 'pause' : 'play'));

  const progress = byId('spotify-progress');
  progress.addEventListener('input', () => { seeking = true; });
  progress.addEventListener('change', () => {
    const duration = Number(state.duration_s) || 0;
    seeking = false;
    if (duration) command('seek', duration * Number(progress.value) / 1000);
  });

  const volume = byId('spotify-volume');
  volume.addEventListener('change', () => command('volume', Number(volume.value)));

  byId('lyrics-button').addEventListener('click', async () => {
    const card = byId('lyrics-card');
    const box = byId('lyrics');
    card.hidden = false;
    box.textContent = 'Loading…';
    try {
      const response = await fetch('/api/media/spotify/lyrics', {cache: 'no-store'});
      const data = await readJson(response);
      const lines = data.plain_lines?.length
        ? data.plain_lines
        : (data.synced_lines || []).map((line) => line.text);
      box.textContent = lines.length ? lines.join('\n') : 'No lyrics found.';
    } catch (error) {
      box.textContent = `Lyrics failed: ${error.message}`;
    }
  });

  render(state);
  window.setInterval(refresh, 3000);
})();
</script>
"""


def _format_time(seconds: object) -> str:
    try:
        total_seconds = max(0, int(float(seconds or 0)))
    except (TypeError, ValueError):
        total_seconds = 0
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes}:{remaining:02d}"


def render_spotify_screen(*, style: str, back: str, state: dict[str, Any]) -> str:
    """Render the initial Spotify state on the server, then enable live JS updates."""
    duration = float(state.get("duration_s") or 0.0)
    position = float(state.get("position_s") or 0.0)
    progress_value = round(position / duration * 1000) if duration > 0 else 0
    volume = state.get("volume_percent")

    return render_template_string(
        _TEMPLATE,
        style=style,
        back=back,
        state=state,
        progress_value=max(0, min(1000, progress_value)),
        position_text=_format_time(position),
        duration_text=_format_time(duration),
        volume_text=f"{volume}%" if volume is not None else "--",
    )
