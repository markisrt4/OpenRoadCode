# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Regression tests for SDRForge acquisition evidence."""

from unittest.mock import Mock

import pytest

from hardware_io.rf.receiver_discovery_if import ReceiverDevice
from hardware_io.rf.sdrforge_acquisition_adapter import SdrforgeAcquisitionAdapter


def test_start_requires_released_receiver() -> None:
    adapter = SdrforgeAcquisitionAdapter("test")
    adapter._request = Mock(return_value={"hardware_released": False})
    device = ReceiverDevice("0bda", "2838", "00000001", "1-1")
    with pytest.raises(RuntimeError, match="cannot confirm receiver release"):
        adapter.start(device)
    adapter._request.assert_called_once_with("/v1/receiver")


def _acquire_receiver() -> SdrforgeAcquisitionAdapter:
    adapter = SdrforgeAcquisitionAdapter("test")
    adapter._request = Mock(
        side_effect=[
            {"running": False, "starting": False, "hardware_released": True},
            {},
            {},
            {"running": True, "starting": False},
            {"device_serial": "00000001"},
        ]
    )
    device = ReceiverDevice("0bda", "2838", "00000001", "1-1")
    assert adapter.start(device)
    return adapter


def test_start_confirms_serial() -> None:
    _acquire_receiver()


def test_stop_does_not_interrupt_preexisting_service_acquisition() -> None:
    adapter = SdrforgeAcquisitionAdapter("test")
    adapter._request = Mock(return_value={"running": True, "hardware_released": False})
    device = ReceiverDevice("0bda", "2838", "00000001", "1-1")
    with pytest.raises(RuntimeError, match="active or starting receiver"):
        adapter.start(device)
    adapter._request.reset_mock()
    assert not adapter.stop()
    adapter._request.assert_called_once_with("/v1/receiver")


def test_stop_requires_release_confirmation() -> None:
    adapter = _acquire_receiver()
    adapter._request = Mock(
        side_effect=[
            {},
            {"running": False, "starting": False, "hardware_released": True},
        ]
    )
    assert adapter.stop()


def test_stop_rejects_release_error() -> None:
    adapter = _acquire_receiver()
    adapter._request = Mock(side_effect=[{}, {"release_error": "close failed"}])
    assert not adapter.stop()


def test_start_diagnoses_service_without_release_evidence() -> None:
    adapter = SdrforgeAcquisitionAdapter("test")
    adapter._request = Mock(return_value={"running": False, "starting": False})
    device = ReceiverDevice("0bda", "2838", "00000001", "1-1")

    with pytest.raises(RuntimeError, match="Install the pinned SDRForge build"):
        adapter.start(device)

    adapter._request.assert_called_once_with("/v1/receiver")
