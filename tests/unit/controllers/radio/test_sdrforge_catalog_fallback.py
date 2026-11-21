# SPDX-License-Identifier: MIT
"""Opt-in SDRForge catalog and offline fallback tests."""
from unittest.mock import patch

from controllers.radio.radio_profiles import RadioProfileCatalog
from controllers.radio.sdrforge_radio_catalog_client import (
    RemoteRadioPreset, RemoteRadioProfile,
)


def test_remote_catalog_is_authoritative_when_enabled(monkeypatch):
    monkeypatch.setenv("ORC_SDRFORGE_RADIO_CATALOG", "1")
    remote = RemoteRadioProfile(
        "fm_radio", "Remote FM", "FM", 87500000, 108000000,
        94700000, "WFM", 180000, 100000,
        (RemoteRadioPreset("preset-1", "fm_radio", "My FM", 94700000,
                           "WFM", 180000, 100000, True),),
    )
    with patch("controllers.radio.radio_profiles.SdrforgeRadioCatalogClient") as client:
        client.return_value.profiles.return_value = (remote,)
        catalog = RadioProfileCatalog()
    assert catalog.profile("fm_radio").label == "Remote FM"
    assert catalog.config_for("fm_radio").radio_range.start_frequency_hz == 94700000
    assert catalog.config_for("fm_radio").presets[0].label == "My FM"


def test_remote_failure_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("ORC_SDRFORGE_RADIO_CATALOG", "1")
    with patch("controllers.radio.radio_profiles.SdrforgeRadioCatalogClient") as client:
        client.return_value.profiles.side_effect = OSError("offline")
        catalog = RadioProfileCatalog()
    assert catalog.profiles
    assert catalog.config_for("fm_radio").key == "fm_radio"
