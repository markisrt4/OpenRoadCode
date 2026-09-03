# SDR++ Telemetry Module

`telemetry` is a read-only OpenRoadCode SDR++ module that exposes runtime receiver/display measurements over a small localhost TCP protocol.

It intentionally does **not** tune the radio or control the SDR++ UI. Those responsibilities belong to Rigctl (`4532`) and the remote-control module (`4533`).

## Endpoint

```text
127.0.0.1:4534
```

## Commands

```text
PING
GET snr
GET signal_peak
GET fft_average
GET selected_vfo
GET center_frequency
GET bandwidth
GET view_bandwidth
GET telemetry
```

`GET telemetry` returns a compact snapshot containing the available metrics in one response.

`fft_average` is the arithmetic average of the finite FFT bins within the selected VFO. It is a relative display measurement, not a calibrated RF noise-floor measurement.

## Testing the Live Module

Prefer the ORC Python client or a small Python socket probe when testing the live module. Different `nc` implementations have different connection-close behavior and are not the canonical telemetry test path.

A dependency-free socket probe is:

```bash
python3 - <<'PY'
import socket

for command in ("PING\n", "GET telemetry\n"):
    print(f">>> {command.strip()}")
    with socket.create_connection(("127.0.0.1", 4534), timeout=2) as sock:
        sock.sendall(command.encode())
        sock.shutdown(socket.SHUT_WR)
        print(sock.recv(4096).decode().rstrip())
PY
```

The application-facing client lives in `protocols/sdrpp_telemetry`.

## Development Test Server

The Python server allows ORC protocol/controller/UI work without rebuilding or running SDR++:

```bash
python development/sdrpp/telemetry/test_server.py
```

It implements the same one-command request/response model and metric names as the production module. Fake signal values vary slowly so refresh behavior is visible during UI testing.

## Intended ORC Data Path

```text
SDR++ telemetry module :4534
        ↓
protocols/sdrpp_telemetry
        ↓
controllers/sdr/sdr_telemetry_monitor.py
        ↓
frontend presentation
```

The frontend must not perform blocking telemetry socket I/O on its UI thread.

## Signal Semantics

SNR is sourced from SDR++'s selected-VFO measurement. FFT-derived peak/average measurements are useful relative indicators but should not be presented as calibrated RF power unless calibration is explicitly implemented and validated.
