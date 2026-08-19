// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(() => {
  "use strict";
  const root = document.getElementById("spotify-app");
  if (!root) return;

  let state = {};
  try { state = JSON.parse(root.dataset.initialState || "{}"); } catch (error) { console.error(error); }
  let seeking = false;
  let syncedLyrics = [];
  let activeLyricIndex = -1;
  let anchorPosition = Number(state.position_s) || 0;
  let anchorTime = performance.now();
  const byId = (id) => document.getElementById(id);

  function fmt(seconds) {
    const value = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
  }

  function estimatedPosition() {
    let position = anchorPosition;
    if (state.playback === "playing") position += (performance.now() - anchorTime) / 1000;
    return Math.min(Number(state.duration_s) || position, Math.max(0, position));
  }

  function setAnchor(position) {
    anchorPosition = Number(position) || 0;
    anchorTime = performance.now();
  }

  function showError(message) {
    const box = byId("spotify-error");
    box.textContent = message;
    box.hidden = false;
    console.error(message);
  }

  function render(nextState) {
    const previousMedia = state.media_uri;
    state = nextState || {};
    setAnchor(state.position_s);
    byId("spotify-status").textContent = state.status_message || state.availability || "Spotify";
    byId("spotify-track").textContent = state.title || "Nothing playing";
    byId("spotify-artist").textContent = [state.artist, state.album].filter(Boolean).join(" · ");
    const art = byId("spotify-art");
    if (state.artwork_uri) { if (art.getAttribute("src") !== state.artwork_uri) art.src = state.artwork_uri; art.hidden = false; } else art.hidden = true;
    byId("spotify-play").textContent = state.playback === "playing" ? "❚❚" : "▶";
    byId("spotify-duration").textContent = fmt(state.duration_s);

    const volume = byId("spotify-volume");
    const supportsVolume = state.supports_volume !== false;
    volume.disabled = !supportsVolume;
    byId("spotify-volume-note").textContent = supportsVolume ? "" : "Active Spotify device does not allow remote volume control.";
    if (state.volume_percent != null) { volume.value = state.volume_percent; byId("spotify-volume-label").textContent = `${state.volume_percent}%`; }

    if (previousMedia && previousMedia !== state.media_uri) {
      syncedLyrics = [];
      activeLyricIndex = -1;
      byId("lyrics-card").hidden = true;
    }
  }

  async function readJson(response) {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  async function command(name, value = null) {
    try {
      const response = await fetch("/api/media/spotify/command", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({command: name, value})});
      await readJson(response);
    } catch (error) { showError(`Spotify command failed: ${error.message}`); refresh(); }
  }

  async function refresh() {
    try { render(await readJson(await fetch("/api/media/spotify/state", {cache: "no-store"}))); }
    catch (error) { showError(`Spotify refresh failed: ${error.message}`); }
  }

  byId("spotify-previous").addEventListener("click", () => { setAnchor(0); command("previous"); setTimeout(refresh, 350); });
  byId("spotify-next").addEventListener("click", () => { setAnchor(0); command("next"); setTimeout(refresh, 350); });
  byId("spotify-play").addEventListener("click", () => {
    const playing = state.playback === "playing";
    if (playing) { setAnchor(estimatedPosition()); state.playback = "paused"; } else { state.playback = "playing"; anchorTime = performance.now(); }
    byId("spotify-play").textContent = state.playback === "playing" ? "❚❚" : "▶";
    command(playing ? "pause" : "play");
  });

  const progress = byId("spotify-progress");
  progress.addEventListener("input", () => { seeking = true; byId("spotify-position").textContent = fmt((Number(state.duration_s) || 0) * Number(progress.value) / 1000); });
  progress.addEventListener("change", () => {
    const position = (Number(state.duration_s) || 0) * Number(progress.value) / 1000;
    seeking = false; setAnchor(position); command("seek", position);
  });

  const volume = byId("spotify-volume");
  volume.addEventListener("input", () => { byId("spotify-volume-label").textContent = `${volume.value}%`; });
  volume.addEventListener("change", () => { if (!volume.disabled) command("volume", Number(volume.value)); });

  function renderLyrics(data) {
    const box = byId("lyrics");
    syncedLyrics = Array.isArray(data.synced_lines) ? data.synced_lines : [];
    activeLyricIndex = -1;
    if (syncedLyrics.length) {
      box.innerHTML = "";
      syncedLyrics.forEach((line, index) => {
        const div = document.createElement("div");
        div.className = "lyric-line";
        div.dataset.index = String(index);
        div.textContent = line.text;
        box.appendChild(div);
      });
      updateLyrics();
      return;
    }
    const plain = Array.isArray(data.plain_lines) ? data.plain_lines : [];
    box.textContent = plain.length ? plain.join("\n") : "No lyrics found.";
  }

  function updateLyrics() {
    if (!syncedLyrics.length) return;
    const positionMs = estimatedPosition() * 1000;
    let index = -1;
    for (let i = 0; i < syncedLyrics.length; i += 1) { if (syncedLyrics[i].time_ms <= positionMs) index = i; else break; }
    if (index === activeLyricIndex) return;
    const oldLine = byId("lyrics").querySelector(".lyric-line.active");
    if (oldLine) oldLine.classList.remove("active");
    activeLyricIndex = index;
    if (index >= 0) {
      const line = byId("lyrics").querySelector(`[data-index="${index}"]`);
      if (line) { line.classList.add("active"); line.scrollIntoView({block: "center", behavior: "smooth"}); }
    }
  }

  byId("lyrics-button").addEventListener("click", async () => {
    const card = byId("lyrics-card"); card.hidden = false; byId("lyrics").textContent = "Loading…";
    try { renderLyrics(await readJson(await fetch("/api/media/spotify/lyrics", {cache: "no-store"}))); }
    catch (error) { byId("lyrics").textContent = `Lyrics failed: ${error.message}`; }
  });

  byId("video-button").addEventListener("click", () => {
    if (!state.title || !state.artist) return;
    const query = encodeURIComponent(`${state.artist} ${state.title} official music video`);
    window.open(`https://www.youtube.com/results?search_query=${query}`, "_blank", "noopener");
  });

  function animate() {
    const position = estimatedPosition();
    if (!seeking) {
      byId("spotify-position").textContent = fmt(position);
      const duration = Number(state.duration_s) || 0;
      progress.value = duration ? Math.round(position / duration * 1000) : 0;
    }
    updateLyrics();
    requestAnimationFrame(animate);
  }

  render(state);
  animate();
  window.setInterval(refresh, 3000);
})();
