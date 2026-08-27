# OpenRoadCode Navigation Magnetic Field State IDD

## Topic

`openroad.navigation.magnetic_field`

ZeroMQ transports the message as two frames: the UTF-8 topic followed by a JSON object.

## Version

Schema version: `1`

## Units and conventions

Magnetic field strength is expressed in microteslas (µT). Vector components are expressed in the source sensor coordinate frame. Heading, declination correction, mounting alignment, and sensor fusion are intentionally outside this raw-measurement contract.

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
    "magnetic_field_ut": {"x": 18.4, "y": -37.9, "z": 26.1}
  }
}
```

## Data fields

| Field | JSON type | Unit | Meaning |
| --- | --- | --- | --- |
| `magnetic_field_ut` | vector object | µT | Raw three-axis magnetic-field measurement |

The vector contains finite numeric `x`, `y`, and `z` fields.

## Producer requirements

Producers normalize measurements to microteslas before publication. `source` identifies the hardware/provider implementation. Producers publish measurements, not derived compass headings.

## Consumer requirements

Consumers validate the schema before use. Consumers requiring heading or attitude must combine this measurement with appropriate calibration, frame alignment, magnetic declination, and other navigation sensors as required.

## Versioning

Version `1` is the initial public magnetic-field contract. Breaking semantic or structural changes require a new schema version.
