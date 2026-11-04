# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Standalone RDS receiver chain, independent of FM audio playback."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from controllers.radio.dsp.fm_multiplex_discriminator import FmMultiplexDiscriminator
from controllers.radio.dsp.rds_subcarrier_extractor import RdsSubcarrierExtractor
from controllers.radio.dsp.rds_carrier_recovery import RdsCarrierRecovery
from controllers.radio.dsp.rds_symbol_timing_recovery import RdsSymbolTimingRecovery
from controllers.radio.dsp.rds_biphase_decoder import RdsBiphaseDecoder
from controllers.radio.dsp.rds_block_sync import RdsBlockSynchronizer, RdsGroup
from controllers.radio.dsp.rds_metadata_decoder import RdsMetadata, RdsMetadataDecoder


@dataclass(frozen=True)
class RdsReceiverStatus:
    metadata: RdsMetadata
    groups_found: int
    invalid_pairs: int
    carrier_offset_hz: float
    half_bit_samples_per_symbol: float


class RdsReceiverController:
    """Process 240 kSPS FM multiplex (or channelized IQ) into RDS groups.

    Half-bit pair phase must currently be supplied by the caller. Automatic
    phase acquisition and real-world RDS BER remain future validation gates.
    Use process_multiplex when another consumer already demodulates FM to
    avoid duplicating the FM discriminator.
    """

    def __init__(self, *, pair_phase: int = 0) -> None:
        self._pair_phase = pair_phase
        self._fm = FmMultiplexDiscriminator()
        self._extractor = RdsSubcarrierExtractor()
        self._carrier = RdsCarrierRecovery()
        self._timing = RdsSymbolTimingRecovery(symbol_rate_hz=2375.0)
        self._biphase = RdsBiphaseDecoder(pair_phase=pair_phase)
        self._blocks = RdsBlockSynchronizer()
        self._metadata = RdsMetadataDecoder()

    def reset(self) -> None:
        for stage in (self._fm, self._extractor, self._carrier,
                      self._timing, self._biphase, self._blocks,
                      self._metadata):
            stage.reset()

    @property
    def status(self) -> RdsReceiverStatus:
        return RdsReceiverStatus(
            metadata=self._metadata.metadata,
            groups_found=self._blocks.groups_found,
            invalid_pairs=self._biphase.invalid_pairs,
            carrier_offset_hz=self._carrier.frequency_offset_hz,
            half_bit_samples_per_symbol=self._timing.samples_per_symbol,
        )

    def process_iq(self, iq: np.ndarray) -> list[RdsGroup]:
        """Accept complex FM channel IQ sampled at 240 kSPS."""
        return self.process_multiplex(self._fm.process(iq))

    def process_multiplex(self, multiplex: np.ndarray) -> list[RdsGroup]:
        """Accept real FM multiplex sampled at 240 kSPS."""
        baseband = self._extractor.process(multiplex)
        corrected = self._carrier.process(baseband)
        halves = self._timing.process(corrected)
        bits, valid = self._biphase.process(halves)
        groups = self._blocks.process(bits, valid)
        for group in groups:
            self._metadata.process(group)
        return groups
