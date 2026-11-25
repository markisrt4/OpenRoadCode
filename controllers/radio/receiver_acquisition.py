# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Serialize acquisition lifecycle operations and retain uncertain reservations."""

from threading import Lock

from controllers.radio.receiver_acquisition_if import ReceiverAcquisitionIf
from controllers.radio.receiver_ownership import ReceiverLease, ReceiverOwnershipController
from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class ReceiverAcquisitionController:
    def __init__(self, ownership: ReceiverOwnershipController) -> None:
        self._ownership = ownership
        self._lock = Lock()
        self._sessions: dict[str, tuple[ReceiverLease, ReceiverAcquisitionIf]] = {}

    def start(
        self, consumer: str, device: ReceiverDevice, adapter: ReceiverAcquisitionIf
    ) -> bool:
        identity = device.identity
        if identity is None:
            return False
        with self._lock:
            if consumer in self._sessions:
                return False
            if any(existing is adapter for _, existing in self._sessions.values()):
                return False
            lease = self._ownership.acquire(identity, consumer)
            if lease is None:
                return False
            self._sessions[consumer] = (lease, adapter)
            try:
                if adapter.start(device):
                    return True
            except Exception:
                self._stop_locked(consumer)
                raise
            self._stop_locked(consumer)
            return False

    def _stop_locked(self, consumer: str) -> bool:
        session = self._sessions.get(consumer)
        if session is None:
            return True
        lease, adapter = session
        if not adapter.stop():
            return False
        if not self._ownership.release(lease, stopped=True):
            return False
        del self._sessions[consumer]
        return True

    def stop(self, consumer: str) -> bool:
        with self._lock:
            return self._stop_locked(consumer)
