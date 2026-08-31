# Automotive Service

The automotive service owns a `VehicleStateSourceIf` and publishes complete SI-normalized `VehicleState` snapshots onto the OpenRoadCode ZeroMQ telemetry bus.

Applications such as Car TUI consume the public vehicle-state topic. They do not own the OBD-II adapter or simulation source.

## Data flow

```text
simulation ------------------------------\
                                         > VehicleStateSourceIf
ELM327 -> Elm327ObdAdapter -> Obd2Manager /
                    |
                    v
             AutomotiveRuntime
                    |
           VehicleStatePublisher
                    |
              ZeroMqPublisher
                    |
               ZeroMQ broker
                    |
            MessageDispatcher
                    |
             VehicleBusState
                    |
          Car TUI / other apps
```

The telemetry contract remains SI regardless of how a UI displays values. Metric/imperial conversion belongs at the presentation layer and uses `common.units`.

## Runtime configuration

The automotive service is configured through the same runtime TOML used by the other producer services.

Simulation example:

```toml
[services.automotive]
enabled = true
rate_hz = 10.0

[services.automotive.input]
source = "simulation"

[services.automotive.publish]
enabled = true
source = "simulated-vehicle"
```

Physical ELM327 example:

```toml
[services.automotive]
enabled = true
rate_hz = 10.0

[services.automotive.input]
source = "device"
device = "elm327"
port = "/dev/rfcomm0"
baud = 38400
timeout_s = 1.0
slow_poll_interval_s = 5.0

[services.automotive.publish]
enabled = true
source = "obd2"
```

`Elm327Device` owns the serial connection, `Elm327ObdAdapter` translates between ELM327 responses and OBD-II models, and `Obd2Manager` polls supported PIDs and assembles the SI-normalized `VehicleState`.

The manager polls RPM, vehicle speed, throttle, accelerator position, engine load, and manifold pressure on each snapshot. Slower-changing values such as barometric pressure, airflow, coolant/intake temperature, fuel level, and module voltage use `slow_poll_interval_s`.

## Start locally

Start the ZeroMQ broker first:

```bash
python3 -m messaging.zeromq.broker_cli
```

Simulation:

```bash
python3 -m services.automotive.automotive_service_cli \
  --config config/runtime.simulated.toml
```

Physical vehicle:

```bash
python3 -m services.automotive.automotive_service_cli \
  --config config/runtime.toml
```

For Bluetooth serial ELM327 adapters, `/dev/rfcomm0` must already exist and be connected before starting the service. Change `port` in the runtime TOML when using another serial device.

The service publishes to `[messaging].publisher_endpoint` at the configured `rate_hz`.

## Consumer example

Car TUI already subscribes to vehicle telemetry through its shared `VehicleBusState`. With the broker and automotive service running, start it normally:

```bash
python3 -m apps.carTui.main
```

The Vehicle screen updates as new `VehicleState` messages arrive. No automotive simulation or OBD-II object is constructed inside Car TUI.

## Design rule

Producer services own hardware and simulation sources. Applications consume messaging contracts. This keeps the consumer path identical between bench simulation and the vehicle:

```text
simulation source --\
                    > AutomotiveRuntime -> ZeroMQ -> application
physical source ---/
```

Switching between simulation and physical hardware therefore changes service composition, not application code or the wire contract.
