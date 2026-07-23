#!/usr/bin/env python3

from __future__ import annotations

import argparse

from hardware_io.automotive.elm327 import (
    Elm327CommandError,
    Elm327ConnectionError,
    Elm327Device,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ELM327 device component test")
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--command", help="Send one command and exit, such as ATI")
    return parser.parse_args()


def print_response(command: str, raw: str, lines: tuple[str, ...]) -> None:
    print(f"\nCommand: {command}")
    print("Response:")
    for line in lines:
        print(f"  {line}")
    if not lines:
        print("  <empty>")
    print("\nRaw response:")
    print(repr(raw))


def run_interactive(device: Elm327Device) -> None:
    print("Connected. Enter an ELM327 command, or 'quit' to stop.\n")
    while True:
        try:
            command = input("elm327> ").strip()
        except EOFError:
            print()
            break
        if command.lower() in {"quit", "exit"}:
            break
        if not command:
            continue
        try:
            response = device.send_command(command)
            print_response(response.command, response.raw, response.lines)
        except Elm327CommandError as exc:
            print(f"Command error: {exc}")


def main() -> None:
    args = parse_args()
    device = Elm327Device(port=args.port, baud=args.baud)
    try:
        print(f"Connecting to ELM327 on {args.port} at {args.baud} baud...")
        device.connect()
        if args.command:
            response = device.send_command(args.command)
            print_response(response.command, response.raw, response.lines)
        else:
            run_interactive(device)
    except Elm327ConnectionError as exc:
        print(f"Connection error: {exc}")
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        device.disconnect()


if __name__ == "__main__":
    main()

