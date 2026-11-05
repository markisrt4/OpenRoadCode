"""The checked Census asset drives repeatable state build plans."""

import pytest

from development.maps.state_map_catalog import (catalog_document,
                                                 coverage_definition,
                                                 state_plan)


def test_catalog_contains_exactly_50_unique_state_identities():
    document = catalog_document()
    states = document["states"]
    assert len(states) == 50
    assert len({state["abbreviation"] for state in states}) == 50
    assert len({state["fips"] for state in states}) == 50
    assert all(state["overview"]["coverage"] and state["detail_shards"] for state in states)


def test_michigan_preserves_reviewed_overview_and_eight_detail_regions():
    state = state_plan("26")
    assert state["abbreviation"] == "MI"
    assert state["overview"]["coverage"] == "michigan-overview"
    assert len(state["detail_shards"]) == 8
    assert coverage_definition("mi-upper-west")[1] == (-90.5, 45.5, -87.0, 48.3)


def test_other_states_receive_deterministic_overview_and_detail_ids():
    state = state_plan("Wisconsin")
    assert state["overview"]["coverage"] == "us-wi-overview"
    assert state["detail_shards"][0]["coverage"] == "us-wi-detail-r0-c0"
    assert coverage_definition("us-wi-detail-r0-c0")[1] == tuple(
        state["detail_shards"][0]["bounds_deg"])
    with pytest.raises(ValueError, match="Unknown state"):
        state_plan("Atlantis")
