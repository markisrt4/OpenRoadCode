"""Command-line router backend component test."""

from __future__ import annotations

import argparse
import sys

from networking.router.backends import (
    NetworkManagerRouter,
    NetworkManagerRouterError,
)
from networking.router.router_status import RouterStatus


DEFAULT_CONNECTION_NAME = "openroad-bench-hotspot"
DEFAULT_WAN_INTERFACE = "ens33"
DEFAULT_LAN_INTERFACE = "wlx7419f81758ca"


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Control an existing NetworkManager router "
            "or hotspot connection."
        )
    )

    parser.add_argument(
        "command",
        choices=(
            "status",
            "start",
            "stop",
            "restart",
        ),
        help="Router operation to perform.",
    )

    parser.add_argument(
        "--connection",
        default=DEFAULT_CONNECTION_NAME,
        help=(
            "NetworkManager connection name. "
            f"Default: {DEFAULT_CONNECTION_NAME}"
        ),
    )

    parser.add_argument(
        "--wan-interface",
        default=DEFAULT_WAN_INTERFACE,
        help=(
            "WAN network interface. "
            f"Default: {DEFAULT_WAN_INTERFACE}"
        ),
    )

    parser.add_argument(
        "--lan-interface",
        default=DEFAULT_LAN_INTERFACE,
        help=(
            "LAN or hotspot network interface. "
            f"Default: {DEFAULT_LAN_INTERFACE}"
        ),
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
    """Run the router control CLI."""

    parser = _create_parser()
    arguments = parser.parse_args()

    router = NetworkManagerRouter(
        connection_name=arguments.connection,
        wan_interface=arguments.wan_interface,
        lan_interface=arguments.lan_interface,
    )

    try:
        if arguments.command == "start":
            router.start_router()
            print(
                f"Router connection started: "
                f"{router.connection_name}"
            )

        elif arguments.command == "stop":
            router.stop_router()
            print(
                f"Router connection stopped: "
                f"{router.connection_name}"
            )

        elif arguments.command == "restart":
            router.restart_router()
            print(
                f"Router connection restarted: "
                f"{router.connection_name}"
            )

        status = router.get_status()
        _print_status(status)

    except NetworkManagerRouterError as exc:
        print(f"Router operation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
