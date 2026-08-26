# OpenRoadCode Navigation IMU State IDD

## Topic

`openroad.navigation.imu`

ZeroMQ transports the message as two frames: the UTF-8 topic followed by a JSON object.

## Version

Schema version: `1`

## Units and conventions

All quantities use SI units. Acceleration vectors use metres per second squared (m/s²). Angular velocity uses radians per second (rad/s). Vector components are expressed in the source sensor coordinate frame; coordinate-frame transformation belongs above the hardware transport layer.

Timestamp uses the common OpenRoadCode timestamp contract:

- `seconds`: uint64 whole seconds since 1970-01-01T00:00:00 UTC
- `nanoseconds`: uint32 fractional nanoseconds in the range 0..999,999,999

## Message envelope

```json
{
  "version": 1,
  "timestamp": {"seconds": 1787337000, "nanoseconds": 123456000},
  "source": "android",
  "data": {
    "acceleration_m_s2": {"x": -1.2, "y": 8.9, "z": -3.4},
    "linear_acceleration_m_s2": {"x": 0.1, "y": 0.2, "z": -0.1},
    "angular_velocity_rad_s": {"x": 0.01, "y": -0.03, "z": 0.005}
  }
}
```

## Data fields

| Field | JSON type | Unit | Meaning |
| --- | --- | --- | --- |
| `acceleration_m_s2` | vector object | m/s² | Accelerometer measurement including gravity when supplied by the source |
| `linear_acceleration_m_s2` | vector object | m/s² | Gravity-compensated acceleration |
| `angular_velocity_rad_s` | vector object | rad/s | Gyroscope angular velocity |

Each vector contains finite numeric `x`, `y`, and `z` fields.

## Producer requirements

Producers normalize hardware measurements to SI units before publication. `source` identifies the hardware/provider implementation without changing topic semantics. Producers must not silently substitute magnetic-field or position measurements into this contract.

## Consumer requirements

Consumers validate the schema before use and must not assume a particular physical mounting orientation from `source`. Sensor-frame alignment and fusion belong to navigation processing above this contract.

## Versioning

Version `1` is the initial public IMU contract. Breaking semantic or structural changes require a new schema version.
