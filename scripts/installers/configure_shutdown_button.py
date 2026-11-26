#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Configure the Raspberry Pi firmware shutdown-button overlay."""

import argparse
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile

# The host installer runs this script before the project environment exists.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hardware_io.gpio import RpiGpioHeader  # noqa: E402


def shutdown_gpio(physical_pin: int) -> int:
    bcm = RpiGpioHeader.bcm_from_physical_pin(physical_pin)
    if bcm in {0, 1, 2, 3}:
        raise ValueError(
            f"Physical pin {physical_pin} is reserved for I2C or HAT identification"
        )
    return bcm


def update_config(path: Path, bcm: int) -> None:
    path = path.resolve(strict=True)
    original = path.read_text(encoding="utf-8")
    overlay = f"dtoverlay=gpio-shutdown,gpio_pin={bcm},active_low=1,gpio_pull=up"
    lines = [
        line for line in original.splitlines()
        if not re.match(r"\s*dtoverlay\s*=\s*gpio-shutdown\s*(?:,|#|$)", line)
    ]
    sections = [line.strip() for line in lines if re.match(r"\s*\[", line)]
    updated = "\n".join(lines).rstrip()
    if not sections or sections[-1] != "[all]":
        updated = f"{updated}\n\n[all]" if updated else "[all]"
    updated = f"{updated}\n{overlay}\n"
    if updated == original:
        return

    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(updated)
            temporary.close()
            temporary_path.chmod(path.stat().st_mode & 0o777)
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("physical_pin", type=int)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    try:
        bcm = shutdown_gpio(args.physical_pin)
        if args.config is None:
            print(bcm)
        else:
            update_config(args.config, bcm)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
