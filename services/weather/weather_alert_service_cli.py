# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode NWS weather alert producer."""

from __future__ import annotations

import argparse
from pathlib import Path

from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.weather import NwsWeatherAlertProvider
from messaging.contracts.weather import WeatherAlertPublisher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from services.weather.weather_alert_runtime import WeatherAlertRuntime

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "config" / "runtime.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish active NWS weather alerts.")
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--poll-seconds", type=float, default=60.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()

    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)
    subscriber = ZeroMqSubscriber(system.messaging.subscriber_endpoint)
    runtime = WeatherAlertRuntime(
        NwsWeatherAlertProvider(),
        WeatherAlertPublisher(publisher),
        subscriber,
        poll_interval_seconds=args.poll_seconds,
    )

    print("OpenRoadCode weather alert service")
    print("  provider:           NWS")
    print(f"  position ingress:   {system.messaging.subscriber_endpoint}")
    print(f"  alert ingress:      {system.messaging.publisher_endpoint}")
    print(f"  poll interval:      {args.poll_seconds:g} s")
    print("  location:           navigation position stream")
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
