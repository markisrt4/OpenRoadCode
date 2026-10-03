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


def test_loss_and_recovery_notify_and_share_effective_state(tmp_path):
    from controllers.connectivity.online_mode import saved_online_mode
    path = tmp_path / 'mode.json'
    mode = OnlineModeController(path)
    listener = Mock()
    mode.subscribe(listener)
    mode.set_reachable(False)
    assert not mode.online and mode.requested_online
    assert not saved_online_mode(path)
    restored = OnlineModeController(path)
    assert not restored.online and restored.requested_online
    mode.set_reachable(False)
    assert listener.call_count == 1
    mode.set_reachable(True)
    assert mode.online and saved_online_mode(path)
    assert listener.call_args_list == [((False,),), ((True,),)]


def test_manual_offline_does_not_recover_automatically(tmp_path):
    mode = OnlineModeController(tmp_path / 'mode.json')
    mode.set_online(False)
    mode.set_reachable(True)
    assert not mode.online and not mode.requested_online
    mode.set_online(True)
    assert mode.online


def test_legacy_offline_preference_stays_manual(tmp_path):
    path = tmp_path / 'mode.json'
    path.write_text('{"online":false}')
    mode = OnlineModeController(path)
    mode.set_reachable(True)
    assert not mode.online and not mode.requested_online
