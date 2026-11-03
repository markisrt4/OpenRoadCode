# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose shared IQ channelization with independent WFM audio decoders."""

from __future__ import annotations

import numpy as np

from controllers.radio.dsp.channelized_wbfm_demodulator import ChannelizedWbfmDemodulator
from controllers.radio.virtual_receiver_manager import VirtualChannel, VirtualReceiverManager
from hardware_io.sdr.sdr_types import IqBlock


class MultiChannelWbfmReceiver:
    """Produce independent mono PCM streams from one shared IQ capture.

    Physical tuner control and audio playback are owned by other components.
    A channel change resets that channel's decoder without touching its peers.
    """

    def __init__(self, *, input_rate_hz: int = 2_400_000) -> None:
        self._manager = VirtualReceiverManager(input_rate_hz=input_rate_hz)
        self._decoders: dict[str, ChannelizedWbfmDemodulator] = {}

    @property
    def channels(self) -> tuple[VirtualChannel, ...]:
        return self._manager.channels

    def add_channel(self, config: VirtualChannel) -> None:
        if config.output_rate_hz != 240_000:
            raise ValueError("WFM audio requires 240 kSPS channel IQ")
        if config.bandwidth_hz < 150_000:
            raise ValueError("WFM audio requires at least 150 kHz channel bandwidth")
        self._manager.add_channel(config)
        self._decoders[config.name] = ChannelizedWbfmDemodulator()

    def remove_channel(self, name: str) -> None:
        self._manager.remove_channel(name)
        del self._decoders[name]

    def retune_channel(self, name: str, frequency_hz: int) -> None:
        self._manager.retune_channel(name, frequency_hz)
        self._decoders[name].reset()

    def reset(self) -> None:
        """Reset all DSP state following dropped samples or tuner retuning."""
        self._manager.reset()
        for decoder in self._decoders.values():
            decoder.reset()

    def process(self, block: IqBlock) -> dict[str, np.ndarray]:
        """Return 48 kHz float32 mono PCM keyed by virtual receiver name."""
        channel_iq = self._manager.process(block)
        return {
            name: self._decoders[name].process(samples)
            for name, samples in channel_iq.items()
        }
