# SPDX-License-Identifier: MIT
"""Project receiver assignments and current reservations for the settings UI."""

from collections import Counter
from collections.abc import Callable

from controllers.radio.receiver_acquisition import ReceiverAcquisitionController
from controllers.radio.receiver_assignments import ReceiverAssignments, ReceiverAssignmentStore
from controllers.radio.receiver_ownership import ReceiverOwnershipController
from hardware_io.rf.receiver_discovery_if import ReceiverDiscoveryIf
from ui.radio.receiver_settings_if import ReceiverSetting, ReceiverSettingsState


class ReceiverSettingsController:
    """Expose USB inventory and preference editing without changing active leases."""

    def __init__(
        self,
        discovery: ReceiverDiscoveryIf,
        store: ReceiverAssignmentStore,
        ownership: ReceiverOwnershipController,
        *,
        acquisition: ReceiverAcquisitionController | None = None,
        run_work: Callable[[Callable[[], None]], None],
        run_ui: Callable[[Callable[[], None]], None],
    ) -> None:
        self._discovery = discovery
        self._store = store
        self._ownership = ownership
        self._acquisition = acquisition
        self._run_work = run_work
        self._run_ui = run_ui

    def _snapshot(self) -> ReceiverSettingsState:
        assignments = self._store.load()
        devices = self._discovery.discover()
        counts = Counter(device.serial for device in devices)
        owners = {lease.identity: lease.consumer for lease in self._ownership.snapshot()}
        phases = (
            {lease.identity: phase for lease, phase in self._acquisition.status()}
            if self._acquisition is not None
            else {}
        )
        receivers = tuple(
            ReceiverSetting(
                device.serial,
                device.identity,
                device.usb_path,
                owners.get(device.identity) if device.identity is not None else None,
                device.identity is not None and counts[device.serial] == 1,
                phases.get(device.identity) if device.identity is not None else None,
            )
            for device in devices
        )
        return ReceiverSettingsState(
            receivers, assignments.radio, assignments.weather, assignments.adsb
        )

    def refresh(
        self, on_result: Callable[[ReceiverSettingsState], None], on_error: Callable[[str], None]
    ) -> None:
        self._submit(self._snapshot, on_result, on_error)

    def save(
        self,
        radio: str | None,
        weather: str | None,
        adsb: str | None,
        on_result: Callable[[ReceiverSettingsState], None],
        on_error: Callable[[str], None],
    ) -> None:
        def persist() -> ReceiverSettingsState:
            state = self._snapshot()
            selectable = {receiver.identity for receiver in state.receivers if receiver.available}
            for requested, previous in zip(
                (radio, weather, adsb), (state.radio, state.weather, state.adsb), strict=True
            ):
                if requested is not None and requested != previous and requested not in selectable:
                    raise ValueError(f"Receiver {requested} is unavailable or ambiguous")
            self._store.save(ReceiverAssignments(radio, weather, adsb))
            return self._snapshot()

        self._submit(persist, on_result, on_error)

    def _submit(
        self,
        operation: Callable[[], ReceiverSettingsState],
        on_result: Callable[[ReceiverSettingsState], None],
        on_error: Callable[[str], None],
    ) -> None:
        def work() -> None:
            try:
                state = operation()
            except (OSError, TypeError, ValueError, KeyError) as exc:
                message = str(exc)
                self._run_ui(lambda: on_error(message))
            else:
                self._run_ui(lambda: on_result(state))

        self._run_work(work)
