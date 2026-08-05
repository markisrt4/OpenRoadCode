#!/usr/bin/env python3
"""Command-line client for exercising a rigctl or SDR++ rigctl server."""

from __future__ import annotations

import argparse
import socket
import sys

from protocols.rigctl import RigctlClient
from protocols.rigctl.emulator.example_rigctl_server import ExampleRigctlServer


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4532)
    parser.add_argument("--timeout", type=float, default=1.0)

    subparsers = parser.add_subparsers(dest="action")

    subparsers.add_parser("get-frequency")

    frequency = subparsers.add_parser("set-frequency")
    frequency.add_argument("hz", type=int)

    mode = subparsers.add_parser("set-mode")
    mode.add_argument("mode")
    mode.add_argument("bandwidth", type=int)

    subparsers.add_parser("start")
    subparsers.add_parser("stop")
    subparsers.add_parser("strength")
    subparsers.add_parser("snr")
    subparsers.add_parser("rds")

    raw = subparsers.add_parser("raw")
    raw.add_argument("command", nargs="+")

    subparsers.add_parser("interactive")
    return parser


def execute_action(client: RigctlClient, args: argparse.Namespace) -> str:
    actions = {
        "get-frequency": client.get_frequency,
        "start": client.start,
        "stop": client.stop,
        "strength": client.get_signal_strength,
        "snr": client.get_snr,
        "rds": client.get_rds,
    }

    if args.action in actions:
        return actions[args.action]()
    if args.action == "set-frequency":
        return client.set_frequency(args.hz)
    if args.action == "set-mode":
        return client.set_mode(args.mode, args.bandwidth)
    if args.action == "raw":
        return client.send(" ".join(args.command))
    raise ValueError(f"unsupported action: {args.action}")


def run_interactive(client: RigctlClient) -> int:
    print("Enter raw rigctl commands. Type 'quit' or press Ctrl-D to exit.")
    while True:
        try:
            command = input("rigctl> ").strip()
        except EOFError:
            print()
            return 0

        if command.lower() in {"quit", "exit"}:
            return 0
        if not command:
            continue

        try:
            response = client.send(command)
            print(response if response else "<no response>")
        except OSError as exc:
            print(f"connection error: {exc}", file=sys.stderr)


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    if args.action is None:
        parser.print_help()
        return 2

    client = RigctlClient(args.host, args.port, args.timeout)

    if args.action == "interactive":
        return run_interactive(client)

    try:
        response = execute_action(client, args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(response if response else "<no response>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
