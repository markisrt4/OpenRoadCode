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

## Bluetooth OBD-II component test

The end-to-end smoke test verifies the Bluetooth RFCOMM serial device, ELM327
initialization, the selected vehicle protocol, and decoded read-only Mode 01
telemetry:

```bash
python3 -m controllers.automotive.component_test.obd2_bluetooth_smoke_cli \
    --port /dev/rfcomm0
```

It reads three samples and exits with a nonzero status identifying the failed
layer. It does not clear diagnostic codes or send vehicle-control commands.
The ignition normally needs to be on for the vehicle ECUs to answer PID
requests.

For lower-level diagnosis, use the interactive raw ELM327 test:

```bash
python3 -m hardware_io.automotive.elm327.component_test.elm327_cli \
    --port /dev/rfcomm0 \
    --command ATI
```
