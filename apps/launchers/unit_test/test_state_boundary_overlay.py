"""Boundary asset normalization and presentation contract tests."""

import math

import pytest

from apps.launchers.state_boundary_overlay import load_state_boundary_overlay
from ui.navigation.boundary_overlay_state import BoundaryOverlayState, BoundaryRegionState


def test_census_boundaries_are_normalized_to_immutable_radians():
    state = load_state_boundary_overlay()
    assert [region.kind for region in state.regions] == [
        "country",
        "disputed",
        "state",
        "state",
        "state",
    ]
    assert [region.name for region in state.regions if region.emphasized] == ["Michigan"]
    assert state.attribution.startswith("Natural Earth")
    assert (
        max(
            abs(point[0]) for region in state.regions for path in region.paths_rad for point in path
        )
        <= math.pi
    )
    document = state.document()
    assert "source" not in str(document).lower()
    assert document["regions"][0]["kind"] == "country"
    edges = [
        tuple(sorted((start, end)))
        for path in state.regions[2].paths_rad
        for start, end in zip(path, path[1:], strict=False)
    ]
    assert len(edges) == len(set(edges))

    canada = state.regions[4]
    assert canada.name == "Canadian province and territory boundaries"
    assert len(canada.paths_rad) == 17
    latitudes = [math.degrees(lat) for path in canada.paths_rad for _, lat in path]
    assert min(latitudes) < 50
    assert max(latitudes) > 65


def test_boundary_contract_rejects_mutable_short_and_unbounded_state():
    with pytest.raises(ValueError, match="immutable"):
        BoundaryRegionState("Michigan", True, [[(0.0, 0.0), (0.1, 0.0)]])
    with pytest.raises(ValueError, match="immutable lines"):
        BoundaryRegionState("Michigan", True, (((0.0, 0.0),),))
    with pytest.raises(ValueError, match="semantic"):
        BoundaryRegionState("Michigan", True, (((0.0, 0.0), (0.1, 0.0)),), "province")
    region = BoundaryRegionState("Michigan", True, (((0.0, 0.0), (0.1, 0.0)),))
    with pytest.raises(ValueError, match="attribution"):
        BoundaryOverlayState((region,), "")
