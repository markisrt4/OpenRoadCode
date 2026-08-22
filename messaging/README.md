# OpenRoadCode Messaging

The `messaging` package provides transport-independent publish/subscribe interfaces,
versioned domain contracts, message dispatch, and the current ZeroMQ transport.
Applications should consume public domain messages rather than reaching directly into
hardware-owning controllers when telemetry is available on the bus.

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

## Start the local broker

From the repository root:

```bash
python3 -m messaging.zeromq.broker_cli
```

Default local connections are:

- publishers: `tcp://127.0.0.1:5556`
- subscribers: `tcp://127.0.0.1:5557`

Use constants from `messaging.zeromq.endpoints` in application code instead of copying
port numbers.

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

Register every topic before calling `start()`.

## Subscribe to multiple topics

One dispatcher can subscribe to many topics over one subscriber connection:

```python
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def on_position(message):
    print("position", message.data)


def on_attitude(message):
    print("attitude", message.data)


def on_imu(message):
    print("imu", message.data)


dispatcher = MessageDispatcher(ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT))
dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, on_position)
dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, on_attitude)
dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, on_imu)
dispatcher.start()
```

## Current public telemetry topics

| Topic | Contract | Purpose |
| --- | --- | --- |
| `openroad.vehicle.state` | automotive vehicle state | Engine, speed, pedal/load, pressures, temperatures, fuel and electrical state |
| `openroad.navigation.position` | navigation position | Geographic position, altitude, GPS fix and accuracy metadata |
| `openroad.navigation.motion` | navigation motion | Heading, ground/vertical speed and turn rate |
| `openroad.navigation.attitude` | navigation attitude | Heading, pitch and roll |
| `openroad.navigation.imu` | navigation IMU | Acceleration, linear acceleration and angular velocity vectors |

Public telemetry contracts use SI units unless explicitly documented otherwise.
Presentation layers should perform conversions such as m/s to mph or Pa to PSI.

## Publish telemetry

Domain publishers accept normalized state and hide wire encoding from producers. For
example, the complete navigation publisher fans one `NavigationState` sample out to
position, motion, attitude and IMU topics:

```python
from controllers.navigation import SimulatedNavigationController
from messaging.contracts.navigation import NavigationStatePublisher
from messaging.zeromq import ZeroMqPublisher
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT

controller = SimulatedNavigationController()
publisher = ZeroMqPublisher(LOCAL_PUBLISHER_ENDPOINT)
telemetry = NavigationStatePublisher(publisher, source="my-navigation-source")

controller.start()
try:
    telemetry.publish(controller.read_state())
finally:
    controller.stop()
    publisher.close()
```

For a live simulated source:

```bash
python3 -m messaging.component_test.navigation_state_publisher_cli
```

## UI threading rule

`MessageDispatcher` handlers run on worker threads. Do not directly modify Tk, curses,
or another toolkit's UI objects from a handler. Update a thread-safe state/cache in the
handler, then render or marshal that state from the UI thread.

The CarTUI `VehicleBusState` and `NavigationBusState` classes are examples of this
pattern.

## PUB/SUB startup behavior

ZeroMQ PUB/SUB is asynchronous. A publisher may send messages before a subscriber's
subscription has propagated, and those early messages can be dropped. For deterministic
manual tests use this startup order:

1. broker
2. subscriber/application
3. publisher

Continuous telemetry publishers naturally tolerate late subscribers because another
sample will arrive shortly.

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

Keep hardware parsing out of messaging contracts and keep UI formatting out of them.
The bus carries domain data, not implementation details or presentation choices.

## Detailed interface document

See `docs/messaging/message_bus_idd.md` for framing, topology, lifecycle, contract rules,
and topic ownership details.
