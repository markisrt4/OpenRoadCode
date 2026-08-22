// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(function () {
  "use strict";

  const MPH_PER_MPS = 2.2369362920544;
  const FEET_PER_METER = 3.2808398950131;
  const RAD_TO_DEG = 180 / Math.PI;
  const RPM_PER_RAD_S = 60 / (2 * Math.PI);
  const PSI_PER_PA = 0.00014503773773020923;

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

    setValue("vehicle-speed", Number.isFinite(speedMps) ? speedMps * MPH_PER_MPS : null, 1);
    setValue("vehicle-heading", Number.isFinite(headingRad) ? headingRad * RAD_TO_DEG : null, 0, "°");
    setValue("vehicle-altitude", Number.isFinite(position?.altitude_m) ? position.altitude_m * FEET_PER_METER : null, 0, " ft");
    setValue("vehicle-accuracy", position?.accuracy_m, 1, " m");

    if (state?.error) setText("vehicle-sensor-status", `Navigation bus error: ${state.error}`);
    else if (position || motion) setText("vehicle-sensor-status", "Live OpenRoadCode navigation bus · SSE");
  }

  function renderVehicleState(state) {
    const vehicle = state?.vehicle;
    const data = vehicle?.data;
    setValue("vehicle-rpm", Number.isFinite(data?.engine_speed_rad_s) ? data.engine_speed_rad_s * RPM_PER_RAD_S : null, 0);
    setValue("vehicle-obd-speed", Number.isFinite(data?.vehicle_speed_m_s) ? data.vehicle_speed_m_s * MPH_PER_MPS : null, 1);
    setValue("vehicle-throttle", Number.isFinite(data?.throttle_position) ? data.throttle_position * 100 : null, 1);
    setValue("vehicle-boost", Number.isFinite(data?.boost_pressure_pa) ? data.boost_pressure_pa * PSI_PER_PA : null, 1);
    setValue("vehicle-coolant", Number.isFinite(data?.coolant_temperature_k) ? (data.coolant_temperature_k - 273.15) * 9 / 5 + 32 : null, 0);
    setValue("vehicle-load", Number.isFinite(data?.engine_load) ? data.engine_load * 100 : null, 1);
    setValue("vehicle-fuel", Number.isFinite(data?.fuel_level) ? data.fuel_level * 100 : null, 0);
    setValue("vehicle-voltage", data?.control_voltage_v, 1);

    if (state?.error) setText("vehicle-obd-status", `Automotive bus error: ${state.error}`);
    else if (vehicle) setText("vehicle-obd-status", `Live ${vehicle.source} vehicle state · SSE`);
  }

  async function loadState(url, renderer, statusId, label) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      renderer(await response.json());
    } catch (error) {
      setText(statusId, `${label} unavailable: ${error.message || error}`);
    }
  }

  function startEventStream(url, eventName, renderer, statusId, label) {
    if (!("EventSource" in window)) {
      setText(statusId, "SSE is not supported by this browser.");
      return;
    }
    const events = new EventSource(url);
    events.addEventListener(eventName, (event) => {
      try { renderer(JSON.parse(event.data)); }
      catch (error) { setText(statusId, `${label} event error: ${error.message || error}`); }
    });
    events.onerror = () => setText(statusId, `${label} stream reconnecting…`);
  }

  function startVehiclePhoneSensors() {
    const button = document.getElementById("start-vehicle-sensors");
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
        setText("vehicle-sensor-status", "Phone GPS active · publishing navigation.position");
        if (button) { button.disabled = true; button.textContent = "PHONE GPS ACTIVE"; }
      },
      (error) => setText("vehicle-sensor-status", `Phone GPS error: ${error.message || error}`),
    );
    setText("vehicle-sensor-status", "Waiting for phone GPS fix…");
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("start-vehicle-sensors")?.addEventListener("click", startVehiclePhoneSensors);
    loadState("/api/navigation/state", renderNavigationState, "vehicle-sensor-status", "Navigation state");
    loadState("/api/vehicle/state", renderVehicleState, "vehicle-obd-status", "Vehicle state");
    startEventStream("/api/navigation/events", "navigation", renderNavigationState, "vehicle-sensor-status", "Navigation");
    startEventStream("/api/vehicle/events", "vehicle", renderVehicleState, "vehicle-obd-status", "Vehicle");
  });
})();
