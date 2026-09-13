# Automotive Architecture

OpenRoadCode treats vehicle telemetry as a domain capability, not as an ELM327 feature. The current reference implementation uses SAE J1979 over an ELM327-compatible adapter, but the public automotive model is intentionally independent of that hardware.

This document describes the architectural boundaries, adaptive telemetry profiles, ECU interpretation, trip analytics, UI ownership, and the extension path for future automotive sources.

## Architectural goals

The automotive stack follows five rules:

1. **Hardware does not define the public vehicle model.** ELM327, SocketCAN, J2534, OEM CAN decoders, Ethernet diagnostics, simulation, and future sources should converge on the same domain state where possible.
2. **Public telemetry is semantic and SI-normalized.** Applications consume engine speed, pressure, temperature, fuel state, and similar measurements rather than adapter commands or PID bytes.
3. **Resource management stays with the source that needs it.** The request-limited OBD-II path owns its polling scheduler. A passive CAN source is not required to imitate OBD polling.
4. **Presentation consumes meaning, not protocol mechanics.** Gauges, ECU interpretation, and Trip analytics consume domain and presentation models. They do not send ELM327 commands.
5. **A telemetry profile expresses intent, not transport behavior.** HOME, PERFORMANCE, ENGINE, ECU, TRIP, and BACKGROUND describe which information matters most. Each source may honor that intent in the way appropriate to its transport.

## End-to-end architecture

The most important boundary is VehicleStateSourceIf. Everything below that interface may be hardware- or protocol-specific. Everything above it consumes a normalized VehicleState.

<aside class="orc-diagram-legend" aria-label="Architecture diagram legend">
  <strong>Diagram key</strong>
  <span><i class="orc-legend-swatch orc-legend-app"></i>App / UI</span>
  <span><i class="orc-legend-swatch orc-legend-service"></i>Service / runtime</span>
  <span><i class="orc-legend-swatch orc-legend-controller"></i>Controller / domain</span>
  <span><i class="orc-legend-swatch orc-legend-message"></i>Messaging / contract</span>
  <span><i class="orc-legend-swatch orc-legend-adapter"></i>Protocol / hardware</span>
  <span><i class="orc-legend-swatch orc-legend-external"></i>External / input</span>
</aside>

~~~mermaid
flowchart LR
    subgraph Inputs["Vehicle telemetry sources"]
        direction TB
        Elm["ELM327-compatible adapter"]
        Sim["Simulation"]
        Can["SocketCAN / raw CAN<br/>future"]
        J2534["J2534 passthrough<br/>future"]
        Oem["OEM decoder / DoIP<br/>future"]
    end

    subgraph SourceLayer["Source implementations"]
        direction TB
        OBD["Obd2Manager"]
        SimSrc["SimulatedVehicleStateSource"]
        CanSrc["CAN VehicleStateSource<br/>future"]
        OtherSrc["Other VehicleStateSource<br/>future"]
    end

    SourceIf["VehicleStateSourceIf"]
    State["VehicleState<br/>SI-normalized domain snapshot"]
    Runtime["AutomotiveRuntime"]
    Pub["VehicleStatePublisher"]
    Bus["openroad.vehicle.state"]

    subgraph Consumers["Domain + application consumers"]
        direction TB
        Analyzer["EngineAnalyzer<br/>EngineAnalysis"]
        Trip["Trip accumulation<br/>fuel / boost / enrichment"]
        Presenter["VehiclePresenter"]
        Screens["orcUi vehicle screens<br/>Gauges · ECU · Trip"]
    end

    Elm --> OBD
    Sim --> SimSrc
    Can --> CanSrc
    J2534 --> OtherSrc
    Oem --> OtherSrc

    OBD --> SourceIf
    SimSrc --> SourceIf
    CanSrc --> SourceIf
    OtherSrc --> SourceIf

    SourceIf --> State --> Runtime --> Pub --> Bus
    Bus --> Analyzer
    Bus --> Trip
    Bus --> Presenter --> Screens
    Analyzer --> Screens
    Trip --> Screens

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcService fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;

    class Elm,Sim,Can,J2534,Oem orcExternal;
    class OBD,SimSrc,CanSrc,OtherSrc,Analyzer,Trip,Presenter orcController;
    class SourceIf,State,Pub,Bus orcMessage;
    class Runtime orcService;
    class Screens orcApp;
