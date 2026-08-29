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
    if config.input.device != "elm327":
        raise ValueError(f"Unsupported automotive device: {config.input.device}")

    # Keep physical-device dependencies out of simulation-only deployments.
    from controllers.automotive.obd2.elm327_obd_adapter import Elm327ObdAdapter
    from controllers.automotive.obd2.obd2_manager import Obd2Manager
    from hardware_io.automotive.elm327 import Elm327Device

    if config.input.transport == "tcp":
        from hardware_io.automotive.tcp_stream_transport import TcpStreamTransport

        transport = TcpStreamTransport(
            host=config.input.host,
            port=config.input.tcp_port,
            timeout=config.input.timeout_s,
        )
        device = Elm327Device(
            timeout=config.input.timeout_s,
            transport=transport,
        )
    elif config.input.transport == "serial":
        device = Elm327Device(
            port=config.input.port,
            baud=config.input.baud,
            timeout=config.input.timeout_s,
        )
    else:
        raise ValueError(f"Unsupported automotive transport: {config.input.transport}")

    adapter = Elm327ObdAdapter(device)
    return Obd2Manager(
        adapter,
        slow_poll_interval_seconds=config.input.slow_poll_interval_s,
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
    if config.input.source == "device":
        print(f"  device:            {config.input.device}")
        print(f"  transport:         {config.input.transport}")
        if config.input.transport == "serial":
            print(f"  serial port:       {config.input.port}")
            print(f"  baud:              {config.input.baud}")
        else:
            print(f"  TCP endpoint:      {config.input.host}:{config.input.tcp_port}")
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
