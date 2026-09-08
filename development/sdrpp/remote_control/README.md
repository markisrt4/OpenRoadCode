# SDR++ Remote Control Module

`remote_control` is an OpenRoadCode SDR++ module for application/UI-level control that is not part of radio tuning itself.

## Endpoint

```text
127.0.0.1:4533
```

## Responsibilities

The module controls SDR++ presentation/runtime features including:

- Waterfall visibility
- Band plan visibility
- FFT peak hold
- FFT/waterfall auto range
- SDR++ theme selection

It deliberately does not own RF tuning, modes, bandwidth, RDS, or telemetry measurements.

## ORC Service Split

```text
:4532  Rigctl          radio/RF control and radio-specific data
:4533  remote_control SDR++ application/UI control
:4534  telemetry      read-only runtime measurements
```

## Python Client

ORC accesses this protocol through:

```text
protocols/sdrpp_remote_control/
```

Application-facing behavior lives under `controllers/sdr`, keeping socket/protocol details out of frontends.

## Development Test Server

A Python test server is included for developing ORC without a live SDR++ module:

```bash
python development/sdrpp/remote_control/test_server.py
```

The test server should mirror only the `:4533` control protocol. Telemetry commands belong exclusively to the telemetry service on `:4534`.
