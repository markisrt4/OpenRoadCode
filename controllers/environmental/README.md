# Barometric Controller

The barometric controller converts normalized pressure and temperature
samples into absolute altitude, relative altitude, and filtered vertical
speed.

## Architecture

- `BarometricControllerIf` is the application-facing controller contract.
- `BarometricSourceIf` is the controller-facing sensor contract.
- `Bmp3xxBarometricAdapter` adapts either a BMP388 or BMP390 hardware device
  to normalized `BarometricSample` values.
- `BarometricController` processes those samples into `BarometricState`.
- `BarometricControllerStub` supplies deterministic state for demos.
- `UnconfiguredBarometricController` explicitly reports unavailable support.

## Component Test

Run the complete BMP3XX adapter and controller path:

```bash
python3 -m controllers.environmental.component_test.barometric_cli
```

Read one sample, select address `0x76`, or use imperial display units:

```bash
python3 -m controllers.environmental.component_test.barometric_cli \
    --address 0x76 \
    --once \
    --imperial
```

Altitude defaults to the standard sea-level reference pressure of 101325 Pa.
Use a local reference for better altitude accuracy:

```bash
python3 -m controllers.environmental.component_test.barometric_cli \
    --sea-level-pressure 100800
```
