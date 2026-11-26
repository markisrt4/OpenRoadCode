# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Receiver arbitration tests without RF hardware."""

from concurrent.futures import ThreadPoolExecutor

from controllers.radio.receiver_ownership import ReceiverOwnershipController


def test_shared_receiver_requires_confirmed_release() -> None:
    controller = ReceiverOwnershipController()
    radio = controller.acquire("receiver-1", "radio")
    assert radio is not None
    assert controller.acquire("receiver-1", "adsb") is None
    assert not controller.release(radio, stopped=False)
    assert controller.acquire("receiver-1", "adsb") is None
    assert controller.release(radio, stopped=True)
    assert controller.acquire("receiver-1", "adsb") is not None


def test_separate_receivers_can_operate_concurrently() -> None:
    controller = ReceiverOwnershipController()
    assert controller.acquire("receiver-1", "radio") is not None
    assert controller.acquire("receiver-2", "adsb") is not None
    assert len(controller.snapshot()) == 2


def test_stale_lease_cannot_release_new_owner() -> None:
    controller = ReceiverOwnershipController()
    old = controller.acquire("receiver-1", "radio")
    assert old is not None
    assert controller.release(old, stopped=True)
    new = controller.acquire("receiver-1", "radio")
    assert new is not None
    assert not controller.release(old, stopped=True)
    assert controller.snapshot() == (new,)


def test_concurrent_requests_have_only_one_winner() -> None:
    controller = ReceiverOwnershipController()

    def acquire(index: int) -> bool:
        return controller.acquire("receiver-1", str(index)) is not None

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(acquire, range(32))) == 1
