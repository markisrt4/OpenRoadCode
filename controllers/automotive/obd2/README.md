# Automotive OBD-II Controllers

This package connects automotive hardware to the transport-independent models
in `protocols.obd2`.

- `Elm327ObdAdapter` formats OBD-II requests for an `Elm327Device`, filters
  ELM327 status lines, parses CAN frames through `protocols.can`, and returns
  normalized `Obd2Response` objects.
- `Obd2Manager` polls supported vehicle values and produces `VehicleState` for
  applications.

On connection, `Obd2Manager` reads the Mode 01 supported-PID bitmaps and then
uses priority polling with cached state:

- hot: RPM and MAP on every `read_state()`;
- standard: speed, throttle, pedal, load, equivalence ratio, and fuel rate at
  `standard_poll_hz`;
- slow: barometric pressure, MAF, coolant/intake temperature, fuel level, and
  voltage at `slow_poll_interval_seconds`.

The automotive service calls `read_state()` at `hot_poll_hz`, so RPM and
boost can update substantially faster than the rest of the dashboard while
every published `VehicleState` remains complete. The ELM327 request stream is
kept strictly serial rather than polling lanes concurrently.

Low-level serial and RFCOMM communication belongs in
`hardware_io.automotive.elm327`. CAN and OBD-II models belong in
`protocols.can` and `protocols.obd2` respectively.

Run the live component test from the project root:

```bash
python3 -m controllers.automotive.obd2.component_test.obd2_cli \
    --port /dev/rfcomm0
```
