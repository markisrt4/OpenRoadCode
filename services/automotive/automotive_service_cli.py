# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode automotive telemetry service."""

from __future__ import annotations

import argparse
from pathlib import Path

from config.service_runtime_config import AutomotiveServiceRuntimeConfig, ServiceRuntimeConfigParser
from controllers.automotive.simulated_vehicle_state_source import SimulatedVehicleStateSource
from messaging.zeromq import ZeroMqPublisher
from services.automotive.automotive_runtime import AutomotiveRuntime

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "config" / "runtime.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish automotive telemetry.")
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    return parser.parse_args()


def build_source(config: AutomotiveServiceRuntimeConfig):
    """Build the configured complete vehicle-state source."""
    if config.input.source == "simulation":
        return SimulatedVehicleStateSource()
    raise ValueError(
        "Automotive device source is not composed yet; use source = 'simulation'"
    )


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    config = system.automotive
    if not config.enabled:
        print("Automotive service disabled by runtime configuration")
        return 0
    if not config.publish.enabled:
        print("Automotive publishing disabled by runtime configuration")
        return 0

    source = build_source(config)
    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)
    runtime = AutomotiveRuntime(
        source,
        publisher,
        publish_source=config.publish.source,
        rate_hz=config.rate_hz,
    )
    print("OpenRoadCode automotive service")
    print(f"  input source:      {config.input.source}")
    print(f"  telemetry ingress: {system.messaging.publisher_endpoint}")
    print(f"  publish rate:      {config.rate_hz:g} Hz")
    print(f"  publish source:    {config.publish.source}")
    print("Ctrl+C to stop")
    try:
        runtime.run()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()
        publisher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
