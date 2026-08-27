# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from apps.common.lighting_runtime_factory import create_lighting_controller
from controllers.lighting import LedDmxController
from hardware_io.bluetooth import BleGattState


def _prepare_transport(transport_type: Mock) -> None:
    transport = transport_type.return_value
    transport.current_state.return_value = BleGattState()
    transport.connect = AsyncMock()
    transport.disconnect = AsyncMock()
    transport.write = AsyncMock()


@patch("apps.common.lighting_runtime_factory.BleakGattTransport")
def test_composes_transport_without_a_fixed_address(transport_type: Mock) -> None:
    _prepare_transport(transport_type)

    controller = create_lighting_controller(project_root=Path.cwd())
    try:
        assert isinstance(controller, LedDmxController)
        assert transport_type.call_args.kwargs["address"] is None
    finally:
        controller.close()


@patch("apps.common.lighting_runtime_factory.BleakGattTransport")
def test_passes_an_explicit_address_to_transport(transport_type: Mock) -> None:
    _prepare_transport(transport_type)
    controller = create_lighting_controller(
        project_root=Path.cwd(),
        address="AA:BB:CC:DD:EE:FF",
    )
    try:
        assert transport_type.call_args.kwargs["address"] == "AA:BB:CC:DD:EE:FF"
    finally:
        controller.close()
