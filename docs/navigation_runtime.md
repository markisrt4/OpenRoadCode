# OpenRoadCode Navigation Runtime

## Purpose

This document describes the vehicle-side navigation runtime: service ownership, startup order, ZeroMQ responsibilities, routing, route guidance, and the intended turn-by-turn lifecycle.

Map generation and deployment are documented separately in `docs/navigation_deployment.md`. Public message schemas are documented under `docs/idd/`.

## Runtime architecture

```text
                         vehicle startup
                               |
             +-----------------+-----------------+
             |                                   |
             v                                   v
          gpsd                         openroadcode-zmq.service
             |                         publisher ingress :5556
             |                         subscriber egress :5557
             |                                   |
             +-------------------+---------------+
                                 |
                         valhalla.service
                                 |
                                 v
                  openroadcode-navigation.service
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
      navigation solution   route planning    navigation session
      position/attitude       Valhalla        route + rerouting
              |                                     |
              +------------------+------------------+
                                 |
                                 v
                       route guidance state
                                 |
                                 v
                         ZeroMQ subscribers
                         CarUi / CarTui / logs
```

## Service ownership

### `openroadcode-zmq.service`

Owns the process-wide ZeroMQ XPUB/XSUB broker. Producers connect to the publisher ingress endpoint and consumers connect to the subscriber egress endpoint. The broker contains no navigation policy.

Runtime wrapper: `scripts/runtime/start_zeromq_broker.sh`

Installer: `scripts/systemd/install_zeromq_systemd.sh`

### `valhalla.service`

Owns the local Valhalla HTTP routing engine and reads the deployed routing dataset. It calculates routes but does not own the active navigation session.

Runtime wrapper: `scripts/runtime/start_valhalla.sh`

Installer: `scripts/systemd/install_valhalla_systemd.sh`

### `openroadcode-navigation.service`

Owns vehicle navigation state and the navigation command endpoint. It publishes normalized navigation telemetry and uses Valhalla when route planning is enabled.

The production target is for this same service to own the active `NavigationSessionController` and `RouteGuidanceController`. Keeping session and guidance ownership here prevents a second daemon from having to duplicate active-route state.

Runtime wrapper: `scripts/runtime/start_navigation_service.sh`

Installer: `scripts/systemd/install_navigation_service_systemd.sh`

## Startup

Install the complete runtime stack from the repository root:

```bash
sudo scripts/systemd/install_navigation_runtime_systemd.sh
```

The installer creates and enables services in dependency order:

1. `openroadcode-zmq.service`
2. `valhalla.service`
3. `openroadcode-navigation.service`

The navigation unit orders itself after the broker and Valhalla so telemetry and routing dependencies are available before navigation starts. `gpsd.service` is also ordered before navigation when present.

Check the complete stack with:

```bash
systemctl --no-pager --full status \
    openroadcode-zmq \
    valhalla \
    openroadcode-navigation
```

Logs are available through journald:

```bash
journalctl -u openroadcode-zmq -b
journalctl -u valhalla -b
journalctl -u openroadcode-navigation -b
```

## Turn-by-turn lifecycle

The intended production lifecycle is:

```text
UI/client requests destination
          |
          v
navigation command service
          |
          v
route planning controller -> Valhalla HTTP API
          |
          v
NavigationSessionController
  owns destination + travel mode + active route
          |
          v
RouteGuidanceController
  consumes normalized geographic position
          |
          +--> maneuver + distance-to-turn
          +--> route progress
          +--> off-route state
          +--> arrival state
          |
          v
route_guidance.state -> ZeroMQ -> presentation clients
```

`NavigationSessionController` owns rerouting policy. `RouteGuidanceController` derives route-relative state but does not decide when a replacement route should be calculated.

CarUi and other presentation clients must not call Valhalla directly or implement rerouting policy. They request navigation actions through the navigation command interface and subscribe to public navigation/guidance state.

## Public messaging

Navigation telemetry and route guidance are presentation-neutral contracts transported through the ZeroMQ broker.

Route guidance is published on `route_guidance.state`. See `docs/idd/route_guidance_state.md` for the versioned JSON schema, SI units, nullable maneuver fields, and consumer requirements.

The broker is transport only. Coordinate-frame semantics, units, source identity, validation, and schema versioning belong to the individual messaging contracts and IDDs.

## Failure behavior

Each systemd unit uses restart-on-failure semantics. A failed UI must not terminate navigation services. A failed navigation consumer must not affect the broker or producer.

If Valhalla is unavailable, navigation telemetry should remain independently useful even though route calculation cannot succeed. The navigation service owns graceful reporting of route-planning availability to command clients.

Port/address conflicts are configuration or deployment errors. Services should fail with a clear diagnostic rather than silently selecting another endpoint, because consumers rely on stable configured endpoints.

## Testing

Controller behavior is covered by unit tests under:

```text
controllers/route_guidance/unit_test/
controllers/navigation_session/unit_test/
```

Messaging contract tests live with their contracts. End-to-end navigation/guidance exercises live under `apps/common/component_test/`.

Static systemd/runtime wiring tests live under:

```text
scripts/systemd/unit_test/
```

Before merging navigation runtime changes, run at minimum:

```bash
python -m pytest \
    controllers/route_guidance/unit_test \
    controllers/navigation_session/unit_test \
    messaging/contracts/route_guidance \
    services/navigation/unit_test \
    scripts/systemd/unit_test -v
```

On a Raspberry Pi deployment target, also verify the real boot boundary:

```bash
sudo systemctl restart openroadcode-zmq valhalla openroadcode-navigation
systemctl --no-pager --full status openroadcode-zmq valhalla openroadcode-navigation
```

A reboot test is required before treating startup changes as deployment-ready.

## Design rules

- ZeroMQ owns transport, not navigation policy.
- Valhalla owns route calculation, not active-route state.
- The navigation service owns normalized navigation state and navigation-session orchestration.
- Route guidance is derived state and is published through a versioned contract.
- Presentation clients subscribe; they do not own routing or rerouting logic.
- Startup dependencies must be explicit in systemd rather than relying on timing delays.
- Service endpoints remain stable and configuration-driven.
- Runtime services must be independently restartable and observable through journald.
