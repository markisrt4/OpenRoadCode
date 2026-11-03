# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-independent mixed-mode virtual SDR receiver.

The physical IQ source is injected by the caller. One IQ block feeds all
channels; each channel owns independent downconversion and demodulation state.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from controllers.radio.dsp.channelized_am_demodulator import ChannelizedAmDemodulator
from controllers.radio.dsp.channelized_nbfm_demodulator import ChannelizedNbfmDemodulator
from controllers.radio.dsp.channelized_wbfm_demodulator import ChannelizedWbfmDemodulator
from controllers.radio.virtual_receiver_manager import VirtualChannel, VirtualReceiverManager
from hardware_io.sdr.sdr_types import IqBlock


@dataclass(frozen=True)
class RadioChannel:
    name: str
    frequency_hz: int
    mode: str
    bandwidth_hz: int | None = None


class MultiModeRadioReceiver:
    """Demodulate independently tuned AM/NFM/WFM channels from shared IQ."""

    _BANDWIDTHS = {"WFM": 180_000, "NFM": 25_000, "AM": 25_000}
    _DEMODULATORS = {
        "WFM": ChannelizedWbfmDemodulator,
        "NFM": ChannelizedNbfmDemodulator,
        "AM": ChannelizedAmDemodulator,
    }

    def __init__(self, *, input_rate_hz: int = 2_400_000) -> None:
        self._manager = VirtualReceiverManager(input_rate_hz=input_rate_hz)
        self._decoders: dict[str, object] = {}
        self._configs: dict[str, RadioChannel] = {}

    @property
    def channels(self) -> tuple[RadioChannel, ...]:
        return tuple(self._configs.values())

    def add_channel(self, config: RadioChannel) -> None:
        mode = config.mode.upper()
        if mode not in self._DEMODULATORS:
            raise ValueError(f"unsupported radio mode: {config.mode}")
        bandwidth = (self._BANDWIDTHS[mode]
                     if config.bandwidth_hz is None else config.bandwidth_hz)
        if mode == "WFM" and bandwidth < 150_000:
            raise ValueError("WFM channel bandwidth must be at least 150 kHz")
        channel = VirtualChannel(config.name, config.frequency_hz,
                                 bandwidth_hz=bandwidth, output_rate_hz=240_000)
        self._manager.add_channel(channel)
        self._configs[config.name] = RadioChannel(config.name, config.frequency_hz,
                                                   mode, bandwidth)
        self._decoders[config.name] = self._DEMODULATORS[mode]()

    def remove_channel(self, name: str) -> None:
        self._manager.remove_channel(name)
        del self._decoders[name]
        del self._configs[name]

    def retune_channel(self, name: str, frequency_hz: int) -> None:
        self._manager.retune_channel(name, frequency_hz)
        old = self._configs[name]
        self._configs[name] = RadioChannel(old.name, frequency_hz, old.mode,
                                            old.bandwidth_hz)
        self._decoders[name].reset()

    def reset(self) -> None:
        """Reset after a source gap, RF retune or discontinuous recording."""
        self._manager.reset()
        for decoder in self._decoders.values():
            decoder.reset()

    def process(self, block: IqBlock) -> dict[str, np.ndarray]:
        """Return separate 48 kHz mono float32 PCM for every active channel."""
        iq_by_channel = self._manager.process(block)
        return {
            name: self._decoders[name].process(samples)
            for name, samples in iq_by_channel.items()
        }
