# OpenRoadCode Route Guidance State IDD

## Topic

`route_guidance.state`

ZeroMQ transports the message as two frames: the UTF-8 topic followed by a JSON object.

## Version

Schema version: `1`

## Units and conventions

All distances on the public messaging interface use SI units (meters). Route-planning controllers may use other explicitly named units internally, but producers must convert them before publishing this contract.

Nullable fields use JSON `null`. The message represents derived guidance state for the currently active route; it is not a raw navigation sensor message.

## Message envelope

```json
{
  "version": 1,
  "source": "route_guidance",
  "data": {
    "distance_along_route_m": 420.0,
    "distance_remaining_m": 1580.0,
    "distance_from_route_m": 3.2,
    "current_maneuver_index": 1,
    "instruction": "Turn left",
    "verbal_instruction": "Turn left onto Main Street",
    "distance_to_maneuver_m": 185.0,
    "off_route": false,
    "route_complete": false
  }
}
```

## Data fields

| Field | JSON type | Unit / range | Nullable | Meaning |
| --- | --- | --- | --- | --- |
| `distance_along_route_m` | number | m, >= 0 | no | Furthest accepted progress along the active route shape |
| `distance_remaining_m` | number | m, >= 0 | no | Remaining distance along the active route shape |
| `distance_from_route_m` | number | m, >= 0 | no | Distance from the current position to the nearest projected point on the route |
| `current_maneuver_index` | integer | >= 0 | yes | Zero-based active maneuver index |
| `instruction` | string | text | yes | Human-readable maneuver instruction |
| `verbal_instruction` | string | text | yes | Instruction intended for speech presentation when supplied by the route planner |
| `distance_to_maneuver_m` | number | m, >= 0 | yes | Distance remaining to the end of the active maneuver |
| `off_route` | boolean | true/false | no | True when route-deviation policy currently considers the vehicle off route |
| `route_complete` | boolean | true/false | no | True when the current position is within the configured arrival threshold |

## Producer requirements

The producer must derive this state from a valid active route and geographic position. Distance values must be finite and non-negative. `current_maneuver_index`, when present, must identify a maneuver in the active route. Producers should apply route-deviation hysteresis so ordinary position noise does not cause rapid `off_route` state flapping.

A route replacement or reroute resets route-relative progress before subsequent guidance state is published.

## Consumer requirements

Consumers must treat this message as presentation-neutral state. UI, speech, logging, and other consumers may independently subscribe without owning route geometry or route-planning policy.

Consumers must tolerate nullable maneuver fields. `off_route` is an observed guidance condition, not by itself a command to calculate a new route. Rerouting policy belongs to navigation-session orchestration.

## Versioning

Version `1` is the initial public route-guidance state contract. Breaking semantic or structural changes require a new schema version.
