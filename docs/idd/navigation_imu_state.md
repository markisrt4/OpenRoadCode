# OpenRoadCode Navigation IMU State IDD

## Topic

`openroad.navigation.imu`

ZeroMQ transports the message as two frames: the UTF-8 topic followed by a JSON object.

## Version

Schema version: `1`

## Coordinate-frame contract

Every IMU message explicitly identifies the coordinate frame of all vectors with `frame_id`. A consumer must never infer axis meaning from `source`.

OpenRoadCode defines these frame identifiers:

| `frame_id` | Axes | Intended use |
| --- | --- | --- |
| `vehicle` | +X forward, +Y left, +Z up | Canonical ORC vehicle/navigation frame |
| `android_device` | +X toward screen right, +Y toward screen top, +Z out of screen | Raw Android device sensors |
| `world_enu` | +X east, +Y north, +Z up | Earth-fixed local ENU data |
| `world_ned` | +X north, +Y east, +Z down | Earth-fixed local NED data |

The ORC vehicle frame is right-handed and is the required frame for normalized navigation outputs. Hardware-facing/raw producers may publish a hardware/device frame, but the adapter or navigation processing layer must transform it before producing vehicle attitude or motion.

For the default Termux phone mounting convention, the phone lies screen-up in portrait orientation with the top of the phone pointing toward vehicle-forward. The Android-to-vehicle transform is:

```text
vehicle.x =  android.y
vehicle.y = -android.x
vehicle.z =  android.z
```

The same rotation must be applied to acceleration, linear acceleration, angular velocity, and magnetic-field vectors when those measurements are transformed between these frames.

## Units and conventions

All quantities use SI units. Acceleration vectors use metres per second squared (m/s²). Angular velocity uses radians per second (rad/s).

Timestamp uses the common OpenRoadCode timestamp contract:

- `seconds`: uint64 whole seconds since 1970-01-01T00:00:00 UTC
- `nanoseconds`: uint32 fractional nanoseconds in the range 0..999,999,999

## Message envelope

```json
{
  "version": 1,
  "timestamp": {"seconds": 1787337000, "nanoseconds": 123456000},
  "source": "android",
  "frame_id": "android_device",
  "data": {
    "acceleration_m_s2": {"x": -1.2, "y": 8.9, "z": -3.4},
    "linear_acceleration_m_s2": {"x": 0.1, "y": 0.2, "z": -0.1},
    "angular_velocity_rad_s": {"x": 0.01, "y": -0.03, "z": 0.005}
  }
}
```

## Envelope fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `version` | integer | Contract schema version |
| `timestamp` | object | Common ORC timestamp |
| `source` | string | Producer/hardware/provider identity |
| `frame_id` | string | Coordinate frame shared by every vector in this message |
| `data` | object | IMU measurements |

## Data fields

| Field | JSON type | Unit | Meaning |
| --- | --- | --- | --- |
| `acceleration_m_s2` | vector object | m/s² | Accelerometer measurement including gravity when supplied by the source |
| `linear_acceleration_m_s2` | vector object | m/s² | Gravity-compensated acceleration |
| `angular_velocity_rad_s` | vector object | rad/s | Gyroscope angular velocity |

Each vector contains finite numeric `x`, `y`, and `z` fields.

## Producer requirements

Producers normalize hardware measurements to SI units before publication and must explicitly label the coordinate frame. `source` identifies the implementation; `frame_id` defines vector semantics. A producer must never relabel a vector without actually performing the corresponding coordinate transformation.

The normalized `NavigationStatePublisher` publishes IMU vectors in `vehicle`. The raw Android sensor service publishes them in `android_device`.

## Consumer requirements

Consumers validate both schema and `frame_id` before use. A consumer requiring vehicle-frame data must reject or explicitly transform other frames. Consumers must not assume mounting orientation from `source`.

## Heading reference versus coordinate frame

Coordinate frame and heading reference are different concepts. `frame_id` describes vector axes. Heading reference describes what zero heading means, such as relative, magnetic north, or true north. Attitude contracts document heading reference independently rather than overloading `frame_id`.

## Versioning

`frame_id` was added while schema version 1 remained under active development on the Termux target branch. Once the public contract is released, removing a frame field, changing axis semantics, or changing the canonical vehicle frame is a breaking change requiring a new schema version.
