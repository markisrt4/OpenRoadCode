// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(() => {
  "use strict";

  const root = document.getElementById("spotify-app");
  if (!root) return;

  let state;
  try {
    state = JSON.parse(root.dataset.initialState || "{}");
  } catch (error) {
    console.error("Invalid Spotify initial state", error);
    state = {};
  }

  let seeking = false;
  const byId = (id) => document.getElementById(id);

  function fmt(seconds) {
    const value = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
  }

  function showError(message) {
    const box = byId("spotify-error");
    if (!box) return;
    box.textContent = message;
    box.hidden = false;
    console.error(message);
  }

  function render(nextState) {
    state = nextState || {};
    byId("spotify-status").textContent = state.status_message || state.availability || "Spotify";
    byId("spotify-track").textContent = state.title || "Nothing playing";
    byId("spotify-artist").textContent = [state.artist, state.album].filter(Boolean).join(" · ");

    const art = byId("spotify-art");
    if (state.artwork_uri) {
      if (art.getAttribute("src") !== state.artwork_uri) art.src = state.artwork_uri;
      art.hidden = false;
    } else {
      art.hidden = true;
    }

    byId("spotify-play").textContent = state.playback === "playing" ? "❚❚" : "▶";
    byId("spotify-position").textContent = fmt(state.position_s);
    byId("spotify-duration").textContent = fmt(state.duration_s);

    if (!seeking) {
      const duration = Number(state.duration_s) || 0;
      byId("spotify-progress").value = duration
        ? Math.round((Number(state.position_s) || 0) / duration * 1000)
        : 0;
    }

    if (state.volume_percent != null) {
      byId("spotify-volume").value = state.volume_percent;
      byId("spotify-volume-label").textContent = `${state.volume_percent}%`;
    }
  }

  async function readJson(response) {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  async function command(name, value = null) {
    try {
      const response = await fetch("/api/media/spotify/command", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({command: name, value}),
      });
      render(await readJson(response));
    } catch (error) {
      showError(`Spotify command failed: ${error.message}`);
    }
  }

  async function refresh() {
    try {
      const response = await fetch("/api/media/spotify/state", {cache: "no-store"});
      render(await readJson(response));
    } catch (error) {
      showError(`Spotify refresh failed: ${error.message}`);
    }
  }

  byId("spotify-previous").addEventListener("click", () => command("previous"));
  byId("spotify-next").addEventListener("click", () => command("next"));
  byId("spotify-play").addEventListener("click", () => command(state.playback === "playing" ? "pause" : "play"));

  const progress = byId("spotify-progress");
  progress.addEventListener("input", () => { seeking = true; });
  progress.addEventListener("change", () => {
    const duration = Number(state.duration_s) || 0;
    seeking = false;
    if (duration) command("seek", duration * Number(progress.value) / 1000);
  });

  const volume = byId("spotify-volume");
  volume.addEventListener("input", () => {
    byId("spotify-volume-label").textContent = `${volume.value}%`;
  });
  volume.addEventListener("change", () => command("volume", Number(volume.value)));

  byId("lyrics-button").addEventListener("click", async () => {
    const card = byId("lyrics-card");
    const box = byId("lyrics");
    card.hidden = false;
    box.textContent = "Loading…";
    try {
      const response = await fetch("/api/media/spotify/lyrics", {cache: "no-store"});
      const data = await readJson(response);
      const plain = Array.isArray(data.plain_lines) ? data.plain_lines : [];
      const synced = Array.isArray(data.synced_lines) ? data.synced_lines : [];
      const lines = plain.length ? plain : synced.map((line) => line.text);
      box.textContent = lines.length ? lines.join("\n") : "No lyrics found.";
    } catch (error) {
      box.textContent = `Lyrics failed: ${error.message}`;
    }
  });

  render(state);
  refresh();
  window.setInterval(refresh, 3000);
})();
