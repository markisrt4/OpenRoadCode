# OpenRoadCode Message Bus IDD

## Purpose

This document defines the application-facing messaging interface used by OpenRoadCode producers and consumers. The bus is intentionally transport-light: domain contracts own schema and validation, while ZeroMQ only carries topic-prefixed JSON messages.

## Topology

```text
Publishers                         Subscribers
    |                                  ^
    | connect                           | connect
    v                                  |
tcp://127.0.0.1:5556             tcp://127.0.0.1:5557
    |                                  ^
    v                                  |
   XSUB ----------- zmq.proxy -------- XPUB
                 broker
```

The broker is the only process that binds the TCP ports. Publishers and subscribers connect to it.

Default endpoints are defined in `messaging/zeromq/endpoints.py`:

- broker publisher ingress bind: `tcp://0.0.0.0:5556`
- broker subscriber egress bind: `tcp://0.0.0.0:5557`
- local publisher connection: `tcp://127.0.0.1:5556`
- local subscriber connection: `tcp://127.0.0.1:5557`

## Message framing

Each bus message is a two-part ZeroMQ multipart message:

1. UTF-8 topic string
2. JSON object payload

Example conceptual frame:

```text
openroad.vehicle.state
{"version":1,"timestamp":...,"source":"obd2","data":{...}}
```

Payloads must be JSON objects. Every public contract owns its encoder, decoder, validator, typed decoded representation, schema version, and topic constant.

## Contract rules

Public telemetry contracts use SI units unless a contract explicitly documents otherwise. Presentation layers may convert SI values for display, but producers must not publish UI-oriented units such as mph, PSI, Fahrenheit, or percent where the domain representation is m/s, Pa, K, or a 0.0..1.0 ratio.

Encoders validate their own output before publication. Decoders validate before constructing typed messages. Unknown or missing fields are rejected for strict versioned contracts.

## Current topics

### `openroad.navigation.position`

Owns absolute position/fix information such as latitude, longitude, altitude, accuracy, source and fix metadata.

### `openroad.navigation.motion`

Owns motion information that is independent of the absolute position contract, including heading, ground speed, vertical speed and turn rate where available or derived.

### `openroad.vehicle.state`

Owns current automotive telemetry. Version 1 includes:

- `engine_speed_rad_s`
- `vehicle_speed_m_s`
- `throttle_position`
- `accelerator_pedal_position`
- `engine_load`
- `intake_manifold_pressure_pa`
- `barometric_pressure_pa`
- `boost_pressure_pa`
- `mass_air_flow_kg_s`
- `coolant_temperature_k`
- `intake_air_temperature_k`
- `fuel_level`
- `control_voltage_v`

## Consumer architecture

Applications should normally create one `MessageDispatcher` for one subscriber connection and register multiple topics with it.

```text
ZeroMqSubscriber
      |
MessageDispatcher
   |       |       |
position motion vehicle
   |       |       |
 UI/state handlers
```

The dispatcher owns one receiver thread. Decoding occurs after receipt and handlers are submitted to an executor so slow handlers do not block bus reception.

A ZeroMQ socket must remain on the thread that owns it. `ZeroMqSubscriber` therefore creates its socket lazily on the thread that first calls `receive()` and releases that transport from the same owning thread during shutdown.

UI toolkit objects must not be mutated directly from dispatcher worker threads. Consumers should update a thread-safe state/cache from handlers, then marshal or poll that state on the UI toolkit thread.

## Publisher architecture

Hardware and simulators should normalize data into domain state before publication. A typical automotive path is:

```text
ELM327 transport or simulated adapter
              |
         Obd2Manager
              |
      VehicleState [SI]
              |
   VehicleStatePublisher
              |
      ZeroMqPublisher
```

Consumers must not know whether the source is simulated or physical hardware.

## Lifecycle

Recommended startup order for deterministic component testing:

1. start broker
2. start subscribers/applications
3. start publishers

ZeroMQ PUB/SUB subscriptions need time to propagate and early messages may be dropped. Continuous publishers should therefore tolerate slow joiners.

Recommended shutdown order is application-specific, but each dispatcher and publisher must be explicitly closed. `MessageDispatcher.close()` stops reception and drains/cancels executor work. ZeroMQ sockets should use zero linger for prompt application shutdown unless a future reliability requirement says otherwise.

## Diagnostics

Consumer state models may expose a monotonically increasing receive counter and latest message timestamp. These are diagnostic metadata only and are not part of the public telemetry contract. They distinguish:

- no messages arriving
- messages arriving with unchanged values
- stale data
- decode or handler errors

## Configuration boundary

Code must consume endpoint constants from `messaging/zeromq/endpoints.py` rather than duplicating port literals. Application-specific environment variables may override endpoints, but default topology semantics remain publisher ingress on 5556 and subscriber egress on 5557.

## Extending the bus

A new public message type should include, at minimum:

1. topic constant
2. typed decoded message representation
3. encoder
4. validator
5. decoder
6. unit tests for valid and invalid payloads
7. publisher helper when a domain state object exists
8. IDD update documenting topic ownership and units

Do not place hardware-specific parsing or UI-specific presentation logic in a public messaging contract.
