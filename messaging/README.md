# OpenRoadCode Messaging

The `messaging` package provides transport-independent publish/subscribe interfaces,
versioned domain contracts, message dispatch, and the current ZeroMQ transport.
Applications should consume public domain messages rather than reaching directly into
hardware-owning controllers when telemetry is available on the bus.

If you only want to consume telemetry, start with **Subscribe to one topic** below. A
new consumer should not need to understand ZeroMQ socket internals, hardware adapters,
or the producer implementation.

## Architecture

```text
hardware / simulator
        |
   domain state
        |
 contract publisher
        |
 ZeroMqPublisher
        |
   XSUB broker XPUB
        |
 ZeroMqSubscriber
        |
 MessageDispatcher
        |
 typed message handler
        |
 application state / UI
```

The broker is intentionally dumb. Topic ownership, schema validation, units, and typed
decoding belong to `messaging/contracts`.

The intended boundary is:

```text
producer implementation  -> SI domain state -> public contract -> bus
bus -> public contract decoder -> application state -> presentation units/UI
```

A subscriber therefore does not need to know whether a message came from physical
hardware, a simulator, a replay tool, or another process.

## Five-minute simulated setup

From the repository root, use three terminals.

Terminal 1, start the broker:

```bash
python3 -m messaging.zeromq.broker_cli
```

Terminal 2, start the navigation service with simulated hardware:

```bash
python3 -m services.navigation.navigation_service_cli --simulate
```

The service emits:

- `openroad.navigation.position`
- `openroad.navigation.motion`
- `openroad.navigation.attitude`
- `openroad.navigation.imu`

It also serves acknowledged navigation commands such as stationary calibration and
heading reset. See `services/navigation/README.md` for the command interface and physical
hardware startup options.

Terminal 3 can run an existing consumer, for example:

```bash
python3 -m messaging.component_test.navigation_state_dispatcher_cli
```

or the CarTUI:

```bash
python3 -m apps.carTui.main --demo
```

The same subscriber code works when the simulated navigation controller is replaced by
real hardware in the service.

## Broker endpoints

Default local connections are:

- publishers: `tcp://127.0.0.1:5556`
- subscribers: `tcp://127.0.0.1:5557`

The broker is the process that binds the TCP ports. Publishers and subscribers connect
to it. Use constants from `messaging.zeromq.endpoints` in application code instead of
copying port numbers.

## Subscribe to one topic

For application code, prefer `MessageDispatcher`. It owns the blocking receive loop,
decodes payloads, and invokes handlers on worker threads.

```python
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    VehicleStateMessage,
    decode_vehicle_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def on_vehicle_state(message: VehicleStateMessage) -> None:
    print(message.data.vehicle_speed_m_s)


subscriber = ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT)
dispatcher = MessageDispatcher(subscriber)
dispatcher.register(
    VEHICLE_STATE_TOPIC,
    decode_vehicle_state,
    on_vehicle_state,
)
dispatcher.start()

try:
    input("Receiving vehicle telemetry. Press Enter to stop.\n")
finally:
    dispatcher.close()
```

The three pieces a normal subscriber supplies are simply:

```text
topic constant + decoder + handler
```

Register every topic before calling `start()`.

## Subscribe to multiple topics

One dispatcher can subscribe to many topics over one subscriber connection:

```python
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def on_position(message):
    print("position", message.data)


def on_motion(message):
    print("motion", message.data)


def on_attitude(message):
    print("attitude", message.data)


def on_imu(message):
    print("imu", message.data)


dispatcher = MessageDispatcher(ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT))
dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, on_position)
dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, on_motion)
dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, on_attitude)
dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, on_imu)
dispatcher.start()

try:
    input("Receiving navigation telemetry. Press Enter to stop.\n")
finally:
    dispatcher.close()
```

A single `MessageDispatcher` per application is normally preferable to one subscriber
thread per topic.

For a latest-value application cache, use the shared thread-safe consumers in
`common.telemetry`: `NavigationBusState` and `VehicleBusState`. This keeps message
callbacks independent of Tk, curses, or another application package.

## Current public telemetry topics

