# OpenRoadCode SDR++ Integration

OpenRoadCode uses SDR++ as its native RF engine and spectrum/waterfall presentation. ORC extends SDR++ with small purpose-built modules instead of forcing unrelated behavior through one protocol or duplicating SDR functionality in the frontend.

## User-interface path

The `orcUi` RADIO item opens `RadioEntryPanel`, which presents two sources:

- **RF RADIO** launches SDR++ and constructs the ORC RF controls.
- **STREAMING RADIO** currently opens a Coming Soon page while the streaming-radio provider/controller work remains under development.

For RF Radio, `SDRPPLauncher` starts SDR++ and `X11WindowEmbedder` discovers and reparents the SDR++ X11 client into the radio panel. The ORC controls remain outside the embedded SDR++ client and communicate through the controller/protocol layers below.

The current embedded implementation requires X11. It is exercised on native Debian/Linux and on Android through Termux:X11 with SDR++ running inside Debian proot.

## Ports

| Port | Service | Responsibility |
| --- | --- | --- |
| 4532 | SDR++ RigCTL Server | RF tuning, mode, bandwidth, receiver operations, and radio-specific data such as RDS when supported |
| 4533 | ORC `remote_control` module | SDR++ application/UI control such as waterfall, band plan, FFT hold, auto range, and theme |
| 4534 | ORC `telemetry` module | Read-only SDR++ runtime telemetry such as SNR, selected VFO, FFT-derived signal metrics, frequency/bandwidth, and display ranges |

Keeping these concerns separate lets radio-domain code remain independent from SDR++ UI control and telemetry. Telemetry is explicitly best-effort: failure of port 4534 must not prevent normal RF tuning or playback.

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

The C++ directories are built as SDR++ modules. The Python test servers implement the corresponding ORC wire protocols for protocol/controller development without requiring SDR++ to be running.

## Architecture boundary

- `development/sdrpp` owns the SDR++ C++ modules and developer test servers.
- `protocols/rigctl` owns RF/RigCTL communication on port 4532.
- `protocols/sdrpp_remote_control` owns the Python client for port 4533.
- `protocols/sdrpp_telemetry` owns the Python client for port 4534.
- `controllers/radio` owns radio-domain behavior such as profiles, tuning, presets, and RDS access.
- `controllers/sdr` exposes SDR++ application controls and best-effort telemetry to frontends.
- `apps/launchers/sdrpp_launcher.py` owns SDR++ process lifecycle and native-versus-Termux launch selection.
- `frontends/x11` owns foreign-window discovery, reparenting, and resize behavior.
- `apps/orcUi` owns Tk presentation and the RF/streaming source chooser.

This separation allows another frontend to reuse the same SDR++ integration without importing ORCui or Tkinter.

## RF profiles and metadata

The ORC radio layer supplies profiles for FM broadcast, NOAA weather, AM airband, HAM, and scanner-oriented use. Profile selection determines the appropriate tuning configuration and preset set while SDR++ remains the RF engine.

FM RDS is obtained through the radio/RigCTL path rather than the telemetry module. `SDRTelemetryMonitor` combines RDS with the latest telemetry snapshot for presentation, but only requests RDS for the FM profile.

## Installation

### Debian / Linux

From the OpenRoadCode repository root:

```bash
./development/debian/setup_sdrpp.sh
```

The script installs SDR++ build dependencies plus the X11 integration utilities used by ORC (`xdotool`, `xwininfo` via `x11-utils`, and `wmctrl`), builds SDR++, stages `remote_control.so` and `telemetry.so`, enables RigCTL, and installs `/usr/local/bin/sdrpp` as a wrapper around the matching ORC `root_dev` resource tree.

Run `orcUi` from an X11 session:

```bash
python3 -m apps.orcUi
```

### Termux

From a normal Termux shell:

```bash
./development/termux/setup_sdrpp.sh
```

The script creates/uses the Debian proot, builds SDR++ and all three integration pieces there, and prepares the `root_dev` resource tree. Start Termux:X11 and follow `development/termux/README.md` for the current application launch sequence.

## Runtime verification

With RF Radio running, the three local services can be checked on Linux with:

```bash
ss -ltn | grep -E '4532|4533|4534'
```

A complete integration normally shows listeners on `127.0.0.1:4532`, `127.0.0.1:4533`, and `127.0.0.1:4534`.
