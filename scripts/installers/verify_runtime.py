#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify OpenRoadCode services and configured runtime resources."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.error
import urllib.request

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 fallback used by supported venvs.
    import tomli as tomllib  # type: ignore[no-redef]


TELEMETRY_SERVICES = (
    "openroadcode-message-broker.service",
    "openroadcode-navigation.service",
    "openroadcode-automotive.service",
)


def report(level: str, label: str, detail: str = "") -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"[{level}] {label}{suffix}")


def load_config(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def nested(mapping: dict[str, object], *keys: str) -> object | None:
    value: object = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def systemd_active(service: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["systemctl", "is-active", service],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    state = result.stdout.strip() or result.stderr.strip() or f"exit {result.returncode}"
    return result.returncode == 0 and state == "active", state


def tcp_endpoint(endpoint: str, timeout_s: float = 0.5) -> tuple[bool, str]:
    if not endpoint.startswith("tcp://"):
        return True, "non-TCP endpoint; skipped"
    address = endpoint.removeprefix("tcp://")
    host, separator, port_text = address.rpartition(":")
    if not separator or not host or not port_text.isdigit():
        return False, f"invalid endpoint: {endpoint}"
    try:
        with socket.create_connection((host, int(port_text)), timeout=timeout_s):
            return True, endpoint
    except OSError as exc:
        return False, str(exc)


def http_endpoint(url: str, timeout_s: float = 1.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return False, str(exc)


def device_accessible(path_text: str) -> tuple[bool, str]:
    path = Path(path_text)
    if not path.exists():
        return False, "not present"
    if not os.access(path, os.R_OK | os.W_OK):
        return False, "present but not readable/writable by current user"
    return True, "accessible"


def hardware_result(
    ok: bool,
    label: str,
    detail: str,
    *,
    strict: bool,
) -> int:
    if ok:
        report("PASS", label, detail)
        return 0
    report("FAIL" if strict else "WARN", label, detail)
    return 1 if strict else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "features",
        nargs="*",
        help="Installed features whose runtime resources should be checked",
    )
    parser.add_argument(
        "--config",
        default="config/runtime.toml",
        help="Runtime TOML path (default: config/runtime.toml)",
    )
    parser.add_argument(
        "--telemetry-services",
        action="store_true",
        help="Require the OpenRoadCode telemetry systemd services to be active",
    )
    parser.add_argument(
        "--gpsd-service",
        action="store_true",
        help="Require gpsd.service or gpsd.socket to be active",
    )
    parser.add_argument(
        "--strict-hardware",
        action="store_true",
        help="Treat missing configured hardware/resources as failures instead of warnings",
    )
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    print("OpenRoadCode runtime verification")
    print(f"Config:   {config_path}")
    print(f"Features: {', '.join(args.features) if args.features else '(none)'}")

    if not config_path.is_file():
        report("FAIL", "runtime configuration", "file not found")
        return 1

    try:
        config = load_config(config_path)
    except Exception as exc:
        report("FAIL", "runtime configuration", f"{type(exc).__name__}: {exc}")
        return 1

    failures = 0
    feature_set = set(args.features)

    print("\nServices:")
    if args.telemetry_services:
        for service in TELEMETRY_SERVICES:
            ok, detail = systemd_active(service)
            report("PASS" if ok else "FAIL", service, detail)
            failures += not ok
    else:
        report("SKIP", "OpenRoadCode telemetry services", "not requested")

    if args.gpsd_service:
        service_ok, service_detail = systemd_active("gpsd.service")
        socket_ok, socket_detail = systemd_active("gpsd.socket")
        ok = service_ok or socket_ok
        detail = f"service={service_detail}, socket={socket_detail}"
        report("PASS" if ok else "FAIL", "gpsd", detail)
        failures += not ok

    print("\nMessaging endpoints:")
    if args.telemetry_services:
        endpoint_paths = (
            ("publisher ingress", nested(config, "messaging", "publisher_endpoint")),
            ("subscriber egress", nested(config, "messaging", "subscriber_endpoint")),
            ("navigation commands", nested(config, "services", "navigation", "command_endpoint")),
        )
        for label, value in endpoint_paths:
            if not isinstance(value, str) or not value:
                report("FAIL", label, "missing endpoint in runtime config")
                failures += 1
                continue
            ok, detail = tcp_endpoint(value)
            report("PASS" if ok else "FAIL", label, detail)
            failures += not ok
    else:
        report("SKIP", "ZeroMQ TCP endpoints", "telemetry services not requested")

    print("\nConfigured resources:")
    gps_source = nested(config, "services", "navigation", "inputs", "gps", "source")
    if "gps" in feature_set and gps_source == "device":
        host = nested(config, "services", "navigation", "inputs", "gps", "host")
        port = nested(config, "services", "navigation", "inputs", "gps", "port")
        if isinstance(host, str) and isinstance(port, str) and port.isdigit():
            ok, detail = tcp_endpoint(f"tcp://{host}:{port}")
            failures += hardware_result(
                ok,
                "GPSD connection",
                detail,
                strict=args.strict_hardware,
            )
        else:
            failures += hardware_result(
                False,
                "GPSD connection",
                "invalid host/port configuration",
                strict=args.strict_hardware,
            )

    imu_source = nested(config, "services", "navigation", "inputs", "imu", "source")
    if "imu" in feature_set and imu_source == "device":
        ok, detail = device_accessible("/dev/i2c-1")
        failures += hardware_result(
            ok,
            "I2C bus /dev/i2c-1",
            detail,
            strict=args.strict_hardware,
        )

    if "environmental" in feature_set:
        ok, detail = device_accessible("/dev/i2c-1")
        failures += hardware_result(
            ok,
            "environmental I2C bus /dev/i2c-1",
            detail,
            strict=args.strict_hardware,
        )

    automotive_source = nested(config, "services", "automotive", "input", "source")
    automotive_port = nested(config, "services", "automotive", "input", "port")
    if (
        "automotive" in feature_set
        and automotive_source == "device"
        and isinstance(automotive_port, str)
    ):
        ok, detail = device_accessible(automotive_port)
        failures += hardware_result(
            ok,
            f"automotive device {automotive_port}",
            detail,
            strict=args.strict_hardware,
        )

    adsb_enabled = nested(config, "auxiliary", "adsb", "enabled")
    adsb_url = nested(config, "auxiliary", "adsb", "url")
    if "adsb" in feature_set and adsb_enabled is True and isinstance(adsb_url, str):
        ok, detail = http_endpoint(adsb_url)
        failures += hardware_result(
            ok,
            f"ADS-B dashboard {adsb_url}",
            detail,
            strict=args.strict_hardware,
        )

    if not feature_set:
        report("SKIP", "hardware/resource probes", "no features supplied")

    print()
    if failures:
        print(f"Runtime verification FAILED: {failures} required check(s) failed.")
        return 1

    print("Runtime verification PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
