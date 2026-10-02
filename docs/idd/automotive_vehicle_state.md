# OpenRoadCode IDD: Automotive Vehicle State

## Status

- Contract: `openroad.vehicle.state`
- Current version: `4`
- Initial transport: ZeroMQ PUB/SUB
- Payload encoding: JSON

This document defines the public OpenRoadCode vehicle-state dissemination contract. Producers may obtain the data from OBD-II, CAN, a simulator, a gateway, or another implementation. Consumers must not depend on the producer's hardware or acquisition mechanism.

## Message framing

The ZeroMQ representation uses two frames:

1. Topic frame: UTF-8 string `openroad.vehicle.state`
2. Payload frame: JSON object defined below

Subscribers may use the topic frame for ZeroMQ subscription filtering.

## Envelope

```json
{
  "version": 1,
  "timestamp": {
    "seconds": 1787333234,
    "nanoseconds": 123456000
  },
  "source": "obd2",
  "data": {
    "engine_speed_rad_s": 298.14,
    "vehicle_speed_m_s": 18.88,
    "throttle_position": 0.314,
    "accelerator_pedal_position": null,
    "engine_load": 0.467,
    "intake_manifold_pressure_pa": 126000,
    "barometric_pressure_pa": 99000,
    "boost_pressure_pa": 27026.0,
    "mass_air_flow_kg_s": 0.0187,
    "coolant_temperature_k": 363.15,
    "intake_air_temperature_k": 303.15,
    "fuel_level": 0.635,
    "control_voltage_v": 14.2
  }
}
```

### `version`

Unsigned contract version. Versions 1 through 4 are supported for decoding. Producers emit Version 4. A producer must emit the version corresponding to the payload schema it is publishing.

### `timestamp`

UTC Unix epoch time for the vehicle-state snapshot.

| Field | IDD type | Meaning |
| --- | --- | --- |
| `seconds` | `uint64` | Whole seconds since `1970-01-01T00:00:00 UTC` |
| `nanoseconds` | `uint32` | Fractional nanoseconds within the second, range `0..999,999,999` |

Negative epoch timestamps are invalid. The timestamp describes the snapshot time, not message-receipt time. This is a wall-clock timestamp and is not a monotonic clock value.

### `source`

UTF-8 string identifying the producer or acquisition source for diagnostics. Examples include `obd2`, `simulator`, `socketcan`, or an implementation-specific gateway name. Consumers must not use `source` to determine the semantic meaning of the vehicle data.

## SI unit policy

All physical quantities in OpenRoadCode public messaging contracts use SI units. Automotive conventions such as RPM, mph, psi, degrees Fahrenheit, and grams per second are converted at the contract boundary.

Dimensionless normalized quantities use the range `0.0..1.0` rather than percentages.

Unit-bearing field names include the unit suffix to keep captures and diagnostic output self-describing.

## Vehicle data fields

Every Version 4 field below must be present in `data`. If a nullable value is unsupported, unavailable, or stale beyond the producer's validity policy, its JSON value is `null`.

