// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  const MPH_PER_MPS = 2.2369362920544;
  const FEET_PER_METER = 3.2808398950131;

  function setValue(id, value, digits = 0, suffix = "") {
    const element = document.getElementById(id);
    if (!element) return;
    element.textContent = Number.isFinite(value)
      ? `${value.toFixed(digits)}${suffix}`
      : "--";
  }

  function setText(id, text) {
    const element = document.getElementById(id);
    if (element) element.textContent = text;
  }

  function startVehiclePhoneSensors() {
    const button = document.getElementById("start-vehicle-sensors");
    const status = document.getElementById("vehicle-sensor-status");

    if (!window.OpenRoadCodeWeb?.GeolocationSensorAdapter) {
      setText("vehicle-sensor-status", "Phone GPS adapter is unavailable.");
      return;
    }

    const gps = new window.OpenRoadCodeWeb.GeolocationSensorAdapter();
    if (!gps.supported) {
      setText("vehicle-sensor-status", "Geolocation is not supported by this browser.");
      return;
    }

    gps.start(
      (sample) => {
        setValue(
          "vehicle-speed",
          Number.isFinite(sample.speed) ? sample.speed * MPH_PER_MPS : null,
          1,
        );
        setValue("vehicle-heading", sample.heading, 0, "°");
        setValue(
          "vehicle-altitude",
          Number.isFinite(sample.altitude) ? sample.altitude * FEET_PER_METER : null,
          0,
          " ft",
        );
        setValue("vehicle-accuracy", sample.accuracy, 1, " m");
        setText("vehicle-sensor-status", "Phone GPS active · publishing navigation.position");
        if (button) {
          button.disabled = true;
          button.textContent = "PHONE GPS ACTIVE";
        }
      },
      (error) => {
        setText("vehicle-sensor-status", `Phone GPS error: ${error.message || error}`);
      },
    );

    if (status) status.textContent = "Waiting for phone GPS fix…";
  }

  document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("start-vehicle-sensors");
    button?.addEventListener("click", startVehiclePhoneSensors);
  });
})();
