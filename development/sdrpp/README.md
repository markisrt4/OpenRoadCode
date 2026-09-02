# OpenRoadCode SDR++ Integration

OpenRoadCode extends SDR++ with small purpose-built modules instead of forcing unrelated behavior through one protocol.

## Ports

| Port | Service | Responsibility |
| --- | --- | --- |
| 4532 | SDR++ Rigctl Server | RF tuning, mode, bandwidth, receiver operations, and radio-specific data such as RDS when supported |
| 4533 | ORC `remote_control` module | SDR++ application/UI control such as waterfall, band plan, FFT hold, auto range, and theme |
| 4534 | ORC `telemetry` module | Read-only SDR++ runtime telemetry such as SNR, selected VFO, FFT-derived signal metrics, and display ranges |

Keeping these concerns separate lets radio-domain code remain independent from SDR++ UI control and telemetry.

## Layout

```text
development/sdrpp/
├── README.md
├── remote_control/
│   ├── README.md
│   ├── CMakeLists.txt
│   ├── src/main.cpp
│   └── test_server.py
└── telemetry/
    ├── README.md
    ├── CMakeLists.txt
    ├── src/main.cpp
    └── test_server.py
```

The C++ directories are intended to be built as SDR++ modules. The Python test servers implement the same ORC wire protocols for frontend/controller development without requiring SDR++ to be running.

## Architecture Boundary

- `development/sdrpp` owns the SDR++ C++ modules and developer test servers.
- `protocols/sdrpp_remote_control` owns the Python client for port 4533.
- `protocols/sdrpp_telemetry` owns the Python client for port 4534.
- `controllers/sdr` exposes application-facing SDR behavior to frontends.
- `controllers/radio` owns radio-domain behavior such as profiles, tuning, presets, and RDS access.
- `apps/orcUi` should primarily contain Tk presentation and ORCui-specific presenters/composition.

This separation allows another frontend to reuse the same SDR++ integration without importing ORCui or Tkinter.
