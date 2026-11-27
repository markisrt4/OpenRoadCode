# SPDX-License-Identifier: MIT
"""Hardware-free SDRForge receiver ordering tests."""

from controllers.radio.adapters.sdrforge_zmq_spectrum_adapter import ReceiverSequenceFilter


def test_increasing_sequence_accepted_and_duplicates_rejected() -> None:
    ordering = ReceiverSequenceFilter()
    assert ordering.accept({"stream_id": "first", "sequence": 1})
    assert ordering.accept({"stream_id": "first", "sequence": 3})
    assert not ordering.accept({"stream_id": "first", "sequence": 2})
    assert not ordering.accept({"stream_id": "first", "sequence": 3})


def test_new_publisher_resets_order_but_old_publisher_cannot_return() -> None:
    ordering = ReceiverSequenceFilter()
    assert ordering.accept({"stream_id": "first", "sequence": 40})
    assert ordering.accept({"stream_id": "second", "sequence": 1})
    assert not ordering.accept({"stream_id": "first", "sequence": 41})
    assert ordering.accept({"stream_id": "second", "sequence": 2})


def test_legacy_telemetry_remains_supported() -> None:
    ordering = ReceiverSequenceFilter()
    assert ordering.accept({})
    assert ordering.accept({"stream_id": "new", "sequence": 1})
    assert ordering.accept({})
    assert not ordering.accept({"stream_id": "new", "sequence": 0})
    assert not ordering.accept({"stream_id": "new", "sequence": True})
    assert not ordering.accept({"stream_id": "new"})
