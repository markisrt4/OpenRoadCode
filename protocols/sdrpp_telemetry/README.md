# SDR++ Telemetry Protocol

`protocols.sdrpp_telemetry` is the Python client for the OpenRoadCode read-only SDR++ telemetry module.

The module normally listens on `127.0.0.1:4534`.

## Responsibilities

This protocol reports SDR/display runtime measurements. It does not tune the receiver and does not control SDR++ UI state.

Current snapshot fields include:

- selected VFO
- selected-VFO SNR
- FFT peak over the selected VFO
- FFT average over the selected VFO
- center frequency
- receiver bandwidth
- view bandwidth
- FFT display range
- waterfall display range

`fft_average` is deliberately named as an FFT average rather than a calibrated noise floor. The value is derived from SDR++ FFT bins and should not be presented as calibrated RF power without additional calibration.

## Example

```python
from protocols.sdrpp_telemetry import SDRPPTelemetryClient

client = SDRPPTelemetryClient()
if client.ping():
    telemetry = client.read()
    print(telemetry.snr_db)
    print(telemetry.signal_peak_db)
```

## Protocol Separation

- `4532`: SDR++ Rigctl Server for radio/RF behavior and RDS when available
- `4533`: ORC SDR++ remote control for application/UI control
- `4534`: ORC SDR++ telemetry for read-only runtime measurements

The matching development server and SDR++ module live under `development/sdrpp/telemetry`.
