#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify OpenRoadCode runtime dependencies after host installation."""

from __future__ import annotations

import argparse
import importlib
import shutil
import sys
from collections.abc import Iterable


PYTHON_IMPORTS: dict[str, tuple[str, ...]] = {
    "base": ("requests", "zmq"),
    "desktop-ui": ("tkinter", "PIL"),
    "web-ui": ("flask",),
    "input": ("evdev",),
    "gps": ("gps", "gpsd", "geocoder"),
    "streamlit": ("streamlit",),
    "bluetooth": ("bleak",),
    "automotive": ("serial",),
    "imu": ("board", "adafruit_mpu6050"),
    "environmental": ("board", "adafruit_bmp3xx"),
    "raspberry-pi": ("board", "adafruit_seesaw"),
}

COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "base": (("git",), ("curl",), ("wget",), ("sudo",), ("pgrep",)),
    "desktop-ui": (("wmctrl",), ("xprop",)),
    "browser": (("chromium", "chromium-browser", "google-chrome"),),
    "vnc": (("tigervncserver", "vncserver"),),
    "audio": (("wpctl", "pactl"),),
    "gps": (("gpsd",), ("gpspipe", "cgps")),
    "rtl-sdr": (("rtl_test",), ("SoapySDRUtil",)),
    "adsb": (("readsb",),),
    "bluetooth": (("bluetoothctl",), ("sdptool",), ("rfcomm",)),
    "automotive": (("candump",),),
    "sdrpp": (("sdrpp",),),
    "raspberry-pi": (("i2cdetect",),),
    "imu": (("i2cdetect",),),
    "environmental": (("i2cdetect",),),
}

DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "vnc": ("desktop-ui",),
    "spotify": ("audio",),
    "adsb": ("rtl-sdr", "browser"),
    "sdrpp": ("rtl-sdr", "desktop-ui", "audio"),
}


def expand_features(features: Iterable[str]) -> list[str]:
    expanded: list[str] = []

    def add(feature: str) -> None:
        for dependency in DEPENDENCIES.get(feature, ()):
            add(dependency)
        if feature not in expanded:
            expanded.append(feature)

    for feature in features:
        add(feature)
    return expanded


def check_import(module: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module)
    except Exception as exc:  # Dependency probes should report, not crash.
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def check_command(alternatives: tuple[str, ...]) -> tuple[bool, str]:
    for command in alternatives:
        path = shutil.which(command)
        if path:
            return True, path
    return False, " or ".join(alternatives)


def status(ok: bool, label: str, detail: str = "") -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "features",
        nargs="+",
        help="Installed features to verify (for example: base web-ui gps)",
    )
    args = parser.parse_args()

    features = expand_features(args.features)
    failures = 0

    print("OpenRoadCode installation verification")
    print(f"Features: {', '.join(features)}")

    print("\nPython dependencies:")
    seen_imports: set[str] = set()
    for feature in features:
        for module in PYTHON_IMPORTS.get(feature, ()):
            if module in seen_imports:
                continue
            seen_imports.add(module)
            ok, detail = check_import(module)
            status(ok, module, detail if not ok else "")
            failures += not ok

    print("\nSystem dependencies:")
    seen_commands: set[tuple[str, ...]] = set()
    for feature in features:
        for alternatives in COMMANDS.get(feature, ()):
            if alternatives in seen_commands:
                continue
            seen_commands.add(alternatives)
            ok, detail = check_command(alternatives)
            status(ok, " / ".join(alternatives), detail if not ok else "")
            failures += not ok

    print()
    if failures:
        print(f"Verification FAILED: {failures} dependency check(s) failed.")
        return 1

    print("Verification PASSED: all selected dependency checks succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
