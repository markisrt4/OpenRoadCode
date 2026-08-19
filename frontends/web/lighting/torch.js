// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(() => {
  "use strict";

  const button = document.getElementById("phone-torch");
  const status = document.getElementById("phone-torch-status");
  if (!button || !status) return;

  let stream = null;
  let track = null;
  let enabled = false;

  function setStatus(text) {
    status.textContent = text;
  }

  async function ensureTrack() {
    if (track) return track;
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Camera access is not available in this browser");
    }

    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });

    track = stream.getVideoTracks()[0] || null;
    if (!track) throw new Error("No camera video track was returned");

    const capabilities = track.getCapabilities ? track.getCapabilities() : {};
    if (!("torch" in capabilities)) {
      stopTrack();
      throw new Error("Torch control is not supported by this camera/browser");
    }

    return track;
  }

  async function setTorch(nextEnabled) {
    const videoTrack = await ensureTrack();
    await videoTrack.applyConstraints({ advanced: [{ torch: nextEnabled }] });
    enabled = nextEnabled;
    button.textContent = enabled ? "TORCH OFF" : "TORCH ON";
    button.dataset.enabled = enabled ? "1" : "0";
    setStatus(enabled ? "Phone torch is on" : "Phone torch is off");

    if (!enabled) stopTrack();
  }

  function stopTrack() {
    if (stream) {
      for (const mediaTrack of stream.getTracks()) mediaTrack.stop();
    }
    stream = null;
    track = null;
  }

  button.addEventListener("click", async () => {
    button.disabled = true;
    setStatus("Requesting camera/torch access…");
    try {
      await setTorch(!enabled);
    } catch (error) {
      enabled = false;
      button.textContent = "TORCH ON";
      button.dataset.enabled = "0";
      setStatus(error?.message || "Torch control failed");
      stopTrack();
    } finally {
      button.disabled = false;
    }
  });

  window.addEventListener("pagehide", stopTrack);
})();
