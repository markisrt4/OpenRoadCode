# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent authorized-client storage for service-manager pairing."""

from __future__ import annotations

from pathlib import Path

from protocols.auth import SecureJsonStore
from services.common.service_manager_pairing import AuthorizedClient


class ServiceManagerClientStore:
    """Persist independently revocable service-manager clients."""

    def __init__(self, path: Path) -> None:
        self._store = SecureJsonStore(path)

    @property
    def path(self) -> Path:
        return self._store.path

    def load(self) -> tuple[AuthorizedClient, ...]:
        payload = self._store.load()
        if payload is None:
            return ()
        clients = payload.get("clients", [])
        if not isinstance(clients, list):
            raise ValueError("service-manager client record must contain a clients list")
        return tuple(
            AuthorizedClient(
                client_id=str(item["client_id"]),
                name=str(item["name"]),
                token_hash=str(item["token_hash"]),
                created_at=float(item["created_at"]),
            )
            for item in clients
        )

    def save(self, clients: tuple[AuthorizedClient, ...]) -> None:
        self._store.save(
            {
                "clients": [
                    {
                        "client_id": client.client_id,
                        "name": client.name,
                        "token_hash": client.token_hash,
                        "created_at": client.created_at,
                    }
                    for client in clients
                ]
            }
        )

    def clear(self) -> None:
        self._store.clear()
