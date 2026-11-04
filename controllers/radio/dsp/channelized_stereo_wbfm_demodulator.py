# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Stereo WFM pipeline from 240 kSPS channelized complex IQ."""

from __future__ import annotations

import numpy as np

from controllers.radio.dsp.fm_multiplex_discriminator import FmMultiplexDiscriminator
from controllers.radio.dsp.fm_stereo_decoder import FmStereoDecoder


class ChannelizedStereoWbfmDemodulator:
    """Independent, resettable stereo path; mono WFM remains unchanged."""

    def __init__(self) -> None:
        self._multiplex = FmMultiplexDiscriminator()
        self._stereo = FmStereoDecoder()

    @property
    def stereo_locked(self) -> bool:
        return self._stereo.stereo_locked

    @property
    def stereo_blend(self) -> float:
        return self._stereo.stereo_blend

    def reset(self) -> None:
        self._multiplex.reset()
        self._stereo.reset()

    def process(self, iq: np.ndarray) -> np.ndarray:
        return self._stereo.process(self._multiplex.process(iq))
