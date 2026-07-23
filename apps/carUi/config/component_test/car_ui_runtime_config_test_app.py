from __future__ import annotations

import argparse
from pathlib import Path
import sys

from apps.carUi.config.car_ui_runtime_config_parser import (
    CarUiRuntimeConfig,
    CarUiRuntimeConfigError,
    CarUiRuntimeConfigParser,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Car UI runtime TOML configuration and display the "
            "resolved runtime composition."
        )
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to the Car UI runtime TOML file.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=(
            "Project root used to resolve config/radio JSON files. "
            "Defaults to the repository root inferred by the parser."
        ),
    )
    parser.add_argument(
        "--skip-radio-file-check",
        action="store_true",
        help=(
            "Validate TOML structure without requiring referenced radio JSON "
            "files to exist."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the final validation result.",
    )
    return parser


def format_config_summary(config: CarUiRuntimeConfig) -> str:
    lines = [
        "Runtime:",
        f"  Remote display: {config.runtime.remote_display}",
        "",
        "RigCTL:",
        f"  Host: {config.rigctl.host}",
        f"  Port: {config.rigctl.port}",
        "",
        "Rotary encoders:",
        f"  Devices: {len(config.input.rotary_encoders.devices)}",
        f"  Volume index: {config.input.rotary_encoders.volume_index}",
        "",
        "Barometric sensor:",
        (
            "  Driver: "
            f"{config.environmental.barometric_sensor.driver}"
        ),
        (
            "  I2C address: "
            f"{config.environmental.barometric_sensor.address:#04x}"
        ),
        "",
        f"Radio stacks: {len(config.radios)} configured",
    ]

    for radio in config.radios:
        state = "enabled" if radio.enabled else "disabled"
        launcher = radio.launcher or "none"
        lines.extend(
            [
                f"  - {radio.key} [{state}]",
                f"      Config:   {radio.config_path}",
                f"      Backend:  {radio.backend}",
                f"      Launcher: {launcher}",
            ]
        )

    lines.extend(
        [
            "",
            "Auxiliary:",
            (
                "  ADS-B: enabled"
                if config.auxiliary.adsb.enabled
                else "  ADS-B: disabled"
            ),
            f"    URL: {config.auxiliary.adsb.url}",
            (
                "  Weather dashboard: enabled"
                if config.auxiliary.weather_dashboard.enabled
                else "  Weather dashboard: disabled"
            ),
        ]
    )

    return "\n".join(lines)


def validate_config(
    config_path: Path,
    *,
    project_root: Path | None = None,
    require_radio_files: bool = True,
) -> CarUiRuntimeConfig:
    parser = CarUiRuntimeConfigParser(
        config_path=config_path,
        project_root=project_root,
        require_radio_files=require_radio_files,
    )
    return parser.load()


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)

    try:
        config = validate_config(
            args.config,
            project_root=args.project_root,
            require_radio_files=not args.skip_radio_file_check,
        )
    except CarUiRuntimeConfigError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"INVALID: unable to read configuration: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(format_config_summary(config))
        print()

    print(f"VALID: {args.config.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
