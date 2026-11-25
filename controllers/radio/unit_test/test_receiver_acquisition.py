# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Acquisition lifecycle tests using simulated consumers."""

from threading import Event, Thread

import pytest

from controllers.radio.receiver_acquisition import ReceiverAcquisitionController
from controllers.radio.receiver_ownership import ReceiverOwnershipController
from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class FakeAdapter:
    def __init__(self, *, starts: bool = True, stops: bool = True) -> None:
        self.starts = starts
        self.stops = stops
        self.start_calls = 0

    def start(self, device: ReceiverDevice) -> bool:
        self.start_calls += 1
        return self.starts

    def stop(self) -> bool:
        return self.stops


DEVICE = ReceiverDevice("0bda", "2838", "00000001", "1-1")


def test_handover_requires_stop_confirmation() -> None:
    controller = ReceiverAcquisitionController(ReceiverOwnershipController())
    radio = FakeAdapter(stops=False)
    adsb = FakeAdapter()
    assert controller.start("radio", DEVICE, radio)
    assert not controller.start("adsb", DEVICE, adsb)
    assert not controller.stop("radio")
    assert not controller.start("adsb", DEVICE, adsb)
    assert adsb.start_calls == 0
    radio.stops = True
    assert controller.stop("radio")
    assert controller.start("adsb", DEVICE, adsb)


@pytest.mark.parametrize("stops", [True, False])
def test_failed_start_requires_cleanup(stops: bool) -> None:
    ownership = ReceiverOwnershipController()
    controller = ReceiverAcquisitionController(ownership)
    assert not controller.start("radio", DEVICE, FakeAdapter(starts=False, stops=stops))
    assert bool(ownership.snapshot()) is not stops


def test_same_adapter_cannot_start_twice() -> None:
    controller = ReceiverAcquisitionController(ReceiverOwnershipController())
    adapter = FakeAdapter()
    second = ReceiverDevice("0bda", "2838", "00000002", "1-2")
    assert controller.start("radio", DEVICE, adapter)
    assert not controller.start("weather", second, adapter)


def test_unknown_identity_cannot_acquire() -> None:
    controller = ReceiverAcquisitionController(ReceiverOwnershipController())
    adapter = FakeAdapter()
    assert not controller.start("radio", ReceiverDevice("0bda", "2838", "", "1-1"), adapter)
    assert adapter.start_calls == 0


def test_separate_receiver_can_start_while_first_receiver_is_starting() -> None:
    controller = ReceiverAcquisitionController(ReceiverOwnershipController())
    starting = Event()
    proceed = Event()
    acquired = Event()

    class SlowAdapter(FakeAdapter):
        def start(self, device: ReceiverDevice) -> bool:
            starting.set()
            return proceed.wait(timeout=5)

    def start_other() -> None:
        assert not controller.start("conflict", DEVICE, FakeAdapter())
        second = ReceiverDevice("0bda", "2838", "00000002", "1-2")
        if controller.start("adsb", second, FakeAdapter()):
            acquired.set()

    radio = Thread(target=controller.start, args=("radio", DEVICE, SlowAdapter()))
    other = Thread(target=start_other)
    radio.start()
    try:
        assert starting.wait(timeout=2)
        other.start()
        assert acquired.wait(timeout=2)
    finally:
        proceed.set()
        radio.join(timeout=5)
        if other.ident is not None:
            other.join(timeout=5)
    assert controller.stop("radio")
    assert controller.stop("adsb")
