// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  class DeviceOrientationSensorAdapter {
    constructor() {
      this._listener = null;
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

    start(onSample, onError) {
      if (!this.supported) {
        onError?.(new Error("Device orientation is not supported by this browser."));
        return false;
      }
      if (this._listener !== null) return true;

      this._listener = (event) => onSample?.({
        heading: event.alpha,
        pitch: event.beta,
        roll: event.gamma,
        absolute: event.absolute === true,
      });
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
