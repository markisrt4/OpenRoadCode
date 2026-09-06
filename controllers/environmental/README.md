# Environmental Controllers

Environmental controllers normalize physical sensor data into application-facing state without tying applications to a particular hardware source.

## Ambient Light

`AmbientLightController` reports ambient illuminance in lux through the hardware-independent `AmbientLightSensorIf` contract.

The Android path supports both direct component testing and the streamed sensor service:

```text
Android TYPE_LIGHT
    -> Android sensor bridge
    -> AndroidSensorBridgeClient
    -> BufferedAmbientLightSensor
    -> AmbientLightController
    -> openroad.environmental.ambient_light
```

The buffered sensor lets `AndroidSensorService` feed values already received on `/stream/imu` through the controller without making a second HTTP request for every light sample.

Run the direct Android adapter/controller component test from this branch:

```bash
cd ~/src/OpenRoadCode
git switch android-ambient-light
git pull
python -m controllers.environmental.component_test.ambient_light_cli
```

To read a phone bridge from another ORC machine, enable Remote Sensor Access in the Android bridge app and provide its address:

```bash
cd ~/src/OpenRoadCode
git switch android-ambient-light
git pull
python -m controllers.environmental.component_test.ambient_light_cli \
    --url http://PHONE_IP:8766
```

Use `--once` to read a single sample. Zero lux is a valid reading; negative and non-finite values are rejected.

## Barometric Controller

The barometric controller converts normalized pressure and temperature samples into absolute altitude, relative altitude, and filtered vertical speed.

### Architecture

- `BarometricControllerIf` is the application-facing controller contract.
- `BarometricSourceIf` is the controller-facing sensor contract.
- `Bmp3xxBarometricAdapter` adapts either a BMP388 or BMP390 hardware device to normalized `BarometricSample` values.
- `BarometricController` processes those samples into `BarometricState`.
- `BarometricControllerStub` supplies deterministic state for demos.
- `UnconfiguredBarometricController` explicitly reports unavailable support.

### Component Test

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

Altitude defaults to the standard sea-level reference pressure of 101325 Pa. Use a local reference for better altitude accuracy:

```bash
python3 -m controllers.environmental.component_test.barometric_cli \
    --sea-level-pressure 100800
```
