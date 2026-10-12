# SPDX-License-Identifier: MIT
"""Road matching observes fresh GPS and owns all asynchronous resources."""

from unittest.mock import Mock, patch
from types import SimpleNamespace
import pytest

from apps.orcUi.composition.road_speed_limit import configure_road_speed_limit
from apps.orcUi.navigation_presenter import PositionPresentationState


def test_cached_and_lost_fixes_clear_current_limit():
    presentation = Mock()
    presentation.position = PositionPresentationState()
    with patch("apps.orcUi.composition.road_speed_limit.RoadSpeedLimitController") as factory:
        composition = configure_road_speed_limit(Mock(), presentation, Mock())
        observe = presentation.observe_position.call_args.args[0]
        observe(PositionPresentationState(latitude_deg=42, longitude_deg=-83, fix_mode=3, is_cached=True))
        factory.return_value.update_position.assert_called_with(None)
        observe(PositionPresentationState(latitude_deg=42, longitude_deg=-83, fix_mode=3, accuracy_m=5))
        point, accuracy = factory.return_value.update_position.call_args.args
        assert point.latitude_rad == pytest.approx(0.7330382858)
        assert accuracy == 5
        observe(PositionPresentationState())
        factory.return_value.update_position.assert_called_with(None)
        composition.close()
        factory.return_value.close.assert_called_once()


def test_invalid_backend_construction_releases_pool():
    with patch("apps.orcUi.composition.road_speed_limit.ThreadPoolExecutor") as workers, patch(
        "apps.orcUi.composition.road_speed_limit.ValhallaSpeedLimitProvider", side_effect=RuntimeError("provider")):
        with pytest.raises(RuntimeError, match="provider"):
            configure_road_speed_limit(Mock(), Mock(), Mock())
        workers.return_value.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
