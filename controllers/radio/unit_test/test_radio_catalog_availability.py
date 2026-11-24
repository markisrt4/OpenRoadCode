# SPDX-License-Identifier: MIT
"""Catalog availability tests without radio hardware."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from controllers.radio.radio_profiles import RadioProfileCatalog


def test_catalog_survives_disconnect_and_recovers(monkeypatch, tmp_path):
    monkeypatch.setenv("ORC_SDRFORGE_RADIO_CATALOG", "1")
    path = tmp_path / "presets.json"
    profile = SimpleNamespace(
        key="fm_radio",
        label="Remote FM",
        group="FM",
        mode_name="WFM",
        bandwidth=180000,
        step_hz=200000,
        minimum_frequency_hz=88100000,
        maximum_frequency_hz=107900000,
        start_frequency_hz=94700000,
        presets=(),
    )
    with patch("controllers.radio.radio_profiles.SdrforgeRadioCatalogClient") as client:
        client.return_value.profiles.side_effect = [(profile,), OSError(), (profile,)]
        catalog = RadioProfileCatalog(user_presets_path=path)
        assert catalog.presets_writable
        snapshot = catalog.profiles
        catalog.reload()
        assert not catalog.presets_writable
        assert catalog.profiles == snapshot
        with pytest.raises(ValueError, match="read-only"):
            catalog.add_user_preset("fm_radio", label="Test", frequency_hz=94700000)
        with pytest.raises(ValueError, match="read-only"):
            catalog.remove_user_preset("fm_radio", label="Test", frequency_hz=94700000)
        assert not path.exists()
        catalog.reload()
        assert catalog.presets_writable
        assert catalog.profiles == snapshot
