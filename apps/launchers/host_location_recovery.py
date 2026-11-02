# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Start the configured producer through the existing restricted supervisor."""
from services.linux.systemd_service_manager import SystemdServiceManager


def start_host_location_service() -> None:
    """Idempotently start the installed navigation unit; never restart guidance."""
    SystemdServiceManager().start('openroadcode-navigation')
