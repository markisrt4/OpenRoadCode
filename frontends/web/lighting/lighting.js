// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(() => {
  "use strict";

  const wheel = document.getElementById("lighting-wheel");
  if (!wheel) return;

  const ctx = wheel.getContext("2d");
  const status = document.getElementById("lighting-status");
  const swatch = document.getElementById("lighting-swatch");
  const hexText = document.getElementById("lighting-hex");
  const brightness = document.getElementById("lighting-brightness");
  const brightnessText = document.getElementById("lighting-brightness-value");
  const power = document.getElementById("lighting-power");
  const backend = document.getElementById("lighting-backend");
  let dragging = false;
  let brightnessTimer = null;

  function hsvToRgb(h, s, v) {
    const c = v * s;
    const hp = h / 60;
    const x = c * (1 - Math.abs((hp % 2) - 1));
    let r = 0, g = 0, b = 0;
    if (hp < 1) [r,g,b] = [c,x,0];
    else if (hp < 2) [r,g,b] = [x,c,0];
    else if (hp < 3) [r,g,b] = [0,c,x];
    else if (hp < 4) [r,g,b] = [0,x,c];
    else if (hp < 5) [r,g,b] = [x,0,c];
    else [r,g,b] = [c,0,x];
    const m = v - c;
    return [r,g,b].map(n => Math.round((n + m) * 255));
  }

  function toHex(rgb) {
    return "#" + rgb.map(v => v.toString(16).padStart(2, "0")).join("").toUpperCase();
  }

  function drawWheel() {
    const w = wheel.width, h = wheel.height;
    const image = ctx.createImageData(w, h);
    const cx = w / 2, cy = h / 2, radius = Math.min(cx, cy) - 2;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const dx = x - cx, dy = y - cy;
        const sat = Math.hypot(dx, dy) / radius;
        const i = (y * w + x) * 4;
        if (sat > 1) { image.data[i+3] = 0; continue; }
        const hue = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
        const [r,g,b] = hsvToRgb(hue, sat, 1);
        image.data[i] = r; image.data[i+1] = g; image.data[i+2] = b; image.data[i+3] = 255;
      }
    }
    ctx.putImageData(image, 0, 0);
  }

  function colorAt(clientX, clientY) {
    const rect = wheel.getBoundingClientRect();
    const x = (clientX - rect.left) * wheel.width / rect.width;
    const y = (clientY - rect.top) * wheel.height / rect.height;
    const cx = wheel.width / 2, cy = wheel.height / 2;
    const dx = x - cx, dy = y - cy;
    const radius = Math.min(cx, cy) - 2;
    const sat = Math.hypot(dx, dy) / radius;
    if (sat > 1) return null;
    const hue = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
    return toHex(hsvToRgb(hue, sat, 1));
  }

  async function post(url, payload) {
    const response = await fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    applyState(data);
  }

  function applyState(state) {
    backend.value = state.backend || "emulator";
    power.textContent = state.power_enabled ? "TURN OFF" : "TURN ON";
    power.dataset.enabled = state.power_enabled ? "1" : "0";
    brightness.value = state.brightness_percent;
    brightnessText.textContent = `${state.brightness_percent}%`;
    swatch.style.background = state.color;
    hexText.textContent = state.color;
    status.textContent = `${state.backend === "ble" ? "Physical BLE" : "Emulator"} · ${state.connection_status}` + (state.device_address ? ` · ${state.device_address}` : "");
  }

  async function refresh() {
    try {
      const response = await fetch("/api/lighting/state", {cache:"no-store"});
      if (response.ok) applyState(await response.json());
    } catch (_) {}
  }

  async function sendColor(event) {
    const color = colorAt(event.clientX, event.clientY);
    if (!color) return;
    swatch.style.background = color;
    hexText.textContent = color;
    try { await post("/api/lighting/command", {command:"color", value:color}); }
    catch (err) { status.textContent = err.message; }
  }

  wheel.addEventListener("pointerdown", e => { dragging = true; wheel.setPointerCapture(e.pointerId); sendColor(e); });
  wheel.addEventListener("pointermove", e => { if (dragging) sendColor(e); });
  wheel.addEventListener("pointerup", () => { dragging = false; });
  wheel.addEventListener("pointercancel", () => { dragging = false; });

  brightness.addEventListener("input", () => {
    brightnessText.textContent = `${brightness.value}%`;
    clearTimeout(brightnessTimer);
    brightnessTimer = setTimeout(async () => {
      try { await post("/api/lighting/command", {command:"brightness", value:Number(brightness.value)}); }
      catch (err) { status.textContent = err.message; }
    }, 100);
  });

  power.addEventListener("click", async () => {
    try { await post("/api/lighting/command", {command:"power", value:power.dataset.enabled !== "1"}); }
    catch (err) { status.textContent = err.message; }
  });

  backend.addEventListener("change", async () => {
    status.textContent = backend.value === "ble" ? "Binding physical BLE…" : "Switching to emulator…";
    try { await post("/api/lighting/bind", {backend:backend.value}); }
    catch (err) { status.textContent = err.message; backend.value = "emulator"; }
  });

  drawWheel();
  refresh();
  setInterval(refresh, 2000);
})();
