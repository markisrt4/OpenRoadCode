# Automotive Service

The automotive service owns a `VehicleStateSourceIf` and publishes complete SI-normalized `VehicleState` snapshots onto the OpenRoadCode ZeroMQ telemetry bus.

Applications such as Car TUI consume the public vehicle-state topic. They do not own the OBD-II adapter or simulation source.

## Data flow

```text
VehicleStateSourceIf
        |
        | read_state()
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
Car TUI / other applications
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

The simulation source produces changing RPM, speed, throttle, accelerator position, engine load, manifold pressure, boost, airflow, coolant and intake temperatures, fuel level, and control-module voltage.

`source = "device"` is reserved for the physical automotive source. The service currently rejects it explicitly until the existing ELM327/OBD-II stack is composed into the producer service.

## Start locally

Start the ZeroMQ broker first:

```bash
python3 -m messaging.zeromq.broker_cli
```

Then start the automotive service:

```bash
python3 -m services.automotive.automotive_service_cli \
  --config config/runtime_simulation.toml
```

The service publishes to `[messaging].publisher_endpoint` at the configured `rate_hz`.

## Consumer example

Car TUI already subscribes to vehicle telemetry through its shared `VehicleBusState`. With the broker and automotive service running, start it normally:

```bash
python3 -m apps.carTui.main
```

The Vehicle screen should update as new `VehicleState` messages arrive. No automotive simulation or OBD-II object is constructed inside Car TUI.

## Design rule

Producer services own hardware and simulation sources. Applications consume messaging contracts. This keeps the consumer path identical between bench simulation and the vehicle:

```text
simulation source --\
                    > AutomotiveRuntime -> ZeroMQ -> application
physical source ---/
```

Switching between simulation and physical hardware therefore changes service composition, not application code or the wire contract.
