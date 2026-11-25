# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Serialize acquisition lifecycle operations and retain uncertain reservations."""

from _thread import LockType
from dataclasses import dataclass, field
from threading import Lock

from controllers.radio.receiver_acquisition_if import ReceiverAcquisitionIf
from controllers.radio.receiver_ownership import ReceiverLease, ReceiverOwnershipController
from hardware_io.rf.receiver_discovery_if import ReceiverDevice


@dataclass(slots=True)
class _AcquisitionSession:
    lease: ReceiverLease
    adapter: ReceiverAcquisitionIf
    lock: LockType = field(default_factory=Lock)
    phase: str = "Acquiring"


class ReceiverAcquisitionController:
    def __init__(self, ownership: ReceiverOwnershipController) -> None:
        self._ownership = ownership
        self._lock = Lock()
        self._sessions: dict[str, _AcquisitionSession] = {}

    def start(self, consumer: str, device: ReceiverDevice, adapter: ReceiverAcquisitionIf) -> bool:
        identity = device.identity
        if identity is None:
            return False
        with self._lock:
            if consumer in self._sessions:
                return False
            if any(existing.adapter is adapter for existing in self._sessions.values()):
                return False
            lease = self._ownership.acquire(identity, consumer)
            if lease is None:
                return False
            session = _AcquisitionSession(lease, adapter)
            session.lock.acquire()
            self._sessions[consumer] = session
        try:
            try:
                if adapter.start(device):
                    self._set_phase(session, "Acquired")
                    return True
            except Exception as error:
                try:
                    self._stop_session(consumer, session)
                except Exception as cleanup:
                    error.add_note(f"Receiver cleanup also failed: {cleanup}")
                raise
            self._stop_session(consumer, session)
            return False
        finally:
            session.lock.release()

    def _set_phase(self, session: _AcquisitionSession, phase: str) -> None:
        with self._lock:
            session.phase = phase

    def uses_adapter(self, consumer: str, adapter: ReceiverAcquisitionIf) -> bool:
        with self._lock:
            session = self._sessions.get(consumer)
            return session is not None and session.adapter is adapter

    def status(self) -> tuple[tuple[ReceiverLease, str], ...]:
        with self._lock:
            return tuple((session.lease, session.phase) for session in self._sessions.values())

    def _stop_session(self, consumer: str, session: _AcquisitionSession) -> bool:
        self._set_phase(session, "Releasing")
        try:
            released = session.adapter.stop()
        except Exception:
            self._set_phase(session, "Release unconfirmed")
            raise
        if not released:
            self._set_phase(session, "Release unconfirmed")
            return False
        with self._lock:
            if not self._ownership.release(session.lease, stopped=True):
                session.phase = "Release unconfirmed"
                return False
            del self._sessions[consumer]
        return True

    def stop(self, consumer: str) -> bool:
        with self._lock:
            session = self._sessions.get(consumer)
        if session is None:
            return True
        with session.lock:
            with self._lock:
                current = self._sessions.get(consumer)
                if current is not session:
                    return current is None
            return self._stop_session(consumer, session)
