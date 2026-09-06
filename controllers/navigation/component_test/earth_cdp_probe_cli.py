# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe the live Google Earth page through Chromium DevTools."""

from __future__ import annotations

import argparse

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_cdp_camera_controller import EarthCdpCameraController


def _print_trace(controller: EarthCdpCameraController) -> None:
    calls = controller.read_command_trace()
    print(f"captured calls: {len(calls)}")
    for index, call in enumerate(calls, 1):
        print(f"  call {index}:")
        args = call.get("args")
        if not isinstance(args, list):
            continue
        for arg_index, arg in enumerate(args, 1):
            if not isinstance(arg, dict):
                continue
            print(
                f"    arg {arg_index}: type={arg.get('type')} "
                f"constructor={arg.get('constructorName')} "
                f"length={arg.get('length')} byteLength={arg.get('byteLength')}"
            )
            keys = arg.get("keys")
            if isinstance(keys, list) and keys:
                print(f"      keys: {', '.join(str(key) for key in keys)}")
            preview = arg.get("preview")
            if preview:
                print(f"      preview: {preview}")


def _probe_geolocation(latitude: float, longitude: float, accuracy_m: float) -> None:
    client = ChromiumDevToolsClient(port=9223)
    client.set_geolocation_override(latitude, longitude, accuracy_m=accuracy_m)
    observed = client.evaluate_earth(
        """(() => new Promise(resolve => {
            if (!navigator.geolocation) {
                resolve({ok: false, error: 'navigator.geolocation unavailable'});
                return;
            }
            navigator.geolocation.getCurrentPosition(
                position => resolve({
                    ok: true,
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }),
                error => resolve({ok: false, error: error.message, code: error.code}),
                {enableHighAccuracy: true, timeout: 5000, maximumAge: 0}
            );
        }))()"""
    )
    print(f"CDP geolocation override set: {latitude:.7f}, {longitude:.7f} accuracy={accuracy_m:g}m")
    print(f"Earth page navigator.geolocation reports: {observed}")
    print("Now use Google Earth's normal My Location control.")
    print("If Earth flies to the injected coordinate, the absolute-position path works.")
    print("The override remains active until Earth/Chromium exits or --clear-geolocation is run.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-commands",
        action="store_true",
        help="passively trace ReceiveViewModelCommand while you manipulate Earth",
    )
    parser.add_argument(
        "--geolocation",
        nargs=2,
        type=float,
        metavar=("LAT", "LON"),
        help="override Chromium geolocation for Earth and verify navigator.geolocation",
    )
    parser.add_argument(
        "--accuracy-m",
        type=float,
        default=5.0,
        help="accuracy reported with --geolocation (default: 5 meters)",
    )
    parser.add_argument(
        "--clear-geolocation",
        action="store_true",
        help="clear the Chromium geolocation override for Earth",
    )
    args = parser.parse_args()

    controller = EarthCdpCameraController()
    if not controller.available():
        raise SystemExit("Google Earth DevTools target is not available")

    if args.clear_geolocation:
        ChromiumDevToolsClient(port=9223).clear_geolocation_override()
        print("Google Earth geolocation override cleared.")
        return

    if args.geolocation is not None:
        latitude, longitude = args.geolocation
        _probe_geolocation(latitude, longitude, args.accuracy_m)
        return

    if args.trace_commands:
        if not controller.install_command_trace():
            raise SystemExit("ReceiveViewModelCommand is not available")
        controller.clear_command_trace()
        print("Tracing ReceiveViewModelCommand.")
        print("Move/rotate/zoom Google Earth now, then press Enter here.")
        input()
        _print_trace(controller)
        return

    probe = controller.probe_runtime()
    print(f"title: {probe.title}")
    print(f"ready: {probe.ready_state}")
    print(f"canvas count: {probe.canvas_count}")
    print(f"url: {probe.url}")

    inspection = controller.inspect_runtime()
    print(f"earthWasmStarted: {inspection.earth_wasm_started}")
    print(f"Module present: {inspection.module_present}")
    print(
        "canvas: "
        f"{inspection.canvas_width}x{inspection.canvas_height} backing, "
        f"{inspection.canvas_client_width}x{inspection.canvas_client_height} client"
    )
    print("Module keys:")
    for key in inspection.module_keys:
        print(f"  {key}")

    print("targeted globals:")
    for item in inspection.globals:
        constructor = f" / {item.constructor_name}" if item.constructor_name else ""
        print(f"  {item.name}: {item.value_type}{constructor}")
        if item.keys:
            print(f"    keys: {', '.join(item.keys)}")

    print("selected Module hooks:")
    for hook in controller.inspect_module_hooks():
        constructor = f" / {hook.constructor_name}" if hook.constructor_name else ""
        arity = f", arity={hook.arity}" if hook.arity is not None else ""
        embind = f", embind_args={hook.embind_arg_count}" if hook.embind_arg_count is not None else ""
        print(f"  {hook.name}: {hook.value_type}{constructor}{arity}{embind}")
        if hook.keys:
            print(f"    keys: {', '.join(hook.keys)}")
        if hook.source_preview:
            print(f"    source: {hook.source_preview}")


if __name__ == "__main__":
    main()
