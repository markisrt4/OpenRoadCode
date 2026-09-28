# OpenRoadCode IDD: Automotive Trip State

## Status

- Contract: `openroad.vehicle.trip.state`
- Current version: `3`
- Initial transport: ZeroMQ PUB/SUB
- Payload encoding: JSON

This document defines the public accumulated Trip telemetry contract. The Trip service derives this state from vehicle and navigation observations and publishes SI-normalized snapshots independently of whether the Trip screen is visible.

## Envelope and framing

ZeroMQ uses a UTF-8 topic frame followed by a JSON payload containing `version`, `timestamp`, `source`, and `data`. The timestamp is UTC Unix epoch time using the shared `seconds` and `nanoseconds` timestamp object.

## Version 3 data fields

| Field | Unit / type | Nullable | Meaning |
| --- | --- | --- | --- |
| `status` | `idle|active|paused|complete` | no | Trip lifecycle |
| `started_at`, `ended_at` | timestamp | yes | Trip boundaries |
| `elapsed_s`, `moving_s`, `stopped_s` | s | no | Accumulated durations |
| `distance_m` | m | no | Accumulated distance |
| `average_speed_m_s`, `maximum_speed_m_s` | m/s | yes | Trip speed statistics |
| `fuel_used_m3` | m³ | yes | Total measured/estimated fuel volume |
| `instantaneous_fuel_consumption_m3_per_m` | m³/m | yes | Current distance-normalized fuel consumption |
| `average_fuel_consumption_m3_per_m` | m³/m | yes | Trip-average distance-normalized fuel consumption |
| `estimated_range_m` | m | yes | Estimated remaining range |
| `boost_time_s` | s | no | Time observed above the configured boost threshold |
| `boost_distance_m` | m | no | Distance accumulated while boosted |
| `boost_fuel_used_m3` | m³ | no | Fuel consumed while boosted |
| `peak_boost_pa` | Pa | yes | Maximum observed positive boost |
| `high_load_fuel_used_m3` | m³ | no | Fuel consumed while engine load met the configured high-load threshold |
| `start_latitude_deg`, `start_longitude_deg` | degrees | yes | First usable trip position |
| `current_latitude_deg`, `current_longitude_deg` | degrees | yes | Latest usable trip position |
| `end_latitude_deg`, `end_longitude_deg` | degrees | yes | Final usable trip position |

All numeric values must be finite. Durations, distances, fuel quantities, speeds, range, and positive boost metrics are nonnegative. Latitude is constrained to -90..90 degrees and longitude to -180..180 degrees.

## Version history and compatibility

- **Version 1:** base trip timing, distance, speed, fuel, range, and position state.
- **Version 2:** adds boost time, boost distance, fuel consumed while boosted, and peak boost.
- **Version 3:** adds fuel consumed while under high engine load.

The decoder accepts Versions 1 through 3 and supplies neutral defaults for metrics introduced after the received version. Producers emit Version 3.

## Semantics

Boost and high-load fuel values are observational associations. They describe fuel consumed while those conditions were present; they do not claim that boost or load caused a specific incremental amount of fuel consumption.

Trip accumulation is independent of presentation. Hiding the Trip screen does not reset or pause the tracker. The automotive BACKGROUND telemetry profile remains Trip-biased so request-limited OBD sources continue supplying useful Trip inputs.

## Producer and consumer requirements

Producers must publish complete objects for their declared schema version, use SI units, preserve nullability, and identify the source with a non-empty string. Consumers must tolerate nullable measurements and explicitly handle unsupported future versions.

Presentation layers may derive driver-facing values such as miles, gallons, MPG, PSI, boost-fuel share, and high-load-fuel share from the SI contract. Those presentation-derived percentages are not additional wire fields.

## Related documentation

- [Automotive architecture](../automotive_architecture.md)
- [Automotive service](../../services/automotive/README.md)
- [Messaging overview](../../messaging/README.md)
- [Automotive vehicle-state IDD](automotive_vehicle_state.md)
