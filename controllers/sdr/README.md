# SDR controllers

This package contains application-facing SDR++ integration that is shared by OpenRoadCode frontends.

## Responsibilities

- `sdrpp_control.py` exposes display controls such as waterfall, band plan, FFT peak hold, auto range, and theme selection without leaking the SDR++ remote-control wire protocol into the UI.
- `sdr_telemetry_monitor.py` combines read-only SDR++ telemetry with radio-specific metadata such as FM RDS.
- `sdr_telemetry_worker.py` polls telemetry off the UI thread and publishes the latest snapshot for frontends.
- SDR++ process launch and lifecycle remain in `apps/launchers/sdrpp_launcher.py`; they do not belong in this controller package.

## SDR++ local interfaces

OpenRoadCode deliberately separates three local interfaces:

| Port | Interface | Purpose |
| --- | --- | --- |
| 4532 | RigCTL | RF tuning, mode/bandwidth, receiver state, and FM RDS |
| 4533 | ORC SDR++ remote control | Waterfall, band plan, FFT hold, auto range, themes |
| 4534 | ORC telemetry | Read-only signal, SNR, FFT, VFO, frequency, and bandwidth telemetry |

Keeping these interfaces separate prevents UI/display controls and telemetry from becoming accidental extensions of the radio backend.

## Frontend use

Frontends should depend on `SDRPPControl` and `SDRTelemetryWorker`, not protocol clients directly. The RF radio UI may continue operating when telemetry is unavailable; telemetry is supplemental and must not make tuning fail.

FM RDS is intentionally enabled only for the FM radio profile. Other RF profiles leave RDS polling and presentation disabled.
