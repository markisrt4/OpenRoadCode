# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode automotive telemetry service."""

from __future__ import annotations

import argparse
from pathlib import Path

from config.service_runtime_config import AutomotiveServiceRuntimeConfig, ServiceRuntimeConfigParser
from controllers.automotive.composite_vehicle_state_source import CompositeVehicleStateSource
from controllers.automotive.gear_estimator import GearEstimator
from controllers.automotive.navigation_motion_vehicle_state_source import NavigationMotionVehicleStateSource
from controllers.automotive.obd2.elm327_obd_adapter import Elm327ObdAdapter
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from controllers.automotive.simulated_vehicle_state_source import SimulatedVehicleStateSource
from hardware_io.automotive.elm327.elm327_tcp_device import Elm327TcpDevice
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter
from services.automotive.automotive_runtime import AutomotiveRuntime
from services.automotive.automotive_telemetry_profile_runtime import AutomotiveTelemetryProfileRuntime

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "config" / "runtime.toml"
DEFAULT_GEAR_PROFILE = Path(__file__).resolve().parents[2] / "vehicle_gears.learned.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish automotive telemetry.")
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument(
        "--configured-source",
        action="store_true",
        help=(
            "deprecated compatibility flag; configured engine telemetry is "
            "always composed with navigation ground speed"
        ),
    )
    parser.add_argument(
        "--navigation-motion",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--gear-profile",
        type=Path,
        default=DEFAULT_GEAR_PROFILE,
        help="learned RPM/speed gear profile; absent file disables gear estimation",
    )
    return parser.parse_args()


def build_source(config: AutomotiveServiceRuntimeConfig):
    """Build the configured complete vehicle-state source."""
    if config.input.source == "simulation":
        return SimulatedVehicleStateSource()
    if config.input.source == "obd_simulation":
        return Obd2Manager(SimulatedObd2Adapter(auto_advance=True))
    if config.input.device != "elm327":
        raise ValueError(f"Unsupported automotive device: {config.input.device}")

    if config.input.transport == "tcp":
        device = Elm327TcpDevice(
            host=config.input.host,
            port=config.input.tcp_port,
            timeout=config.input.timeout_s,
        )
    else:
        from hardware_io.automotive.elm327.elm327_device import Elm327Device

        device = Elm327Device(
            port=config.input.port,
            baud=config.input.baud,
            timeout=config.input.timeout_s,
        )
    adapter = Elm327ObdAdapter(device)
    return Obd2Manager(adapter)


def _load_gear_estimator(path: Path) -> GearEstimator | None:
    if not path.is_file():
        return None
    return GearEstimator.from_toml(path)


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

    if config.input.source in {"device", "obd_simulation"}:
        engine_source = build_source(config)
        motion_source = NavigationMotionVehicleStateSource(
            ZeroMqSubscriber(system.messaging.subscriber_endpoint)
        )
        source = CompositeVehicleStateSource(engine_source, motion_source)
        source_description = (
            "configured-engine + navigation-motion"
            if config.input.source == "device"
            else "simulated-obd-engine + navigation-motion"
        )
        rate_hz = config.input.request_rate_hz
    else:
        source = build_source(config)
        source_description = config.input.source
        rate_hz = config.rate_hz

    gear_estimator = _load_gear_estimator(args.gear_profile)
    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)
    runtime = AutomotiveRuntime(
        source,
        publisher,
        publish_source=config.publish.source,
        rate_hz=rate_hz,
        gear_estimator=gear_estimator,
    )
    profile_runtime = AutomotiveTelemetryProfileRuntime(
        ZeroMqSubscriber(system.messaging.subscriber_endpoint),
        source,
    )
    print("OpenRoadCode automotive service")
    print(f"  input source:      {source_description}")
    if config.input.source in {"device", "obd_simulation"}:
        print(f"  motion endpoint:   {system.messaging.subscriber_endpoint}")
    if config.input.source == "device":
        print(f"  device:            {config.input.device}")
        print(f"  transport:         {config.input.transport}")
        if config.input.transport == "tcp":
            print(f"  TCP endpoint:      {config.input.host}:{config.input.tcp_port}")
        else:
            print(f"  serial port:       {config.input.port}")
            print(f"  baud:              {config.input.baud}")
    elif config.input.source == "obd_simulation":
        print("  device:            simulated ELM327 / ECU")
    print(f"  telemetry ingress: {system.messaging.publisher_endpoint}")
    print(f"  service cadence:   {rate_hz:g} Hz")
    if config.input.source in {"device", "obd_simulation"}:
        print(f"  OBD request budget:{config.input.request_rate_hz:g} req/s")
        print("  road speed:        navigation ground motion")
    print(f"  publish source:    {config.publish.source}")
    print(
        f"  gear estimation:  {args.gear_profile}"
        if gear_estimator is not None
        else "  gear estimation:  disabled (no learned profile)"
    )
    print("Ctrl+C to stop")
    profile_runtime.start()
    try:
        runtime.run()
    except KeyboardInterrupt:
        pass
    finally:
        profile_runtime.close()
        runtime.close()
        publisher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
