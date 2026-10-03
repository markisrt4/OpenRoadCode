# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Moved values must retain identity for backend and new UI callers."""
from controllers.automotive.engine_analysis import EngineAnalysis as BackendAnalysis
from controllers.automotive.vehicle_configuration import VehicleConfiguration as BackendConfiguration
from controllers.poi.poi_models import PoiCategory as BackendCategory
from controllers.radio.radio_types import RadioPreset as BackendPreset
from ui.automotive.engine_analysis import EngineAnalysis
from ui.automotive.vehicle_configuration import VehicleConfiguration
from ui.navigation.poi_models import PoiCategory
from ui.radio.radio_types import RadioPreset


def test_compatibility_exports_preserve_value_identity():
    assert BackendAnalysis is EngineAnalysis
    assert BackendConfiguration is VehicleConfiguration
    assert BackendCategory is PoiCategory
    assert BackendPreset is RadioPreset
