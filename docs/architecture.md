# OpenRoadCode Architecture

OpenRoadCode deliberately separates **commands/behavior** from **telemetry/state**. These paths solve different problems and should not be collapsed into one dependency chain.

## Command and behavior path

Applications use controller interfaces when they need to request behavior such as changing a radio frequency, controlling audio, changing lighting, or starting an external application.

```text
Application / UI
      |
      v
Controller interface
      |
      v
Concrete controller
      |
      v
Hardware adapter / protocol
      |
      v
Linux service / physical hardware
```

This path uses dependency injection so applications can run against real, simulated, stub, or unconfigured implementations.

## Telemetry and state path

Continuously changing public state is distributed through the message bus instead of requiring every application to own or directly reference the producing controller.

```text
Physical hardware / simulator
          |
          v
   Domain state in SI
          |
          v
    Contract publisher
          |
          v
      Message bus
          |
          v
 Contract decoder / dispatcher
          |
          v
 Thread-safe application state
          |
          v
     Frontend / UI
```

This lets CarUI, CarTUI, WebUI, diagnostics, recorders, and future applications consume the same telemetry without coupling themselves to the hardware implementation.

A consumer should not need to know whether telemetry originated from physical hardware, a simulator, a replay process, or another computer on the vehicle network.

## Public telemetry today

Current public bus domains include:

- vehicle state
- navigation position
- navigation motion
- navigation attitude
- navigation IMU

See [`messaging/README.md`](../messaging/README.md) for the subscriber quick start and [`docs/messaging/message_bus_idd.md`](messaging/message_bus_idd.md) for the detailed interface design.

## Units

Domain state and public telemetry contracts use **SI units** unless a contract explicitly documents otherwise.

```text
hardware -> SI domain state -> SI bus contract -> application state
                                               |
                                               v
                                         presentation
                                               |
                           +-------------------+-------------------+
                           |                                       |
                       imperial                                metric
```

Presentation conversions belong at the frontend boundary. Shared conversion functions and `UnitSystem` live in `common.units` so CarUI, CarTUI, WebUI, diagnostics, and future consumers use the same conversion math.

Do not publish separate metric and imperial topics.

## Threading

`MessageDispatcher` owns one blocking subscriber receive thread and delegates decoded handlers to worker threads. UI toolkits are generally thread-affine, so dispatcher handlers should update a thread-safe cache/state object rather than manipulating widgets directly.

CarTUI's `VehicleBusState` and `NavigationBusState` are reference examples of this pattern.

## Package responsibilities

| Package | Responsibility |
| --- | --- |
| `apps/` | Application assembly, screens, and app-specific state |
| `controllers/` | Application-facing behavior and domain coordination |
| `messaging/` | Public telemetry contracts, dispatch, and transports |
| `frontends/` | Toolkit-specific reusable presentation |
| `ui/` | Toolkit-independent presentation contracts |
| `common/` | Cross-cutting neutral utilities such as unit conversion |
| `input_events/` | Normalized physical-input contracts and values |
| `hardware_io/` | Device-specific adapters |
| `protocols/` | Communication protocols and wire/device parsing |
| `config/` | Runtime and hardware configuration |

Lower-level packages must not import application implementations merely to obtain state or behavior.

## Adding telemetry

When exposing a new public telemetry domain:

1. Normalize the producer's data into domain/SI values.
2. Define a stable topic constant and versioned contract.
3. Add validation, encoder, typed decoded message, and decoder.
4. Add contract unit tests.
5. Add a publisher helper when a domain state already exists.
6. Add an integration test through the broker when practical.
7. Consume the message through application state rather than directly from hardware.
8. Update the message-bus IDD and `messaging/README.md`.

The message bus carries domain data. Hardware quirks stay below it; UI formatting stays above it.

## Adding behavior

Not every feature belongs on the message bus. Commands and synchronous operations should normally continue to use narrow controller interfaces. A useful rule is:

- **"Do this"** usually belongs behind a controller interface.
- **"This is the current state"** is a candidate for telemetry.

Use the simplest boundary that preserves testability and implementation independence. Architecture is supposed to remove problems, not breed them for sport.
