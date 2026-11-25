# SPDX-License-Identifier: MIT
"""Report observed OpenRoadCode installation state without modifying it."""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import os
import sys
from pathlib import Path

from common.xdg_paths import openroadcode_config_dir, openroadcode_data_dir
from scripts.installers.verify_installation import COMMANDS, PYTHON_IMPORTS, check_command
from scripts.installers.verify_runtime import TELEMETRY_SERVICES, command_output

SYSTEM_UNITS = (
    *TELEMETRY_SERVICES,
    "valhalla.service",
    "gpsd.socket",
    "gpsd.service",
    "lighttpd.service",
    "readsb.service",
)
USER_UNITS = (
    "libsdrforge.service",
    "libsdrforge-weather.service",
    "openroadcode-readsb@.service",
    "carui-vnc.service",
    "openroadcode-calendar-sync.service",
)


def show_units(units: tuple[str, ...], *, user: bool = False) -> None:
    """Show installation, boot and runtime state as reported by systemd."""
    scope = ("--user",) if user else ()
    for unit in units:
        output = command_output(
            "systemctl",
            *scope,
            "show",
            "-p",
            "LoadState",
            "-p",
            "UnitFileState",
            "-p",
            "ActiveState",
            unit,
        )
        fields = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
        print(unit)
        load = fields.get("LoadState")
        if load == "not-found":
            print("  Missing")
        elif load is None:
            # Unavailable manager or an unsupported query, for example a template.
            enabled = command_output("systemctl", *scope, "is-enabled", unit)
            if enabled in {
                "static",
                "disabled",
                "enabled",
                "masked",
                "indirect",
                "enabled-runtime",
            }:
                print(f"  Unit file: {enabled} | runtime state unavailable")
            else:
                print(f"  Unknown: {output or enabled}")
        else:
            print(
                f"  {load} | boot: {fields.get('UnitFileState') or 'not applicable'}"
                f" | now: {fields.get('ActiveState', 'unknown')}"
            )


def show_services() -> None:
    """Show system and user services."""
    print("\nSystem units:")
    show_units(SYSTEM_UNITS)
    print("\nUser units:")
    show_units(USER_UNITS, user=True)
    readsb_instances = command_output(
        "systemctl",
        "--user",
        "list-units",
        "--all",
        "--plain",
        "--no-legend",
        "openroadcode-readsb@*.service",
    )
    if readsb_instances != "exit 0":
        print(f"\nManaged readsb instances:\n{readsb_instances}")
    linger = command_output("loginctl", "show-user", str(os.getuid()), "-p", "Linger", "--value")
    print(f"User manager linger: {linger}")


def show_software(catalog: set[str]) -> None:
    """Show package records, modules and commands."""
    print("\nInstalled Debian packages from the installer catalog:")
    package_records = command_output("dpkg-query", "-W", "-f=${Package}\t${Status}\t${Version}\\n")
    records = [line.split("\t", 2) for line in package_records.splitlines()]
    installed = [
        f"  {name} {version}"
        for name, status, version in (record for record in records if len(record) == 3)
        if name in catalog and status == "install ok installed"
    ]
    print("\n".join(sorted(installed)) or "  No matching installed packages reported.")
    if not any(len(record) == 3 for record in records):
        print(f"  Package database unavailable: {package_records}")

    print("\nPython modules discoverable in the interpreter above:")
    for module in sorted({name for group in PYTHON_IMPORTS.values() for name in group}):
        state = "found" if importlib.util.find_spec(module) else "missing"
        print(f"  {module}: {state}")

    print("\nCommands:")
    for alternatives in sorted({names for group in COMMANDS.values() for names in group}):
        ok, detail = check_command(alternatives)
        print(f"  {' / '.join(alternatives)}: {detail if ok else 'missing'}")


def main() -> None:
    """Inspect known services, package records and installer artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hide-software", action="store_true")
    parser.add_argument("--hide-services", action="store_true")
    parser.add_argument("packages", nargs="*")
    args = parser.parse_args()
    print("OpenRoadCode installation inventory")
    print(f"Python: {sys.executable}")
    print(f"User: {getpass.getuser()}")
    if not args.hide_services:
        show_services()
    if not args.hide_software:
        show_software(set(args.packages))

    print("\nConfiguration and model files:")
    for label, path in (
        ("Host profile", openroadcode_config_dir("host.toml")),
        ("Managed RF credentials", openroadcode_config_dir("rf-acquisition.env")),
        ("RF assignments", openroadcode_config_dir("rf-receivers.json")),
        ("Vision model", openroadcode_data_dir("vision", "models", "yolo11n.pt")),
        (
            "Valhalla configuration",
            Path(os.environ.get("DATA_ROOT", "/srv/openroadcode")) / "valhalla/valhalla.json",
        ),
    ):
        print(f"  {label}: {'present' if path.is_file() else 'missing'}")


if __name__ == "__main__":
    main()
