# OpenRoadCode Navigation Position State IDD

## Topic

`openroad.navigation.position`

ZeroMQ transports the message as two frames: the UTF-8 topic followed by a JSON object.

## Version

Schema version: `1`

## Units and conventions

All physical quantities use SI units. Geographic and angular quantities are expressed in radians rather than degrees. All defined fields are always present; unavailable values are JSON `null`.

Timestamp uses the common OpenRoadCode timestamp contract:

- `seconds`: uint64 whole seconds since 1970-01-01T00:00:00 UTC
- `nanoseconds`: uint32 fractional nanoseconds in the range 0..999,999,999

## Message envelope

```json
{
  "version": 1,
  "timestamp": {"seconds": 1787337000, "nanoseconds": 123456000},
  "source": "simulator",
  "data": {
    "latitude_rad": 0.74705,
    "longitude_rad": -1.44885,
    "altitude_m": 250.5,
    "fix_mode": 3,
    "satellites_visible": 14,
    "satellites_used": 10,
    "accuracy_m": 2.5,
    "is_cached": false
  }
}
```

## Data fields

| Field | JSON type | Unit / range | Nullable | Meaning |
| --- | --- | --- | --- | --- |
| `latitude_rad` | number | rad, -pi/2..pi/2 | yes | Geodetic latitude |
| `longitude_rad` | number | rad, -pi..pi | yes | Geodetic longitude |
| `altitude_m` | number | m | yes | Altitude reported by the source; signed values are allowed |
| `fix_mode` | integer | 1, 2, or 3 | yes | Source fix mode: no fix, 2D, or 3D |
| `satellites_visible` | integer | >= 0 | yes | Satellites visible to the source |
| `satellites_used` | integer | >= 0 | yes | Satellites used in the solution |
| `accuracy_m` | number | m, >= 0 | yes | Position accuracy estimate supplied by the source |
| `is_cached` | boolean | true/false | no | True when the position is a retained/cached sample rather than a fresh observation |

When both satellite counts are available, `satellites_used` must not exceed `satellites_visible`.

Position messages do not include speed or course. Those values belong to
`openroad.navigation.motion`, documented in the
[Message Bus IDD](../messaging/message_bus_idd.md#openroadnavigationmotion).
Older position examples containing `speed_m_s` or `course_rad` do not match the
current encoder/validator; unknown data fields are rejected.

Service-local route playback uses `source = "route-simulation"` without changing
the schema. Synthetic fix/accuracy/satellite values are development data, not
evidence of an actual GNSS fix. The bridge continues producing real GPS while
ORC temporarily publishes the route-generated position.

## Producer requirements

Producers must publish every defined field, using `null` when a value is unavailable. Values must be finite JSON numbers and conform to the units and ranges above. Producers may originate from gpsd, browser geolocation, simulation, CAN/GNSS gateways, or other implementations; `source` identifies the producer without changing the topic semantics.

## Consumer requirements

Consumers must validate the envelope and data contract before using a message. Consumers must tolerate `null` for every nullable field and must not infer a usable position solely from field presence. `fix_mode >= 2` indicates a usable 2D or 3D fix when fix mode is supplied.

## Versioning

Version `1` is the initial public position contract. Breaking semantic or structural changes require a new schema version. The topic remains the semantic identity of normalized geographic position state.
