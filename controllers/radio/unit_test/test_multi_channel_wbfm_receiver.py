# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""End-to-end synthetic tests for two WFM stations in one IQ capture."""

import unittest

import numpy as np

from controllers.radio.multi_channel_wbfm_receiver import MultiChannelWbfmReceiver
from controllers.radio.virtual_receiver_manager import VirtualChannel
from hardware_io.sdr.sdr_types import IqBlock

RATE = 2_400_000
CENTER = 104_300_000


def fm_capture(count: int = 240_000) -> IqBlock:
    t = np.arange(count, dtype=np.float64) / RATE
    phase_a = 2 * np.pi * (100_000 * t + 15_000 / (2 * np.pi * 1_000) *
                          (1 - np.cos(2 * np.pi * 1_000 * t)))
    phase_b = 2 * np.pi * (-300_000 * t + 12_000 / (2 * np.pi * 2_000) *
                          (1 - np.cos(2 * np.pi * 2_000 * t)))
    iq = 0.35 * np.exp(1j * phase_a) + 0.35 * np.exp(1j * phase_b)
    raw = np.empty(2 * count, dtype=np.uint8)
    raw[::2] = np.clip(np.rint(127.5 + 127.5 * iq.real), 0, 255).astype(np.uint8)
    raw[1::2] = np.clip(np.rint(127.5 + 127.5 * iq.imag), 0, 255).astype(np.uint8)
    return IqBlock(raw.tobytes(), CENTER, RATE, 1)


def receiver() -> MultiChannelWbfmReceiver:
    radio = MultiChannelWbfmReceiver()
    radio.add_channel(VirtualChannel("station_a", CENTER + 100_000))
    radio.add_channel(VirtualChannel("station_b", CENTER - 300_000))
    return radio


def dominant_hz(audio: np.ndarray) -> float:
    steady = audio[1_200:]
    spectrum = np.abs(np.fft.rfft(steady))
    return float(np.fft.rfftfreq(len(steady), 1 / 48_000)[np.argmax(spectrum)])


class MultiChannelWbfmReceiverTest(unittest.TestCase):
    def test_two_stations_produce_distinct_audio(self) -> None:
        audio = receiver().process(fm_capture())
        self.assertEqual(set(audio), {"station_a", "station_b"})
        self.assertEqual(len(audio["station_a"]), 4_800)
        self.assertEqual(len(audio["station_b"]), 4_800)
        self.assertLess(abs(dominant_hz(audio["station_a"]) - 1_000), 20)
        self.assertLess(abs(dominant_hz(audio["station_b"]) - 2_000), 20)

    def test_streaming_matches_single_block(self) -> None:
        capture = fm_capture(96_000)
        expected = receiver().process(capture)
        streaming = receiver()
        chunks = {"station_a": [], "station_b": []}
        for offset in range(0, len(capture.samples), 24_690):
            block = IqBlock(capture.samples[offset:offset + 24_690], CENTER, RATE, 1)
            for name, pcm in streaming.process(block).items():
                chunks[name].append(pcm)
        for name in chunks:
            np.testing.assert_allclose(np.concatenate(chunks[name]),
                                       expected[name], atol=1e-5)

    def test_retune_one_channel_preserves_other(self) -> None:
        capture = fm_capture(48_000)
        baseline = receiver()
        baseline.process(capture)
        expected = baseline.process(capture)["station_a"]
        actual = receiver()
        actual.process(capture)
        actual.retune_channel("station_b", CENTER - 200_000)
        observed = actual.process(capture)["station_a"]
        np.testing.assert_allclose(observed, expected, atol=1e-5)


if __name__ == "__main__":
    unittest.main()
