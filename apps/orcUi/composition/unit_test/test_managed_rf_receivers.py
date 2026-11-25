# SPDX-License-Identifier: MIT
"""Exercise the managed RF composition without systemd or USB hardware."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from apps.orcUi.composition.rf_receivers import RADIO_REST, WEATHER_REST, ManagedReceiverServices
from controllers.radio.receiver_assignments import ReceiverAssignments, ReceiverAssignmentStore
from controllers.radio.receiver_ownership import ReceiverOwnershipController
from hardware_io.rf.receiver_discovery_if import ReceiverDevice

RADIO = ReceiverDevice("0bda", "2838", "listen", "1-1")
WEATHER = ReceiverDevice("0bda", "2838", "noaa", "1-2")


def setup_receivers(
    path: Path, weather: ReceiverDevice
) -> tuple[ManagedReceiverServices, ReceiverOwnershipController]:
    assignments = ReceiverAssignmentStore(path)
    assignments.save(ReceiverAssignments(radio=RADIO.identity, weather=weather.identity))
    discovery = Mock()
    discovery.discover.return_value = (RADIO, WEATHER)
    ownership = ReceiverOwnershipController()
    managed = ManagedReceiverServices("test-token", ownership, assignments, discovery)
    managed._radio = Mock()
    managed._weather = Mock()
    return managed, ownership


def test_noaa_uses_second_supervised_instance_with_distinct_receiver(tmp_path: Path) -> None:
    services, ownership = setup_receivers(tmp_path / "assignments.json", WEATHER)
    services.start_radio()
    assert services.start_weather() == WEATHER_REST
    assert {lease.identity for lease in ownership.snapshot()} == {RADIO.identity, WEATHER.identity}
    services._radio.start.assert_called_once_with(RADIO)
    services._weather.start.assert_called_once_with(WEATHER)
    assert not services._radio.stop.called
    services.close()
    assert not ownership.snapshot()


def test_noaa_sharing_receiver_preserves_broadcast_until_explicit_stop(tmp_path: Path) -> None:
    services, ownership = setup_receivers(tmp_path / "assignments.json", RADIO)
    services.start_radio()
    with pytest.raises(RuntimeError, match="another RF consumer"):
        services.start_weather()
    services._radio.stop.assert_not_called()
    services.stop_radio()
    assert services.start_weather() == RADIO_REST
    assert ownership.snapshot()[0].consumer == "weather"
    services._weather.start.assert_not_called()
    services.close()
    assert not ownership.snapshot()
