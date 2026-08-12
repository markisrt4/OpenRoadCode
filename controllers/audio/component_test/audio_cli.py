#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

from controllers.audio import PipewireAudioController


def print_commands() -> None:
    print()
    print("Commands")
    print("--------")
    print("  +          Volume up")
    print("  -          Volume down")
    print("  s <level>  Set volume level")
    print("  g          Get volume level")
    print("  q          Quit")
    print()


def main() -> None:
    controller = PipewireAudioController(
        steps=20,
        step_percent=5,
    )

    print("PipeWire Audio Controller Component Test")
    print("========================================")
    print(f"Current level: {controller.get_volume_level()}")
    print_commands()

    try:
        while True:
            command = input("audio> ").strip()

            if command == "q":
                break

            if command == "+":
                level = controller.volume_up()
                print(f"Volume level: {level}")
                continue

            if command == "-":
                level = controller.volume_down()
                print(f"Volume level: {level}")
                continue

            if command == "g":
                print(
                    f"Volume level: "
                    f"{controller.get_volume_level()}"
                )
                continue

            if command.startswith("s "):
                try:
                    level = int(command.split(maxsplit=1)[1])
                except ValueError:
                    print("Volume level must be an integer.")
                    continue

                result = controller.set_volume_level(level)
                print(f"Volume level: {result}")
                continue

            print("Unknown command.")
            print_commands()

    except KeyboardInterrupt:
        print()

    print("Audio component test stopped.")


if __name__ == "__main__":
    main()
