// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  const MPH_PER_MPS = 2.2369362920544;
  const FEET_PER_METER = 3.2808398950131;
  const RAD_TO_DEG = 180 / Math.PI;

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

  function renderNavigationState(state) {
    const position = state?.position?.data;
    const motion = state?.motion?.data;

    const speedMps = Number.isFinite(motion?.ground_speed_m_s)
      ? motion.ground_speed_m_s
      : position?.speed_m_s;
    const headingRad = Number.isFinite(motion?.heading_rad)
      ? motion.heading_rad
      : position?.course_rad;

    setValue(
      "vehicle-speed",
      Number.isFinite(speedMps) ? speedMps * MPH_PER_MPS : null,
      1,
    );
    setValue(
      "vehicle-heading",
      Number.isFinite(headingRad) ? headingRad * RAD_TO_DEG : null,
      0,
      "°",
    );
    setValue(
      "vehicle-altitude",
      Number.isFinite(position?.altitude_m)
        ? position.altitude_m * FEET_PER_METER
        : null,
      0,
      " ft",
    );
    setValue("vehicle-accuracy", position?.accuracy_m, 1, " m");

    if (state?.error) {
      setText("vehicle-sensor-status", `Navigation bus error: ${state.error}`);
    } else if (position || motion) {
      setText("vehicle-sensor-status", "Live OpenRoadCode navigation bus");
    }
  }

  async function refreshNavigationState() {
    try {
      const response = await fetch("/api/navigation/state", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      renderNavigationState(await response.json());
    } catch (error) {
      setText(
        "vehicle-sensor-status",
        `Navigation state unavailable: ${error.message || error}`,
      );
    }
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
      () => {
        setText(
          "vehicle-sensor-status",
          "Phone GPS active · publishing navigation.position",
        );
        if (button) {
          button.disabled = true;
          button.textContent = "PHONE GPS ACTIVE";
        }
      },
      (error) => {
        setText(
          "vehicle-sensor-status",
          `Phone GPS error: ${error.message || error}`,
        );
      },
    );

    if (status) status.textContent = "Waiting for phone GPS fix…";
  }

  document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("start-vehicle-sensors");
    button?.addEventListener("click", startVehiclePhoneSensors);
    refreshNavigationState();
    window.setInterval(refreshNavigationState, 200);
  });
})();
