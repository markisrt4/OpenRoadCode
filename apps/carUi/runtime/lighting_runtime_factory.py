# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from controllers.lighting import (
    DummyLightingController,
    LightingControllerIf,
    UnconfiguredControllerStub,
)
from controllers.lighting.adapters.leddmx_controller import LedDmxController
from controllers.lighting.parsers.leddmx_config_parser import load_leddmx_config
from hardware_io.bluetooth.bleak_gatt_transport import (
    BleakGattTransport,
    BleakUnavailableError,
)


def create_lighting_controller(
    *,
    project_root: Path,
    backend: str = "leddmx",
    address: str | None = None,
) -> LightingControllerIf:
    """Compose the selected lighting backend over its hardware transport."""

    normalized_backend = backend.strip().lower()
    if normalized_backend == "dummy":
        return DummyLightingController()
    if normalized_backend == "disabled":
        return UnconfiguredControllerStub("Lighting is disabled")
    if normalized_backend != "leddmx":
        raise ValueError(f"Unknown lighting backend: {backend}")

    config = load_leddmx_config(project_root=project_root)

    try:
        transport = BleakGattTransport(
            address=address,
            characteristic_uuid=config.characteristic_uuid,
            excluded_service_uuids=config.excluded_service_uuids,
            excluded_name_fragments=config.excluded_name_fragments,
            write_with_response=config.write_with_response,
            command_delay_seconds=config.command_delay_seconds,
            reconnect_delay_seconds=config.reconnect_delay_seconds,
            scan_timeout_seconds=config.scan_timeout_seconds,
            connect_timeout_seconds=config.candidate_connect_timeout_seconds,
        )
    except BleakUnavailableError as exc:
        return UnconfiguredControllerStub(str(exc))

    return LedDmxController(transport=transport)
