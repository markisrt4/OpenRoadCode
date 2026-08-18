// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  class GeolocationSensorAdapter {
    constructor() {
      this._watchId = null;
    }

    get supported() {
      return "geolocation" in navigator;
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
        (position) => {
          const coordinates = position.coords;
          onSample?.({
            latitude: coordinates.latitude,
            longitude: coordinates.longitude,
            accuracyM: coordinates.accuracy,
            altitudeM: coordinates.altitude,
            altitudeAccuracyM: coordinates.altitudeAccuracy,
            headingDeg: coordinates.heading,
            speedMps: coordinates.speed,
            timestampMs: position.timestamp,
          });
        },
        (error) => onError?.(error),
        {
          enableHighAccuracy: true,
          maximumAge: 1000,
          timeout: 10000,
        },
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
