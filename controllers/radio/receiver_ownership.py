# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""In-process receiver arbitration, independent of acquisition services."""

from dataclasses import dataclass
from threading import Lock
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ReceiverLease:
    identity: str
    consumer: str
    token: str


class ReceiverOwnershipController:
    """Reserve receivers until their consumers confirm acquisition has stopped."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._leases: dict[str, ReceiverLease] = {}

    def acquire(self, identity: str, consumer: str) -> ReceiverLease | None:
        if not identity.strip() or not consumer.strip():
            raise ValueError("Receiver identity and consumer are required")
        with self._lock:
            if identity in self._leases:
                return None
            lease = ReceiverLease(identity, consumer, uuid4().hex)
            self._leases[identity] = lease
            return lease

    def release(self, lease: ReceiverLease, *, stopped: bool) -> bool:
        """Never free a reservation after an unsuccessful acquisition shutdown."""
        with self._lock:
            if not stopped or self._leases.get(lease.identity) != lease:
                return False
            del self._leases[lease.identity]
            return True

    def snapshot(self) -> tuple[ReceiverLease, ...]:
        with self._lock:
            return tuple(self._leases.values())
