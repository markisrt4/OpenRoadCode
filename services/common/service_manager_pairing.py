# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared pairing and per-client credentials for service-manager endpoints."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import secrets
import time
import uuid

from typing import Protocol


class ClientStoreIf(Protocol):
    def load(self) -> tuple["AuthorizedClient", ...]: ...
    def save(self, clients: tuple["AuthorizedClient", ...]) -> None: ...


@dataclass(frozen=True)
class AuthorizedClient:
    client_id: str
    name: str
    token_hash: str
    created_at: float


class ServiceManagerPairing:
    """Own temporary PINs and independently revocable client credentials."""

    def __init__(
        self,
        pin_ttl_seconds: float = 300.0,
        client_store: ClientStoreIf | None = None,
    ) -> None:
        self._pin_ttl_seconds = pin_ttl_seconds
        self._client_store = client_store
        self._pin_hash: str | None = None
        self._pin_expires_at = 0.0
        stored_clients = client_store.load() if client_store is not None else ()
        self._clients = {client.client_id: client for client in stored_clients}

    def begin(self) -> tuple[str, float]:
        pin = f"{secrets.randbelow(1_000_000):06d}"
        self._pin_hash = self._digest(pin)
        self._pin_expires_at = time.time() + self._pin_ttl_seconds
        return pin, self._pin_expires_at

    def pair(self, pin: str, client_name: str) -> tuple[str, str]:
        name = client_name.strip()
        if not name:
            raise ValueError("client_name is required")
        if self._pin_hash is None or time.time() > self._pin_expires_at:
            self._clear_pin()
            raise ValueError("pairing PIN is expired or unavailable")
        if not hmac.compare_digest(self._digest(pin), self._pin_hash):
            raise ValueError("invalid pairing PIN")
        self._clear_pin()
        client_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        self._clients[client_id] = AuthorizedClient(
            client_id=client_id,
            name=name,
            token_hash=self._digest(token),
            created_at=time.time(),
        )
        self._persist_clients()
        return client_id, token

    def authorized(self, token: str) -> bool:
        candidate = self._digest(token)
        return any(hmac.compare_digest(candidate, c.token_hash) for c in self._clients.values())

    def clients(self) -> tuple[AuthorizedClient, ...]:
        return tuple(self._clients.values())

    def revoke(self, client_id: str) -> bool:
        removed = self._clients.pop(client_id, None) is not None
        if removed:
            self._persist_clients()
        return removed

    def _persist_clients(self) -> None:
        if self._client_store is not None:
            self._client_store.save(tuple(self._clients.values()))

    def _clear_pin(self) -> None:
        self._pin_hash = None
        self._pin_expires_at = 0.0

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
