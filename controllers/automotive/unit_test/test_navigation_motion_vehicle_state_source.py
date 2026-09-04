# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for real navigation motion feeding partial vehicle state."""

from types import SimpleNamespace

from controllers.automotive.navigation_motion_vehicle_state_source import NavigationMotionVehicleStateSource


class _Subscriber:
    def __init__(self) -> None:
        self.topics: list[str] = []

    def subscribe(self, topic: str) -> None:
        self.topics.append(topic)

    def receive(self):
        raise RuntimeError("not used by this unit test")

    def close(self) -> None:
        pass


def test_navigation_motion_populates_only_real_ground_speed() -> None:
    subscriber = _Subscriber()
    source = NavigationMotionVehicleStateSource(subscriber)

    source._on_motion_state(  # noqa: SLF001 - isolate message-to-state behavior
        SimpleNamespace(data=SimpleNamespace(ground_speed_m_s=12.5))
    )
    state = source.read_state()

    assert state.vehicle_speed_m_s == 12.5
    assert state.engine_speed_rad_s is None
    assert state.boost_pressure_pa is None
    assert state.fuel_level is None
    assert state.coolant_temperature_k is None
    assert state.transmission_gear is None


def test_navigation_motion_starts_with_unknown_speed() -> None:
    source = NavigationMotionVehicleStateSource(_Subscriber())

    assert source.read_state().vehicle_speed_m_s is None