| Field | JSON type | SI unit / range | Nullable | Meaning |
| --- | --- | --- | --- | --- |
| `engine_speed_rad_s` | number | rad/s | yes | Engine angular velocity |
| `vehicle_speed_m_s` | number | m/s | yes | Vehicle road speed; the reference composition supplies navigation ground speed |
| `transmission_gear` | integer | `-1, 0, 1..6` | yes | Reverse, neutral, or estimated forward gear when known |
| `throttle_position` | number | `0.0..1.0` | yes | Measured throttle position |
| `commanded_throttle_position` | number | `0.0..1.0` | yes | ECU-commanded throttle position |
| `accelerator_pedal_position` | number | `0.0..1.0` | yes | Accelerator pedal position |
| `engine_load` | number | `0.0..1.0` | yes | Calculated engine load |
| `absolute_engine_load` | number | nonnegative ratio | yes | Absolute engine load reported by the ECU |
| `fuel_system_status_1` | integer | `0..255` | yes | SAE J1979 fuel-system status byte for system 1 |
| `fuel_system_status_2` | integer | `0..255` | yes | SAE J1979 fuel-system status byte for system 2 |
| `short_term_fuel_trim_bank1` | number | signed ratio | yes | Bank 1 short-term fuel correction |
| `long_term_fuel_trim_bank1` | number | signed ratio | yes | Bank 1 long-term fuel correction |
| `ignition_timing_advance_deg` | number | degrees | yes | Ignition advance relative to top dead center |
| `intake_manifold_pressure_pa` | number | Pa | yes | Absolute intake manifold pressure |
| `barometric_pressure_pa` | number | Pa | yes | Ambient/barometric pressure |
| `boost_pressure_pa` | number | Pa | yes | Gauge boost relative to barometric pressure; negative values may represent vacuum |
| `mass_air_flow_kg_s` | number | kg/s | yes | Mass air flow rate |
| `coolant_temperature_k` | number | K | yes | Engine coolant temperature |
| `intake_air_temperature_k` | number | K | yes | Intake air temperature |
| `fuel_level` | number | `0.0..1.0` | yes | Fuel tank level |
| `fuel_rail_pressure_pa` | number | Pa | yes | Fuel rail pressure |
| `commanded_equivalence_ratio` | number | `0.0..2.0` | yes | ECU-commanded equivalence ratio |
| `measured_equivalence_ratio` | number | `0.0..2.0` | yes | Measured equivalence ratio |
| `engine_fuel_rate_m3_s` | number | m³/s | yes | Engine fuel volume flow rate |
| `control_voltage_v` | number | V | yes | Vehicle/control-system electrical voltage |

### Version history

- **Version 1:** base vehicle state plus `transmission_gear`.
- **Version 2:** adds `engine_fuel_rate_m3_s`.
- **Version 3:** adds `commanded_equivalence_ratio`.
- **Version 4:** adds commanded throttle, absolute load, fuel-system status, fuel trims, ignition timing, fuel-rail pressure, and measured equivalence ratio.

## Nullability

Fields are not omitted when unavailable. Producers emit explicit JSON `null` values so the Version 4 object shape remains stable.

Example partial producer:

```json
{
  "engine_speed_rad_s": 298.14,
  "vehicle_speed_m_s": 18.88,
  "throttle_position": null,
  "accelerator_pedal_position": null,
  "engine_load": null,
  "intake_manifold_pressure_pa": null,
  "barometric_pressure_pa": null,
  "boost_pressure_pa": null,
  "mass_air_flow_kg_s": null,
  "coolant_temperature_k": 363.15,
  "intake_air_temperature_k": null,
  "fuel_level": null,
  "control_voltage_v": null
}
```

## Producer requirements

A Version 4 producer must:

- publish on `openroad.vehicle.state`;
- emit `version` equal to `4`;
- provide a valid Unix-epoch timestamp;
- use the SI units and dimensionless ranges defined above;
- include every Version 4 data field;
- use JSON `null` for unavailable values;
- avoid encoding hardware- or protocol-specific semantics into the public fields.

The producer controls its publication rate. Version 4 does not require a particular frequency.

## Consumer requirements

Consumers should treat each message as a complete vehicle-state snapshot. Consumers must tolerate `null` for every nullable data field and must not assume a particular producer type or publication frequency.

Consumers should reject or explicitly handle unsupported contract versions rather than silently interpreting them as a different version.

## Versioning

The `version` field versions the payload contract, not the ZeroMQ transport.

Changes that alter the meaning, unit, type, required presence, or interpretation of an existing field require a new contract version. Version 4 field semantics must not be silently changed after publication.

Transport implementations are intentionally separate from this IDD. A future transport may carry the same contract without changing the automotive data semantics.
