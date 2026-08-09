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
