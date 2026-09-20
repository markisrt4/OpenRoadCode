# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from services.common.service_manager_client_store import ServiceManagerClientStore
from services.common.service_manager_pairing import ServiceManagerPairing


def test_pairing_pin_is_six_digits_and_single_use():
    pairing = ServiceManagerPairing()
    pin, _ = pairing.begin()
    assert len(pin) == 6 and pin.isdigit()
    client_id, token = pairing.pair(pin, "Phone")
    assert client_id
    assert pairing.authorized(token)
    with pytest.raises(ValueError):
        pairing.pair(pin, "Second phone")


def test_wrong_pin_does_not_consume_valid_pin():
    pairing = ServiceManagerPairing()
    pin, _ = pairing.begin()
    with pytest.raises(ValueError, match="invalid"):
        pairing.pair("999999" if pin != "999999" else "000000", "Phone")
    _, token = pairing.pair(pin, "Phone")
    assert pairing.authorized(token)


def test_pin_expires():
    with patch("services.common.service_manager_pairing.time.time", side_effect=[100.0, 106.0]):
        pairing = ServiceManagerPairing(pin_ttl_seconds=5.0)
        pin, _ = pairing.begin()
        with pytest.raises(ValueError, match="expired"):
            pairing.pair(pin, "Phone")


def test_multiple_clients_have_unique_independently_revocable_tokens():
    pairing = ServiceManagerPairing()
    pin_a, _ = pairing.begin()
    id_a, token_a = pairing.pair(pin_a, "Phone")
    pin_b, _ = pairing.begin()
    id_b, token_b = pairing.pair(pin_b, "Tablet")
    assert id_a != id_b
    assert token_a != token_b
    assert pairing.authorized(token_a)
    assert pairing.authorized(token_b)
    assert pairing.revoke(id_a)
    assert not pairing.authorized(token_a)
    assert pairing.authorized(token_b)


def test_paired_clients_survive_reconstruction_and_revocation_persists():
    with tempfile.TemporaryDirectory() as directory:
        store = ServiceManagerClientStore(Path(directory) / "clients.json")
        first = ServiceManagerPairing(client_store=store)

        pin_a, _ = first.begin()
        id_a, token_a = first.pair(pin_a, "Phone")
        pin_b, _ = first.begin()
        _, token_b = first.pair(pin_b, "Tablet")

        restarted = ServiceManagerPairing(client_store=store)
        assert restarted.authorized(token_a)
        assert restarted.authorized(token_b)

        assert restarted.revoke(id_a)
        after_revoke = ServiceManagerPairing(client_store=store)
        assert not after_revoke.authorized(token_a)
        assert after_revoke.authorized(token_b)
