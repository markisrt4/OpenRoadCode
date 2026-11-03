"""Boundary asset normalization and presentation contract tests."""

import math

import pytest

from apps.launchers.state_boundary_overlay import load_state_boundary_overlay
from ui.navigation.boundary_overlay_state import BoundaryOverlayState, BoundaryRegionState


def test_census_boundaries_are_normalized_to_immutable_radians():
    state = load_state_boundary_overlay()
    assert [region.name for region in state.regions] == ['United States state boundaries', 'Michigan']
    assert [region.name for region in state.regions if region.emphasized] == ['Michigan']
    assert state.attribution.startswith('U.S. Census Bureau')
    assert max(abs(point[0]) for region in state.regions for path in region.paths_rad for point in path) <= math.pi
    document = state.document()
    assert 'source' not in str(document).lower()
    assert document['regions'][0]['paths_rad']
    edges = [tuple(sorted((start, end))) for path in state.regions[0].paths_rad
             for start, end in zip(path, path[1:])]
    assert len(edges) == len(set(edges))


def test_boundary_contract_rejects_mutable_short_and_unbounded_state():
    with pytest.raises(ValueError, match='immutable'):
        BoundaryRegionState('Michigan', True, [[(0.,0.),(.1,0.)]])
    with pytest.raises(ValueError, match='immutable lines'):
        BoundaryRegionState('Michigan', True, (((0.,0.),),))
    region = BoundaryRegionState('Michigan', True, (((0.,0.),(.1,0.)),))
    with pytest.raises(ValueError, match='attribution'):
        BoundaryOverlayState((region,), '')
