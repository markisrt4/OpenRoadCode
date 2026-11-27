# SPDX-License-Identifier: MIT
"""Regression tests for profile demodulation commands sent to SDRForge."""

from unittest.mock import patch

from protocols.rigctl.rigctl_client import RigctlClient


def test_nfm_is_not_silently_converted_to_wideband_fm() -> None:
    client = RigctlClient()
    with patch.object(client, "send", return_value="RPRT 0") as send:
        assert client.set_mode("NFM", 12_500) == "RPRT 0"
        send.assert_called_once_with("M NFM 12500")


def test_other_supported_modes_retain_their_bandwidths() -> None:
    client = RigctlClient()
    with patch.object(client, "send", return_value="RPRT 0") as send:
        for mode, bandwidth in (("WFM", 200_000), ("AM", 6_000), ("NFM", 7_500)):
            client.set_mode(mode, bandwidth)
            send.assert_called_with(f"M {mode} {bandwidth}")