~~~

The diagram deliberately shows several possible sources converging on the same domain boundary. ELM327 is therefore one implementation path, not the definition of OpenRoadCode automotive telemetry.

## OBD-II and ELM327 boundaries

The current reference vehicle reaches the domain model through two distinct abstractions.

Obd2AdapterIf is the OBD-II transport boundary. It accepts normalized Obd2Request values and returns normalized Obd2Response values. A concrete adapter may use ELM327, J2534, SocketCAN/ISO-TP, or another mechanism as long as it can satisfy that contract.

VehicleStateSourceIf is the vehicle-domain boundary. Obd2Manager implements it by decoding supported PIDs, caching measurements, deriving values such as boost pressure, and returning a complete VehicleState.

~~~mermaid
flowchart LR
    subgraph Hardware["Hardware / transport"]
        Bridge["Android Bridge<br/>Bluetooth SPP → localhost TCP"]
        Serial["Linux serial / RFCOMM"]
        Other["Other J1979 transport<br/>future"]
    end

    subgraph ElmLayer["ELM327 implementation"]
        Tcp["Elm327TcpDevice"]
        SerialDev["Elm327Device"]
        ElmAdapter["Elm327ObdAdapter"]
    end

    ObdIf["Obd2AdapterIf<br/>J1979 request/response boundary"]
    Manager["Obd2Manager<br/>PID decode · cache · derived state"]
    SourceIf["VehicleStateSourceIf"]
    Vehicle["VehicleState"]

    Bridge --> Tcp --> ElmAdapter
    Serial --> SerialDev --> ElmAdapter
    ElmAdapter --> ObdIf
    Other --> ObdIf
    ObdIf --> Manager --> SourceIf --> Vehicle

    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;

    class Bridge,Serial,Other orcExternal;
    class Tcp,SerialDev,ElmAdapter orcAdapter;
    class Manager orcController;
    class ObdIf,SourceIf,Vehicle orcMessage;
~~~

A replacement adapter that still exposes standardized OBD-II data normally requires a new Obd2AdapterIf implementation, not changes to the UI or public vehicle contract.

A richer source that does not naturally fit OBD-II may bypass Obd2Manager entirely and implement VehicleStateSourceIf directly.

## VehicleState domain model

VehicleState is the canonical automotive snapshot used above the source boundary. Its fields describe vehicle and engine measurements rather than protocol identifiers.

Examples include engine angular speed, road speed, throttle and commanded throttle, calculated and absolute engine load, manifold and barometric pressure, derived boost pressure, coolant and intake-air temperature, fuel level and fuel rate, commanded and measured equivalence ratio, short- and long-term fuel trim, ignition timing, fuel-rail pressure, and control-module voltage.

Physical quantities are normalized to SI at the domain boundary. Presentation code converts them to driver-facing units such as RPM, MPH, PSI, Fahrenheit, and gallons.

None means that a measurement is currently unavailable or unsupported. A source is not required to fabricate a value merely to satisfy the shape of the snapshot.

## Navigation-owned road speed

Road speed is intentionally not consumed from the scarce OBD request budget in the reference composition. Navigation ground motion provides vehicle speed and the automotive runtime composes that motion with engine telemetry.

~~~mermaid
flowchart LR
    GPS["GNSS / Android location"] --> Nav["Navigation GroundMotion"]
    ECU["OBD / engine source"] --> Engine["Cached engine telemetry"]

    Nav --> Compose["Automotive composition"]
    Engine --> Compose
    Compose --> State["VehicleState"]

    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;

    class GPS,ECU orcExternal;
    class Nav,Engine,Compose orcController;
    class State orcMessage;
~~~

This is a composition decision, not a universal rule for every future source. A source that already receives authoritative vehicle speed may expose it, but the application contract remains the same.

## Adaptive telemetry profiles

The tested KONNWEI/ELM327 Bluetooth path is request-limited. Repeated live measurements showed roughly six OBD transactions per second through:

    Termux → TCP → Android Bridge → Bluetooth SPP → ELM327 → ECU

A six-request budget cannot refresh every supported PID at gauge-like rates. OpenRoadCode therefore uses semantic telemetry profiles to spend the available bandwidth where it has the most value.

