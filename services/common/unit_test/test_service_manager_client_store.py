# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
import tempfile

from services.common.service_manager_client_store import ServiceManagerClientStore
from services.common.service_manager_pairing import AuthorizedClient


def test_missing_store_loads_empty_clients():
    with tempfile.TemporaryDirectory() as directory:
        store = ServiceManagerClientStore(Path(directory) / "clients.json")
        assert store.load() == ()


def test_multiple_clients_round_trip():
    with tempfile.TemporaryDirectory() as directory:
        store = ServiceManagerClientStore(Path(directory) / "clients.json")
        clients = (
            AuthorizedClient("phone-id", "Phone", "phone-hash", 100.0),
            AuthorizedClient("tablet-id", "Tablet", "tablet-hash", 200.0),
        )
        store.save(clients)
        assert store.load() == clients


def test_store_persists_hashes_not_bearer_tokens():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "clients.json"
        store = ServiceManagerClientStore(path)
        store.save((AuthorizedClient("phone-id", "Phone", "hashed-secret", 100.0),))
        contents = path.read_text(encoding="utf-8")
        assert "hashed-secret" in contents
        assert "access_token" not in contents


def test_clear_removes_client_store():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "clients.json"
        store = ServiceManagerClientStore(path)
        store.save((AuthorizedClient("phone-id", "Phone", "hash", 100.0),))
        store.clear()
        assert not path.exists()
