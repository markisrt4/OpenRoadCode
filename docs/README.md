# OpenRoadCode Documentation

This directory is the central entry point for project documentation. Component READMEs remain beside the code they describe. Follow the links below rather than copying or symlinking those files.

The [project README](../README.md) is the main landing page, and [Doxygen](../Doxyfile) generates the API reference and documentation pages.

## Architecture and design

- [System architecture](architecture.md)
- [Applications architecture audit](apps_architecture_audit.md)
- [Ethernet interface design](ethernet_idd.md)
- [Interface design documents](idd/)
- [Messaging documentation](messaging/)
- [Navigation runtime](navigation_runtime.md)
- [Android sensor pipeline](android_sensor_pipeline.md)

## Applications and components

- [Automotive dashboard](../apps/automotive_dashboard/README.md)
- [Car terminal UI](../apps/carTui/README.md)
- [Applications](../apps/)
- [Controllers](../controllers/)
- [Services](../services/)
- [Messaging](../messaging/)
- [Hardware I/O](../hardware_io/)
- [Protocols](../protocols/)
- [User interfaces](../ui/)
- [Frontends](../frontends/)

## Development and deployment

- [Contributing](../CONTRIBUTING.md)
- [Development tools and platform setup](../development/)
- [Navigation deployment](navigation_deployment.md)
- [XDG paths](xdg_paths.md)
- [Doxygen configuration](../Doxyfile)

## Features and reference

- [Streaming radio](streaming_radio.md)
- [Roadmap](roadmap.md)
- [Vehicle one-wire reference](vehicle-one-wire.pdf)
- [Security policy](../SECURITY.md)

## Documentation conventions

Keep implementation-specific instructions in the owning component's README. Put cross-cutting architecture, deployment, and user guides under `docs/`. Link to canonical files instead of duplicating them. When adding a new component README, add a useful entry here and ensure Doxygen can discover it.
