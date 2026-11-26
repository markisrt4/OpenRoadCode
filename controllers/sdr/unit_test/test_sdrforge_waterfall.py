"""Hardware-free SDRForge waterfall and wire protocol tests."""

import json

import pytest

from controllers.sdr.sdrforge_spectrum import SdrForgeSpectrumFrame
from controllers.sdr.sdrforge_spectrum_subscriber import decode_spectrum_message
from controllers.sdr.sdrforge_waterfall import SdrForgeWaterfall


def payload(center=104_300_000, timestamp=1):
    return {
        "timestamp_ns": timestamp,
        "center_frequency_hz": center,
        "sample_rate_hz": 200_000,
        "bin_count": 2,
        "first_bin_frequency_hz": center - 100_000,
        "bin_spacing_hz": 100_000,
        "power_db": [-30.0, None],
    }


def test_wire_message_decodes_spectrum():
    message = (
        b"spectrum "
        + json.dumps(
            {
                "schema_version": 1,
                "payload": payload(),
            }
        ).encode()
    )
    frame = decode_spectrum_message(message)
    assert frame.center_frequency_hz == 104_300_000
    assert frame.power_db == (-30.0, None)


def test_other_topics_ignored():
    assert decode_spectrum_message(b"receiver {}") is None


def test_invalid_schema_rejected():
    with pytest.raises(ValueError):
        decode_spectrum_message(b'spectrum {"schema_version":2,"payload":{}}')


def test_history_is_bounded():
    history = SdrForgeWaterfall(max_rows=3)
    for i in range(6):
        history.append(SdrForgeSpectrumFrame.from_payload(payload(timestamp=i)))
    assert [frame.timestamp_ns for frame in history.rows] == [3, 4, 5]


def test_retune_clears_previous_waterfall():
    history = SdrForgeWaterfall()
    history.append(SdrForgeSpectrumFrame.from_payload(payload()))
    history.append(SdrForgeSpectrumFrame.from_payload(payload(center=162_550_000, timestamp=2)))
    assert len(history.rows) == 1
    assert history.latest.center_frequency_hz == 162_550_000


def test_timestamp_regression_resets_history():
    history = SdrForgeWaterfall()
    history.append(SdrForgeSpectrumFrame.from_payload(payload(timestamp=10)))
    history.append(SdrForgeSpectrumFrame.from_payload(payload(timestamp=2)))
    assert len(history.rows) == 1


def test_invalid_capacity():
    with pytest.raises(ValueError):
        SdrForgeWaterfall(max_rows=0)