| Topic | Contract | Purpose |
| --- | --- | --- |
| `openroad.vehicle.state` | automotive vehicle state | Engine, speed, pedal/load, pressures, temperatures, fuel and electrical state |
| `openroad.navigation.position` | navigation position | Geographic position, altitude, GPS fix and accuracy metadata |
| `openroad.navigation.motion` | navigation motion | Heading, ground/vertical speed and turn rate |
| `openroad.navigation.attitude` | navigation attitude | Heading, pitch and roll |
| `openroad.navigation.imu` | navigation IMU | Acceleration, linear acceleration and angular velocity vectors |

Public telemetry contracts use SI units unless explicitly documented otherwise.
Presentation layers should perform conversions such as m/s to mph or Pa to PSI. Shared
presentation conversions live in `common.units` so applications do not duplicate unit
math.

## Publish telemetry

Domain publishers accept normalized state and hide wire encoding from producers. For
navigation, normal runtime ownership belongs to the navigation service:

```bash
python3 -m services.navigation.navigation_service_cli --simulate
```

The service owns one `NavigationControllerIf` and fans each state sample out to position,
motion, attitude, and IMU contracts. The same controller instance handles acknowledged
navigation commands, so applications never need a second hardware-owning controller.

The lower-level `NavigationStatePublisher` remains available to producers and component
tests that intentionally own a controller.

## Commands are not telemetry

PUB/SUB is intended for continuously changing state. Commands that require acknowledgement
use an explicit request/reply service instead of being disguised as telemetry messages.
Navigation currently follows this pattern for stationary calibration and heading reset.
Applications depend on `ui.navigation.NavigationRequestHandlerIf`; the current process
transport is `ZeroMqNavigationRequestHandler` talking to the navigation service.

See `services/navigation/README.md` for examples.

## UI threading rule

`MessageDispatcher` handlers run on worker threads. Do not directly modify Tk, curses,
or another toolkit's UI objects from a handler. Update a thread-safe state/cache in the
handler, then render or marshal that state from the UI thread.

`common.telemetry.VehicleBusState` and `common.telemetry.NavigationBusState` implement
this pattern for the current vehicle and navigation contracts.

## PUB/SUB startup behavior

ZeroMQ PUB/SUB is asynchronous. A publisher may send messages before a subscriber's
subscription has propagated, and those early messages can be dropped. For deterministic
manual tests use this startup order:

1. broker
2. subscriber/application
3. producer service

Continuous telemetry publishers naturally tolerate late subscribers because another
sample will arrive shortly.

The bus is intended for continuously changing telemetry. Do not assume PUB/SUB provides
queue durability or replay semantics. If a future domain requires guaranteed delivery,
history, or command acknowledgement, that requirement should be designed explicitly
rather than quietly inferred from telemetry behavior.

## Error handling

`MessageDispatcher` can receive an application error callback:

```python
def on_error(topic: str, error: Exception) -> None:
    print(f"{topic}: {error}")


dispatcher = MessageDispatcher(
    ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT),
    error_handler=on_error,
)
```

Decode errors and handler failures are reported with the associated topic. Transport
receive failures use the synthetic topic name `receive`.

## Adding a new topic

A public contract should normally contain:

1. a topic constant
2. a versioned wire schema and validator
3. an encoder
4. a typed decoded message representation
5. a decoder
6. contract unit tests
7. a publisher helper when a domain state exists
8. an integration test through the broker when practical
9. an update to `docs/messaging/message_bus_idd.md`
10. an update to this topic catalog and subscriber documentation

Keep hardware parsing out of messaging contracts and keep UI formatting out of them.
The bus carries domain data, not implementation details or presentation choices.

## Testing the messaging layer

Useful checks from the repository root include:

```bash
python3 scripts/check_doxygen_contracts.py

python3 -m pytest \
  messaging/contracts \
  messaging/unit_test \
  messaging/integration_test -v
```

Component-test CLIs under `messaging/component_test` are useful for live diagnostics but
supplement rather than replace automated tests.

## Detailed interface document

See `docs/messaging/message_bus_idd.md` for framing, topology, lifecycle, contract rules,
and topic ownership details.
