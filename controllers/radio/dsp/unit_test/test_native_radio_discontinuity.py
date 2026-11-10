# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Exercise transient RF gaps through the real native service reset path."""

import unittest
from unittest.mock import Mock

from controllers.radio.dsp.rds_block_sync import RdsGroup
from controllers.radio.multi_mode_radio_receiver import MultiModeRadioReceiver, RadioChannel
from controllers.radio.native_radio_service import NativeRadioService
from hardware_io.sdr.sdr_types import IqBlock


class NativeRadioDiscontinuityTest(unittest.TestCase):
    def test_timestamp_gap_preserves_rds_metadata_and_resets_dsp(self):
        receiver = MultiModeRadioReceiver(stereo_wfm=True, rds_wfm=True)
        receiver.add_channel(RadioChannel("fm", 104_300_000, "WFM"))
        source = Mock()
        source.get_acquisition_stats.return_value = {"dropped_blocks": 0}
        source.read_iq.side_effect = [
            IqBlock(bytes([128, 128] * 1200), 104_300_000, 2_400_000, 1_000_000_000),
            IqBlock(bytes([128, 128] * 1200), 104_300_000, 2_400_000, 1_100_000_000),
        ]
        service = NativeRadioService(
            source, receiver, center_frequency_hz=104_300_000)
        # The service is under test; replace only the DSP computation.
        receiver.process = Mock(return_value={})
        service.start()
        receiver._decoders["fm"]._rds._metadata.process(
            RdsGroup(0x7ADA, 0, 0, 0x574F, False))
        self.assertEqual(receiver.rds_status["fm"].metadata.pi, 0x7ADA)
        service.process_once()
        self.assertEqual(service.status.discontinuities, 0)
        service.process_once()
        self.assertEqual(service.status.discontinuities, 1)
        self.assertEqual(receiver.rds_status["fm"].metadata.pi, 0x7ADA)
        self.assertIsNone(receiver.rds_status["fm"].locked_pair_phase)
        service.stop()
        self.assertIsNone(receiver.rds_status["fm"].metadata.pi)


if __name__ == "__main__":
    unittest.main()