| Profile | User context | Primary intent |
| --- | --- | --- |
| HOME | Home screen visible | Keep glance telemetry fresh while preserving Trip inputs |
| PERFORMANCE | Performance gauges visible | Prioritize RPM and MAP/boost responsiveness |
| ENGINE | Engine screen visible | Favor engine condition, temperatures, load, and supporting data |
| ECU | ECU screen visible | Favor trims, lambda, load, throttle control, timing, and fuel-control data |
| TRIP | Trip screen visible | Favor fuel/trip analytics inputs |
| BACKGROUND | No automotive screen demanding fast response | Preserve continuous Trip quality with low-rate situational telemetry |

~~~mermaid
flowchart TD
    UI["Current UI context"] --> Profile{"Telemetry profile"}

    Profile --> Home["HOME<br/>glance metrics + trip continuity"]
    Profile --> Perf["PERFORMANCE<br/>RPM + MAP urgent"]
    Profile --> Engine["ENGINE<br/>temps + load + engine health"]
    Profile --> Ecu["ECU<br/>lambda + trims + control state"]
    Profile --> Trip["TRIP<br/>fuel / trip inputs"]
    Profile --> Bg["BACKGROUND<br/>trip-biased continuity"]

    Home --> Scheduler["Source-specific scheduling policy"]
    Perf --> Scheduler
    Engine --> Scheduler
    Ecu --> Scheduler
    Trip --> Scheduler
    Bg --> Scheduler

    Scheduler --> OBD["OBD source:<br/>change PID request weighting"]
    Scheduler --> Passive["Passive CAN source:<br/>may ignore or reinterpret"]
    Scheduler --> Future["Future source:<br/>source-appropriate behavior"]

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;

    class UI,Home,Perf,Engine,Ecu,Trip,Bg orcApp;
    class Profile,Scheduler orcController;
    class OBD,Passive,Future orcAdapter;
~~~

The profile is intentionally generic. The current OBD implementation maps it to weighted supported-PID groups. A passive CAN implementation may already receive all relevant frames continuously and may choose to ignore the hint or use it only to control downstream decoding/publication cost.

### OBD scheduler behavior

Obd2Manager discovers supported Mode 01 PIDs on connection. Unsupported PIDs are excluded from scheduling so they do not consume request opportunities.

Each service tick performs at most one physical OBD request. The resulting measurement updates a cache, and read_state returns the complete cached snapshot. A transient missing response does not erase the last valid cached measurement.

Current profiles use weighted group schedules. They are intentionally a source-local implementation detail and may evolve toward deadline/freshness scheduling without changing AutomotiveTelemetryProfile.

## ECU interpretation

The ECU screen is not intended to be a raw PID viewer. EngineAnalyzer converts the current vehicle snapshot into EngineAnalysis, which expresses driver-meaningful concepts such as operating mode, fuel-control mode, mixture mode, mixture tracking quality, throttle tracking quality, fuel-correction status, engine-load level, and warm-up/high-load/enrichment/boost conditions.

High load, boost, enrichment, and warm-up are modeled as conditions rather than mutually exclusive operating modes. For example, the engine may be accelerating while simultaneously under high load, in boost, and enriched.

~~~mermaid
flowchart LR
    State["VehicleState"] --> Analyzer["EngineAnalyzer"]
    Analyzer --> Analysis["EngineAnalysis"]

    Analysis --> Fuel["Fuel control<br/>mode + correction"]
    Analysis --> Mix["Mixture<br/>rich / stoich / lean<br/>tracking quality"]
    Analysis --> Load["Engine load<br/>low / moderate / high"]
    Analysis --> Conditions["Conditions<br/>boost · enrichment<br/>warm-up · high load"]

    Fuel --> ECU["ECU Monitor"]
    Mix --> ECU
    Load --> ECU
    Conditions --> ECU

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;

    class State,Analysis orcMessage;
    class Analyzer,Fuel,Mix,Load,Conditions orcController;
    class ECU orcApp;
~~~

Raw measurements remain available as supporting evidence, but interpretation belongs in the controller/domain layer rather than in Tk widgets.

## Trip analytics

Trip is the historical counterpart to the ECU screen.

