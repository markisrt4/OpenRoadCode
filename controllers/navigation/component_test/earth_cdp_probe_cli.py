# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe the live Google Earth page through Chromium DevTools."""

from __future__ import annotations

from controllers.navigation.earth_cdp_camera_controller import EarthCdpCameraController


def main() -> None:
    controller = EarthCdpCameraController()
    if not controller.available():
        raise SystemExit("Google Earth DevTools target is not available")

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
        embind = (
            f", embind_args={hook.embind_arg_count}"
            if hook.embind_arg_count is not None
            else ""
        )
        print(f"  {hook.name}: {hook.value_type}{constructor}{arity}{embind}")
        if hook.keys:
            print(f"    keys: {', '.join(hook.keys)}")
        if hook.source_preview:
            print(f"    source: {hook.source_preview}")


if __name__ == "__main__":
    main()
