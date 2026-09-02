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

Physical serial ELM327 example for Linux/Raspberry Pi:

```toml
[services.automotive]
enabled = true
rate_hz = 10.0

[services.automotive.input]
source = "device"
device = "elm327"
transport = "serial"
port = "/dev/rfcomm0"
baud = 38400
timeout_s = 1.0
slow_poll_interval_s = 5.0

[services.automotive.publish]
enabled = true
source = "obd2"
```

Termux uses the Android Bluetooth bridge over localhost TCP rather than a local
serial device:

```toml
[services.automotive]
enabled = true
rate_hz = 10.0

[services.automotive.input]
source = "device"
device = "elm327"
transport = "tcp"
host = "127.0.0.1"
tcp_port = 35000
timeout_s = 2.0
slow_poll_interval_s = 5.0

[services.automotive.publish]
enabled = true
source = "automotive-service-android"
```

`Elm327Device` owns the serial transport and `Elm327TcpDevice` owns the TCP
transport. Both feed the same `Elm327ObdAdapter`, `Obd2Manager`,
`AutomotiveRuntime`, and public `VehicleState` contract. This keeps the
Raspberry Pi/Linux and Termux compositions symmetric above the transport
boundary.

The manager polls RPM, vehicle speed, throttle, accelerator position, engine load, and manifold pressure on each snapshot. Slower-changing values such as barometric pressure, airflow, coolant/intake temperature, fuel level, and module voltage use `slow_poll_interval_s`.

## Gear estimation

The automotive runtime can augment each published `VehicleState` with an
estimated `transmission_gear`. The estimator compares engine speed and road
speed against a learned ratio profile.

By default the service looks for `vehicle_gears.learned.toml`. A different
profile can be supplied with `--gear-profile`. If the profile does not exist,
gear estimation is safely disabled.

Learn a manual-transmission profile with:

```bash
python -m scripts.automotive.learn_gears
```

The ratio estimator identifies forward gears only. RPM and road speed alone
cannot reliably distinguish neutral or reverse, and the estimator intentionally
returns an unknown gear during shifts, clutch slip, very low speed, or a poor
ratio match.

`transmission_gear` is part of the public `openroad.vehicle.state` schema.
After deploying a wire-contract change, restart long-running supervised
producer processes so an older service does not continue publishing the prior
schema.

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

For a serial Bluetooth ELM327 on Linux/Raspberry Pi, `/dev/rfcomm0` must already exist and be connected before starting the service. Termux instead uses the configured Android bridge TCP endpoint.

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
