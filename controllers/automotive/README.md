# Automotive Controllers

The automotive controller package exposes `VehicleStateSourceIf`, the data
source boundary used by vehicle telemetry screens. `Obd2Manager` implements
the contract with an ELM327 adapter, while `SimulatedVehicleStateSource`
generates changing, plausible telemetry without Bluetooth, serial, or vehicle
hardware.

Applications should accept `VehicleStateSourceIf` rather than depending on
either implementation directly. This lets the same screen run against live
vehicle data or the simulator.

Run the terminal frontend with both automotive and navigation simulation:

```bash
venv/bin/python -m apps.carTui.main --demo
```


## Architecture boundary

`VehicleStateSourceIf` is the source-neutral automotive boundary. A new
standardized OBD transport can normally implement `Obd2AdapterIf` and reuse
`Obd2Manager`; a richer non-OBD source can implement
`VehicleStateSourceIf` directly.

Do not make ELM327, PID identifiers, Bluetooth framing, or source-specific
polling mechanics part of the public vehicle domain model merely because the
reference vehicle currently uses them.

The complete layering, adaptive-profile behavior, ECU interpretation, Trip
analytics, and extension guidance are documented in
[Automotive Architecture](../../docs/automotive_architecture.md).
