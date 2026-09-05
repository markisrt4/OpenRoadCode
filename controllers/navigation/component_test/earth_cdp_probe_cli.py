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
    print("custom elements:")
    for name in probe.custom_element_names:
        print(f"  {name}")

    print("matching globals:")
    for name in controller.inspect_globals():
        print(f"  {name}")


if __name__ == "__main__":
    main()