- **Gauges** answer: what is the vehicle doing right now?
- **ECU** answers: what is engine management doing right now, and why?
- **Trip** answers: what happened over the drive?

Trip accumulation continues even when the Trip screen is not visible. BACKGROUND is deliberately trip-biased so leaving Vehicle does not substantially degrade accumulated analytics.

Advanced fuel metrics should prefer defensible measurements such as total fuel used, average fuel economy, time in boost, distance in boost, fuel consumed while boosted, share of trip fuel consumed while boosted, time enriched, high-load duration, and peak boost.

A metric claiming fuel caused by boost requires a defensible counterfactual baseline. Until such a model exists, OpenRoadCode should report measured association, such as "fuel consumed while boosted", rather than claiming an exact boost penalty.

## Vehicle configuration and induction type

Vehicle configuration distinguishes naturally aspirated and forced-induction vehicles. This affects presentation and interpretation, not the public telemetry transport.

Forced-induction vehicles may show boost-specific gauges, conditions, and Trip metrics. Naturally aspirated vehicles should omit those elements rather than displaying permanent N/A placeholders.

## UI contract guidance

The legacy VehicleUiIf contains independent setters for physical measurements. It remains useful for compatible frontends, but it should not become the dumping ground for every new ECU measurement.

For new orcUi work, prefer coherent presentation/domain state:

- VehiclePresentationState for driver-facing current measurements
- EngineAnalysis for interpreted engine-management state
- TripPresentationState for accumulated trip metrics

If a reusable UI contract is needed, prefer purpose-specific interfaces over one ever-growing vehicle interface. Candidate boundaries include motion/gear, engine telemetry, engine-management interpretation, trip analytics, and diagnostics.

The test for adding a field to a UI contract is not "the ECU exposes it". The field should be added only when a UI abstraction genuinely needs that semantic measurement.

## Adding a new automotive source

A contributor adding a new source should choose the narrowest applicable extension point.

### New transport for standardized OBD-II

Implement Obd2AdapterIf when the new hardware still exposes SAE J1979 requests and responses.

Examples include J2534 passthrough, SocketCAN + ISO-TP OBD, and non-ELM USB diagnostic adapters. The existing PID decoders, Obd2Manager, cache, domain conversion, messaging, EngineAnalyzer, Trip, and UIs can remain unchanged.

### New non-OBD source

Implement VehicleStateSourceIf when the new source already has decoded vehicle semantics or uses a richer proprietary protocol.

Examples include an OEM CAN database / DBC decoder, gateway service, DoIP source, or manufacturer-specific telemetry API. Translate the source into canonical VehicleState fields. Do not expose transport frames directly to applications.

### New measurement not represented by VehicleState

Add a domain field only when the value has stable vehicle meaning independent of one adapter. Keep adapter-only metadata and protocol diagnostics below the domain boundary.

## Dependency rules

The intended dependency direction is:

~~~mermaid
flowchart BT
    HW["hardware_io<br/>physical transports"]
    Proto["protocols<br/>OBD-II / CAN models"]
    Ctrl["controllers/automotive<br/>domain sources + analysis"]
    Svc["services/automotive<br/>lifecycle + composition"]
    Msg["messaging/contracts/automotive<br/>public wire state"]
    App["apps / frontends<br/>presentation"]

    HW --> Ctrl
    Proto --> Ctrl
    Ctrl --> Svc
    Ctrl --> Msg
    Svc --> Msg
    Msg --> App
    Ctrl --> App

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcService fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;

    class HW orcAdapter;
    class Proto,Msg orcMessage;
    class Ctrl orcController;
    class Svc orcService;
    class App orcApp;
~~~

The important prohibition is the reverse dependency: applications must not reach down into ELM327 devices, Bluetooth transports, or raw OBD requests just to render vehicle state.

## Related documentation

- [Automotive service](../services/automotive/README.md)
- [Automotive controllers](../controllers/automotive/README.md)
- [OBD-II controller](../controllers/automotive/obd2/README.md)
- [OBD-II protocol models](../protocols/obd2/README.md)
- [ELM327 hardware implementation](../hardware_io/automotive/elm327/README.md)
- [Automotive vehicle-state IDD](idd/automotive_vehicle_state.md)
- [Messaging overview](../messaging/README.md)
