"""Destination links retain normal browser behavior without navigation injection."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import pytest

from apps.launchers.earth_exploration_actions import EarthExplorationActions
from ui.navigation.poi_models import PoiAction, PoiActionKind


def test_opens_selected_uri_as_plain_browser_window():
    fallback = Mock()
    executor = EarthExplorationActions(fallback)
    uri = 'https://earth.google.com/web/search/42,-83'
    action = PoiAction(PoiActionKind.OPEN_WEBSITE, 'Explore in Google Earth',
                       provider_id='google-earth-explore', uri=uri)
    with (
        TemporaryDirectory() as temporary,
        patch('apps.launchers.earth_exploration_actions.shutil.which', return_value='/usr/bin/chromium'),
        patch('apps.launchers.earth_exploration_actions.logging_file_path', return_value=Path(temporary)/'earth.log'),
        # Keep hardware probing out of browser-handoff unit tests: Popen is
        # shared with subprocess.run, including Android getprop calls.
        patch('apps.launchers.earth_exploration_actions.graphics_environment',
              side_effect=lambda environment: dict(environment)),
        patch('apps.launchers.earth_exploration_actions.subprocess.Popen') as launch,
    ):
        assert executor.execute(Mock(), action) == 'Opened selected place in Google Earth'
    assert launch.call_args.args[0] == ['/usr/bin/chromium', '--new-window', '--start-maximized', '--password-store=basic', uri]
    fallback.execute.assert_not_called()


def test_other_place_actions_keep_platform_executor():
    fallback = Mock()
    poi, action = Mock(), PoiAction(PoiActionKind.ORDER, 'Order')
    assert EarthExplorationActions(fallback).execute(poi, action) is fallback.execute.return_value
    fallback.execute.assert_called_once_with(poi, action)


def test_rejects_disguised_earth_link():
    action = PoiAction(PoiActionKind.OPEN_WEBSITE, 'Explore', provider_id='google-earth-explore',
                       uri='https://earth.google.com.evil.example/web/search/42,-83')
    with patch('apps.launchers.earth_exploration_actions.subprocess.Popen') as launch:
        with pytest.raises(ValueError, match='Invalid'):
            EarthExplorationActions(Mock()).execute(Mock(), action)
    launch.assert_not_called()


def test_home_page_opens_without_selected_coordinates():
    action = PoiAction(PoiActionKind.OPEN_WEBSITE, 'Open Google Earth',
                       provider_id='google-earth-explore', uri='https://earth.google.com/web/')
    with (
        TemporaryDirectory() as temporary,
        patch('apps.launchers.earth_exploration_actions.shutil.which', return_value='/usr/bin/chromium'),
        patch('apps.launchers.earth_exploration_actions.logging_file_path', return_value=Path(temporary)/'earth.log'),
        # Keep hardware probing out of browser-handoff unit tests: Popen is
        # shared with subprocess.run, including Android getprop calls.
        patch('apps.launchers.earth_exploration_actions.graphics_environment',
              side_effect=lambda environment: dict(environment)),
        patch('apps.launchers.earth_exploration_actions.subprocess.Popen') as launch,
    ):
        assert EarthExplorationActions(Mock()).execute(Mock(), action) == 'Opened Google Earth'
    assert launch.call_args.args[0][-1] == 'https://earth.google.com/web/'
