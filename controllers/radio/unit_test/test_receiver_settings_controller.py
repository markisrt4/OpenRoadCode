# SPDX-License-Identifier: MIT
"""Regression tests for receiver assignment and ambiguity in RF settings."""

from pathlib import Path

from controllers.radio.receiver_assignments import ReceiverAssignments, ReceiverAssignmentStore
from controllers.radio.receiver_ownership import ReceiverOwnershipController
from controllers.radio.receiver_settings_controller import ReceiverSettingsController
from hardware_io.rf.receiver_discovery_if import ReceiverDevice
from ui.radio.receiver_settings_if import ReceiverSettingsState


class Inventory:
    devices = (
        ReceiverDevice("0bda", "2838", "unique", "1-1"),
        ReceiverDevice("0bda", "2838", "duplicate", "1-2"),
        ReceiverDevice("0bda", "2838", "duplicate", "1-3"),
    )

    def discover(self) -> tuple[ReceiverDevice, ...]:
        return self.devices


def test_settings_retains_disconnected_assignment_and_rejects_ambiguous_selection(
    tmp_path: Path,
) -> None:
    inventory = Inventory()
    ownership = ReceiverOwnershipController()
    store = ReceiverAssignmentStore(tmp_path / "rf-receivers.json")
    store.save(ReceiverAssignments(weather="0bda:2838:disconnected"))
    assert ownership.acquire("0bda:2838:unique", "adsb") is not None
    settings = ReceiverSettingsController(
        inventory, store, ownership, run_work=lambda work: work(), run_ui=lambda work: work()
    )
    results: list[ReceiverSettingsState] = []
    errors: list[str] = []
    settings.refresh(results.append, errors.append)
    snapshot = results[-1]
    assert snapshot.weather == "0bda:2838:disconnected"
    assert snapshot.receivers[0].owner == "adsb"
    assert all(not device.available for device in snapshot.receivers[1:])

    settings.save("0bda:2838:duplicate", snapshot.weather, None, results.append, errors.append)
    assert "ambiguous" in errors[-1]
    assert store.load().radio is None

    settings.save("0bda:2838:unique", snapshot.weather, None, results.append, errors.append)
    assert store.load() == ReceiverAssignments(
        radio="0bda:2838:unique", weather="0bda:2838:disconnected"
    )
