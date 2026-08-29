# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the ambient light controller."""

from __future__ import annotations

import pytest

from controllers.environmental import AmbientLightController, BufferedAmbientLightSensor


def _started_controller(illuminance_lux: float) -> AmbientLightController:
    sensor = BufferedAmbientLightSensor()
    sensor.update_illuminance_lux(illuminance_lux)
    controller = AmbientLightController(sensor)
    controller.start()
    return controller


def test_read_state_returns_illuminance_and_caches_latest_state() -> None:
    controller = _started_controller(12.5)

    state = controller.read_state()

    assert state.illuminance_lux == 12.5
    assert controller.latest_state is state


def test_read_state_requires_started_controller() -> None:
    controller = AmbientLightController(BufferedAmbientLightSensor())

    with pytest.raises(RuntimeError, match="not started"):
        controller.read_state()


@pytest.mark.parametrize("illuminance_lux", (-1.0, float("nan"), float("inf")))
def test_read_state_rejects_invalid_illuminance(illuminance_lux: float) -> None:
    controller = _started_controller(illuminance_lux)

    with pytest.raises(RuntimeError, match="invalid illuminance"):
        controller.read_state()


def test_stop_stops_controller() -> None:
    controller = _started_controller(1.0)

    controller.stop()

    assert not controller.is_started
