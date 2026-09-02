# SDR++ Telemetry Module

`telemetry` is a read-only OpenRoadCode SDR++ module that exposes runtime receiver/display measurements over a small localhost TCP protocol.

It intentionally does **not** tune the radio or control the SDR++ UI. Those responsibilities belong to Rigctl (`4532`) and the ORC remote-control module (`4533`).

## Endpoint

```text
127.0.0.1:4534
```

## Commands

```text
PING
GET snr
GET signal_peak
GET noise_floor
GET selected_vfo
GET center_frequency
GET bandwidth
GET view_bandwidth
GET telemetry
```

`GET telemetry` returns a compact snapshot containing the available metrics in one response. The exact metric set may evolve while the module is validated against SDR++ upstream APIs.

## Development Test Server

The Python server allows ORC protocol/controller/UI work without rebuilding or running SDR++:

```bash
python development/sdrpp/telemetry/test_server.py
```

Then query it from another shell:

```bash
printf 'PING\nGET snr\nGET signal_peak\nGET noise_floor\nGET telemetry\n' | nc 127.0.0.1 4534
```

The fake signal values vary slowly so refresh behavior is visible during UI testing.

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
