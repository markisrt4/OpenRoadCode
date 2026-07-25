# Automotive OBD-II Controllers

This package connects automotive hardware to the transport-independent models
in `protocols.obd2`.

- `Elm327ObdAdapter` formats OBD-II requests for an `Elm327Device`, filters
  ELM327 status lines, parses CAN frames through `protocols.can`, and returns
  normalized `Obd2Response` objects.
- `Obd2Manager` polls supported vehicle values and produces `VehicleState` for
  applications.

On connection, `Obd2Manager` reads the Mode 01 supported-PID bitmaps. It polls
fast-changing values on every `read_state()` call and caches slow-changing
values for five seconds by default. The slow interval is configurable through
`slow_poll_interval_seconds`.

Low-level serial and RFCOMM communication belongs in
`hardware_io.automotive.elm327`. CAN and OBD-II models belong in
`protocols.can` and `protocols.obd2` respectively.

Run the live component test from the project root:

```bash
python3 -m controllers.automotive.obd2.component_test.obd2_cli \
    --port /dev/rfcomm0
```
