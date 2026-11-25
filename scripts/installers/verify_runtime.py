#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify OpenRoadCode services and configured runtime resources."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

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


def systemd_enabled(service: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["systemctl", "is-enabled", service],
        capture_output=True, text=True, check=False, timeout=5,
    )
    state = result.stdout.strip()
    return state == "enabled", state or result.stderr.strip()


def routing_ready(root: Path, region: str) -> tuple[bool, str]:
    """Probe the local routing engine with a catalogued regional route."""
    try:
        catalog_path = Path(__file__).resolve().parents[1] / "runtime/navigation-data-catalog.json"
        catalog = json.loads(catalog_path.read_text())
        route = catalog["regions"][region]["smoke_route"]
        config = json.loads((root / "valhalla/valhalla.json").read_text())
        listen = config["httpd"]["service"]["listen"]
        port = int(listen.rsplit(":", 1)[1])
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 30
        while True:
            ok, detail = http_endpoint(f"{base}/status", timeout_s=1)
            if ok:
                break
            if time.monotonic() >= deadline:
                return False, detail
            time.sleep(0.5)
        query = urllib.parse.urlencode({"json": json.dumps(route)})
        with urllib.request.urlopen(f"{base}/route?{query}", timeout=15) as response:
            trip = json.load(response)["trip"]
        summary = trip["summary"]
        if summary["length"] <= 0 or summary["time"] <= 0:
            return False, "empty route summary"
        if not trip["legs"] or not all(leg.get("shape") for leg in trip["legs"]):
            return False, "missing route geometry"
        return True, f"{summary['length']} {trip.get('units', 'km')}, {summary['time']} s"
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        return False, str(exc)


def radio_service_ready() -> tuple[bool, str]:
    """Check the user service, its listeners, and its REST health."""
    try:
        state = subprocess.check_output(
            ["systemctl", "--user", "is-active", "libsdrforge.service"],
            text=True,
            timeout=5,
        ).strip()
        if state != "active":
            return False, f"service state: {state}"
        pid = subprocess.check_output(
            ["systemctl", "--user", "show", "libsdrforge.service", "-p", "MainPID", "--value"],
            text=True,
            timeout=5,
        ).strip()
        if not pid.isdigit() or int(pid) == 0:
            return False, "no systemd MainPID"
        for port in (5570, 5571, 4532):
            listeners = subprocess.check_output(
                ["ss", "-H", "-lntp", f"sport = :{port}"], text=True, timeout=5
            )
            if set(re.findall(r"pid=(\d+)", listeners)) != {pid}:
                return False, f"port {port} is not owned by PID {pid}"
        with urllib.request.urlopen("http://127.0.0.1:5570/v1/health", timeout=2) as response:
            health = json.load(response)
            if not isinstance(health, dict) or health.get("status") != "ok":
                return False, "REST health is not ok"
        return True, f"systemd PID {pid} owns REST, ZMQ and rigctl"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return False, str(exc)


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
        "--radio-service",
        action="store_true",
        help="Require the native radio user service and message broker",
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
    parser.add_argument("--navigation-service", action="store_true")
    parser.add_argument("--navigation-data-root", type=Path)
    parser.add_argument("--navigation-region")
    args = parser.parse_args()
    if args.navigation_region and args.navigation_data_root is None:
        parser.error("--navigation-region requires --navigation-data-root")

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

    if args.navigation_service and not args.telemetry_services:
        for service in TELEMETRY_SERVICES[:2]:
            ok, detail = systemd_active(service)
            report("PASS" if ok else "FAIL", service, detail)
            failures += not ok

    if args.navigation_data_root is not None:
        for relative in (
            "build-manifest.json",
            "maps/vector/openroadcode.mbtiles",
            "maps/search/openroadcode-search.sqlite",
            "valhalla/valhalla.json",
        ):
            path = args.navigation_data_root / relative
            ok = path.is_file() and path.stat().st_size > 0
            report("PASS" if ok else "FAIL", str(path))
            failures += not ok
        ok, detail = systemd_active("valhalla.service")
        report("PASS" if ok else "FAIL", "valhalla.service", detail)
        failures += not ok

    if args.navigation_service or args.telemetry_services:
        for service in TELEMETRY_SERVICES[:2]:
            ok, detail = systemd_enabled(service)
            report("PASS" if ok else "FAIL", f"{service} boot persistence", detail)
            failures += not ok
    if args.navigation_data_root is not None:
        ok, detail = systemd_enabled("valhalla.service")
        report("PASS" if ok else "FAIL", "Valhalla boot persistence", detail)
        failures += not ok
        if args.navigation_region:
            ok, detail = routing_ready(args.navigation_data_root, args.navigation_region)
            report("PASS" if ok else "FAIL", "Offline routing", detail)
            failures += not ok

    if args.radio_service:
        if not (args.telemetry_services or args.navigation_service):
            ok, detail = systemd_active(TELEMETRY_SERVICES[0])
            report("PASS" if ok else "FAIL", TELEMETRY_SERVICES[0], detail)
            failures += not ok
        ok, detail = radio_service_ready()
        report("PASS" if ok else "FAIL", "libsdrforge.service", detail)
        failures += not ok

    if args.gpsd_service:
        service_ok, service_detail = systemd_active("gpsd.service")
        socket_ok, socket_detail = systemd_active("gpsd.socket")
        ok = service_ok or socket_ok
        detail = f"service={service_detail}, socket={socket_detail}"
        report("PASS" if ok else "FAIL", "gpsd", detail)
        failures += not ok

    print("\nMessaging endpoints:")
    if args.telemetry_services or args.radio_service or args.navigation_service:
        endpoint_paths = (
            ("publisher ingress", nested(config, "messaging", "publisher_endpoint")),
            ("subscriber egress", nested(config, "messaging", "subscriber_endpoint")),
            ("navigation commands", nested(config, "services", "navigation", "command_endpoint")),
        )
        if not (args.telemetry_services or args.navigation_service):
            endpoint_paths = endpoint_paths[:2]
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
