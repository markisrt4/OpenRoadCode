# Automotive OBD-II Controllers

This package connects automotive hardware to the transport-independent models
in `protocols.obd2`.

- `Elm327ObdAdapter` formats OBD-II requests for an `Elm327Device`, filters
  ELM327 status lines, parses CAN frames through `protocols.can`, and returns
  normalized `Obd2Response` objects.
- `Obd2Manager` polls supported vehicle values and produces `VehicleState` for
  applications.

On connection, `Obd2Manager` reads the Mode 01 supported-PID bitmaps and
builds a weighted scheduler containing only supported PIDs. Each
`read_state()` performs at most one physical OBD request and returns a complete
snapshot assembled from cached values.

The default 12-slot request schedule prioritizes RPM and MAP while rotating
standard and slow telemetry so fuel, ECU, temperature, pressure, and voltage
data continue to refresh without blocking the hot gauges. Vehicle speed is
owned by navigation ground motion and is not requested from OBD.

Low-level serial and RFCOMM communication belongs in
`hardware_io.automotive.elm327`. CAN and OBD-II models belong in
`protocols.can` and `protocols.obd2` respectively.

Run the live component test from the project root:

```bash
python3 -m controllers.automotive.obd2.component_test.obd2_cli \
    --port /dev/rfcomm0
```
