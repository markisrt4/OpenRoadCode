from __future__ import annotations

from pathlib import Path

from controllers.lighting import (
    LightingControllerIf,
    UnconfiguredControllerStub,
)
from controllers.lighting.adapters.leddmx_bluetooth_controller import (
    BleakUnavailableError,
    LedDmxBluetoothController,
)
from controllers.lighting.parsers.leddmx_config_parser import (
    load_leddmx_config,
)


def create_lighting_controller(
    *,
    project_root: Path,
    address: str | None = None,
) -> LightingControllerIf:
    """Create Bluetooth lighting, or a safe stub if BLE support is absent."""

    config = load_leddmx_config(project_root=project_root)

    try:
        return LedDmxBluetoothController(
            address=address,
            config=config,
        )
    except BleakUnavailableError as exc:
        return UnconfiguredControllerStub(str(exc))
