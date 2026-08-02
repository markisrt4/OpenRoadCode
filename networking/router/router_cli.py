"""Command-line interface for router management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from networking.router.network_manager_router import (
    NetworkManagerRouterError,
)
from networking.router.router_config import RouterConfigError
from networking.router.router_manager import (
    RouterManager,
    RouterManagerError,
)
from networking.router.router_status import RouterStatus


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "vm_bench.toml"
)


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control a configured OpenRoadCode router."
    )

    parser.add_argument(
        "command",
        choices=("status", "validate", "start", "stop", "restart"),
        help="Router operation to perform.",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Router TOML configuration. Default: {DEFAULT_CONFIG}",
    )

    return parser


def _print_status(status: RouterStatus) -> None:
    print("Router status")
    print("=============")
    print()
    print(f"State:               {status.state_text}")
    print(f"Connection:          {status.connection_name}")
    print(f"WAN interface:       {status.wan_interface}")
    print(f"LAN interface:       {status.lan_interface}")
    print(f"SSID:                {status.ssid or '-'}")
    print(
        "Internet connected: "
        f"{'yes' if status.internet_connected else 'no'}"
    )

    if status.addresses:
        print("LAN addresses:")

        for address in status.addresses:
            print(f"  - {address}")
    else:
        print("LAN addresses:       -")


def main() -> int:
    """Run the router management CLI."""

    parser = _create_parser()
    arguments = parser.parse_args()

    try:
        manager = RouterManager.from_file(arguments.config)

        if arguments.command == "validate":
            manager.validate()
            print(f"Router configuration is valid: {arguments.config}")
            return 0

        if arguments.command == "start":
            status = manager.start()
        elif arguments.command == "stop":
            status = manager.stop()
        elif arguments.command == "restart":
            status = manager.restart()
        else:
            status = manager.get_status()

        _print_status(status)

    except (
        RouterConfigError,
        RouterManagerError,
        NetworkManagerRouterError,
    ) as exc:
        print(f"Router operation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())