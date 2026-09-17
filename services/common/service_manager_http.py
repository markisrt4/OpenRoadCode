# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime-aware HTTP entry point for OpenRoadCode service management."""

from __future__ import annotations

from services.common.service_manager_runtime import detect_service_manager_runtime


def main() -> int:
    """Run the service-manager HTTP server appropriate for this host."""

    runtime = detect_service_manager_runtime()
    if runtime == "termux":
        from services.termux.service_manager_http import main as platform_main
    else:
        from services.linux.systemd_service_manager_http import main as platform_main
    return platform_main()


if __name__ == "__main__":
    raise SystemExit(main())
