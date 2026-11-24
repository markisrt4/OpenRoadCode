# SPDX-License-Identifier: MIT
"""Radio catalog client contract tests without network or hardware."""

import io
import json
from unittest.mock import patch

from controllers.radio.sdrforge_radio_catalog_client import SdrforgeRadioCatalogClient


def test_catalog_maps_factory_and_user_presets():
    payloads = [
        {
            "profiles": [
                {
                    "key": "fm_radio",
                    "label": "FM Broadcast",
                    "group": "FM",
                    "minimum_frequency_hz": 87500000,
                    "maximum_frequency_hz": 108000000,
                    "start_frequency_hz": 88100000,
                    "default_mode": {"name": "WFM", "bandwidth_hz": 180000, "step_hz": 100000},
                }
            ]
        },
        {
            "presets": [
                {
                    "id": "factory-1",
                    "profile_key": "fm_radio",
                    "label": "Factory",
                    "frequency_hz": 88100000,
                    "origin": "factory",
                    "mode": {"name": "WFM", "bandwidth_hz": 180000, "step_hz": 100000},
                },
                {
                    "id": "user-1",
                    "profile_key": "fm_radio",
                    "label": "My station",
                    "frequency_hz": 94700000,
                    "origin": "user",
                    "mode": {"name": "WFM", "bandwidth_hz": 180000, "step_hz": 100000},
                },
            ]
        },
    ]
    urls = []

    def fetch(url, *, timeout):
        urls.append(url)
        return io.BytesIO(json.dumps(payloads.pop(0)).encode())

    with patch(
        "controllers.radio.sdrforge_readiness.urlopen",
        return_value=io.BytesIO(json.dumps({"status": "ok"}).encode()),
    ):
        with patch(
            "controllers.radio.sdrforge_radio_catalog_client.urllib.request.urlopen",
            side_effect=fetch,
        ):
            profiles = SdrforgeRadioCatalogClient().profiles()

    assert len(profiles) == 1
    assert profiles[0].key == "fm_radio"
    assert [preset.user_defined for preset in profiles[0].presets] == [False, True]
    assert profiles[0].presets[1].id == "user-1"
    assert urls == [
        "http://127.0.0.1:5570/v1/radio/profiles",
        "http://127.0.0.1:5570/v1/radio/presets",
    ]
