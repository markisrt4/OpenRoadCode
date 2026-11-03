"""Boundary asset normalization and presentation contract tests."""

import math

import pytest

from apps.launchers.state_boundary_overlay import load_state_boundary_overlay
from ui.navigation.boundary_overlay_state import BoundaryOverlayState, BoundaryRegionState


def test_census_boundaries_are_normalized_to_immutable_radians():
    state = load_state_boundary_overlay()
    assert [region.name for region in state.regions] == ['Michigan', 'Indiana', 'Ohio', 'Wisconsin']
    assert [region.name for region in state.regions if region.emphasized] == ['Michigan']
    assert state.attribution.startswith('U.S. Census Bureau')
    assert max(abs(point[0]) for region in state.regions for ring in region.rings_rad for point in ring) <= math.pi
    document = state.document()
    assert 'path' not in str(document).lower()
    assert document['regions'][0]['rings_rad'][0][0] == document['regions'][0]['rings_rad'][0][-1]


def test_boundary_contract_rejects_mutable_open_and_unbounded_state():
    with pytest.raises(ValueError, match='closed'):
        BoundaryRegionState('Michigan', True, (((0.,0.),(.1,0.),(.1,.1),(.2,.2)),))
    region = BoundaryRegionState('Michigan', True, (((0.,0.),(.1,0.),(.1,.1),(0.,0.)),))
    with pytest.raises(ValueError, match='attribution'):
        BoundaryOverlayState((region,), '')
