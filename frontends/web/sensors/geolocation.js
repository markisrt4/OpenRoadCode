// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  class GeolocationSensorAdapter {
    constructor(endpoint = "/api/navigation/position") {
      this._watchId = null;
      this._endpoint = endpoint;
    }

    get supported() {
      return "geolocation" in navigator;
    }

    async _publish(sample) {
      const response = await fetch(this._endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(sample),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `position update failed (${response.status})`);
      }
    }

    start(onSample, onError) {
      if (!this.supported) {
        onError?.(new Error("Geolocation is not supported by this browser."));
        return false;
      }
      if (this._watchId !== null) {
        return true;
      }

      this._watchId = navigator.geolocation.watchPosition(
        async (position) => {
          const c = position.coords;
          const sample = {
            latitude: c.latitude,
            longitude: c.longitude,
            altitude: c.altitude,
            speed: c.speed,
            heading: c.heading,
            accuracy: c.accuracy,
          };
          try {
            await this._publish(sample);
            onSample?.(sample);
          } catch (error) {
            onError?.(error);
          }
        },
        (error) => onError?.(error),
        {enableHighAccuracy: true, maximumAge: 1000, timeout: 10000},
      );
      return true;
    }

    stop() {
      if (this._watchId === null || !this.supported) {
        return;
      }
      navigator.geolocation.clearWatch(this._watchId);
      this._watchId = null;
    }
  }

  window.OpenRoadCodeWeb = window.OpenRoadCodeWeb || {};
  window.OpenRoadCodeWeb.GeolocationSensorAdapter = GeolocationSensorAdapter;
})();
