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

The scheduler is profile-aware. PERFORMANCE prioritizes RPM and MAP/boost,
ECU prioritizes engine-management telemetry, HOME keeps glance metrics fresh,
and BACKGROUND is Trip-biased so accumulated drive analytics remain useful
while another application screen is visible. Vehicle speed is owned by
navigation ground motion and is not requested from OBD.

These schedules are an OBD-link implementation detail rather than a universal
automotive contract. See
[Automotive Architecture](../../../docs/automotive_architecture.md).

Low-level serial and RFCOMM communication belongs in
`hardware_io.automotive.elm327`. CAN and OBD-II models belong in
`protocols.can` and `protocols.obd2` respectively.

Run the live component test from the project root:

```bash
python3 -m controllers.automotive.obd2.component_test.obd2_cli \
    --port /dev/rfcomm0
```
