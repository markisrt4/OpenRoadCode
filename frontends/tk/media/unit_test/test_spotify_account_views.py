# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from frontends.tk.media.media_screen import MediaScreen
from frontends.tk.media.spotify_account_dialog import SpotifyAccountDialog
from frontends.tk.media.spotify_screen import SpotifyScreen
from ui.media.spotify_account_if import SpotifyAccountAction, SpotifyAccountState


def test_media_hiding_retires_accounts_and_dialog():
    host, session, close_dialog = Mock(), Mock(), Mock()
    screen = MediaScreen(host, theme_bundle=Mock(), show_spotify=Mock(), show_youtube=Mock(),
        show_youtube_music=Mock(), show_netflix=Mock(), account_session=session,
        close_account_configuration=close_dialog)
    handler = Mock()
    screen.set_spotify_account_handler(handler)
    screen.set_spotify_account_state(SpotifyAccountState(connected=False))
    screen._request_account_action()
    handler.request_connect.assert_called_once()
    screen.set_spotify_account_state(SpotifyAccountState(connected=True))
    screen._request_account_action()
    handler.request_disconnect.assert_called_once()
    screen.hide()
    session.deactivate.assert_called_once()
    close_dialog.assert_called_once()
    host.activate_screen.assert_not_called()


def test_spotify_hiding_retires_accounts_and_dialog():
    session, close_dialog = Mock(), Mock()
    screen = SpotifyScreen(Mock(), theme={"colors": {}}, back_action=Mock(),
        playback_session=Mock(), native_surface=Mock(), account_session=session,
        close_account_configuration=close_dialog)
    screen.hide()
    session.deactivate.assert_called_once()
    close_dialog.assert_called_once()


def dialog():
    view = SpotifyAccountDialog(Mock(), session=Mock(), theme_bundle=Mock())
    view._dialog, view._client_id, view._status, view._save = Mock(), Mock(), Mock(), Mock()
    view._client_id.get.return_value = ""
    return view


def test_configuration_snapshot_does_not_overwrite_input():
    view = dialog()
    view._client_id.get.return_value = "already typing"
    view.set_spotify_account_state(SpotifyAccountState(client_id="stored", loading=False))
    view._client_id.set.assert_not_called()


def test_configuration_emits_request_and_closes_after_success():
    view = dialog()
    window = view._dialog
    handler = Mock()
    view.set_spotify_account_handler(handler)
    view._client_id.get.return_value = "public-client"
    view._request_save()
    handler.request_configure.assert_called_once_with("public-client")
    view.set_spotify_account_state(SpotifyAccountState(loading=False, action=SpotifyAccountAction.CONFIGURE))
    window.destroy.assert_called_once()
    view._session.deactivate.assert_called_once()


def test_closed_dialog_ignores_late_state():
    view = dialog()
    status = view._status
    view.close()
    view.set_spotify_account_state(SpotifyAccountState(message="late"))
    status.set.assert_not_called()
