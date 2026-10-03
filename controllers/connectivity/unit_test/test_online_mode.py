from unittest.mock import Mock, patch

import pytest

from controllers.connectivity.online_mode import OnlineModeController
from controllers.connectivity.internet_access import internet_reachable


def test_mode_persists_and_notifies_subscribers(tmp_path):
    path = tmp_path / 'settings/mode.json'
    mode = OnlineModeController(path)
    listener = Mock()
    unsubscribe = mode.subscribe(listener)
    mode.set_online(False)
    assert OnlineModeController(path).online is False
    listener.assert_called_once_with(False)
    unsubscribe()
    mode.set_online(True)
    listener.assert_called_once_with(False)


def test_failed_save_does_not_change_permission_or_notify(tmp_path):
    mode = OnlineModeController(tmp_path / 'mode.json')
    listener = Mock()
    mode.subscribe(listener)
    with patch('controllers.connectivity.online_mode.Path.write_text', side_effect=OSError('read only')):
        with pytest.raises(OSError):
            mode.set_online(False)
    assert mode.online
    listener.assert_not_called()


def test_reachability_requires_expected_response():
    with patch('controllers.connectivity.internet_access.urllib.request.urlopen') as open_url:
        open_url.return_value.__enter__.return_value.status = 200
        assert internet_reachable() is False
        open_url.return_value.__enter__.return_value.status = 204
        assert internet_reachable() is True
        assert open_url.call_args.kwargs['timeout'] == 3


def test_unreachable_network_is_not_online():
    with patch('controllers.connectivity.internet_access.urllib.request.urlopen', side_effect=TimeoutError):
        assert internet_reachable() is False
