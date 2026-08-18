// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  class DeviceOrientationSensorAdapter {
    constructor(endpoint = "/api/navigation/orientation", publishIntervalMs = 150) {
      this._listener = null;
      this._endpoint = endpoint;
      this._publishIntervalMs = publishIntervalMs;
      this._lastPublishedMs = 0;
    }

    get supported() {
      return "DeviceOrientationEvent" in window;
    }

    async requestPermission() {
      if (!this.supported) {
        throw new Error("Device orientation is not supported by this browser.");
      }
      const requestPermission = window.DeviceOrientationEvent.requestPermission;
      if (typeof requestPermission !== "function") return true;
      return (await requestPermission.call(window.DeviceOrientationEvent)) === "granted";
    }

    async _publish(sample) {
      const response = await fetch(this._endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(sample),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `orientation update failed (${response.status})`);
      }
    }

    start(onSample, onError) {
      if (!this.supported) {
        onError?.(new Error("Device orientation is not supported by this browser."));
        return false;
      }
      if (this._listener !== null) return true;

      this._listener = (event) => {
        const sample = {
          heading: event.alpha,
          pitch: event.beta,
          roll: event.gamma,
          absolute: event.absolute === true,
        };
        onSample?.(sample);

        const now = Date.now();
        if (now - this._lastPublishedMs < this._publishIntervalMs) return;
        this._lastPublishedMs = now;
        this._publish(sample).catch((error) => onError?.(error));
      };
      window.addEventListener("deviceorientation", this._listener, true);
      return true;
    }

    stop() {
      if (this._listener === null) return;
      window.removeEventListener("deviceorientation", this._listener, true);
      this._listener = null;
    }
  }

  window.OpenRoadCodeWeb = window.OpenRoadCodeWeb || {};
  window.OpenRoadCodeWeb.DeviceOrientationSensorAdapter = DeviceOrientationSensorAdapter;
})();
