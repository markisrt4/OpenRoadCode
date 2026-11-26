# SPDX-License-Identifier: MIT

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from controllers.spotify.guarded_token_store import GuardedTokenStore
from controllers.spotify.spotify_account import (
    Commit,
    Current,
    SpotifyAccountBinding,
    SpotifyAccountController,
)
from protocols.spotify.spotify_auth import SpotifyAuthError
from ui.media.spotify_account_if import SpotifyAccountState

AccountFixture = tuple[
    SpotifyAccountController,
    SpotifyAccountBinding,
    Mock,
    Mock,
    list[Callable[[], None]],
    list[Callable[[], None]],
    list[bool],
    Mock,
    Mock,
    Mock,
    Mock,
]


@pytest.fixture
def account() -> AccountFixture:
    work: list[Callable[[], None]] = []
    ui: list[Callable[[], None]] = []
    online = [True]
    dispatcher = Mock()
    dispatcher.dispatch_ui.side_effect = ui.append
    read = Mock(return_value=("public-client", False))
    save, connect, disconnect, refresh = Mock(), Mock(), Mock(), Mock()
    controller = SpotifyAccountController(
        read_account=read,
        save_client_id=save,
        connect=connect,
        disconnect=disconnect,
        online=lambda: online[0],
        run_work=work.append,
        dispatcher=dispatcher,
        refresh_playback=refresh,
    )
    session = SpotifyAccountBinding(controller)
    view = Mock()
    session.activate(view)
    drain(work, ui)
    handler = view.set_spotify_account_handler.call_args.args[0]
    return controller, session, view, handler, work, ui, online, save, connect, disconnect, refresh


def drain(work: list[Callable[[], None]], ui: list[Callable[[], None]]) -> None:
    while work or ui:
        while work:
            work.pop(0)()
        while ui:
            ui.pop(0)()


def state(view: Mock) -> SpotifyAccountState:
    value = view.set_spotify_account_state.call_args.args[0]
    assert isinstance(value, SpotifyAccountState)
    return value


def test_state_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        SpotifyAccountState().connected = True  # type: ignore[misc]


def test_configuration_runs_off_frontend_and_normalizes_input(account: AccountFixture) -> None:
    _, _, view, handler, work, ui, _, save, _, _, refresh = account
    handler.request_configure("  changed-client  ")
    save.assert_not_called()
    assert state(view).busy
    work.pop(0)()
    save.assert_called_once_with("changed-client")
    assert state(view).busy
    ui.pop(0)()
    assert not state(view).busy
    assert "Restart" in state(view).message
    refresh.assert_called_once()


@pytest.mark.parametrize("retire", ["deactivate", "close"])
def test_retired_view_drops_queued_work_and_old_handler(
    account: AccountFixture, retire: str
) -> None:
    _, session, view, handler, work, ui, _, save, connect, _, _ = account
    handler.request_configure("changed")
    getattr(session, retire)()
    view.set_spotify_account_state.reset_mock()
    handler.request_connect()
    drain(work, ui)
    save.assert_not_called()
    connect.assert_not_called()
    view.set_spotify_account_state.assert_not_called()


def test_close_during_token_exchange_rejects_persistence_and_completion(
    account: AccountFixture,
) -> None:
    controller, _, view, handler, work, ui, _, _, connect, _, refresh = account
    store = Mock()

    def exchange(current: Current, commit: Commit) -> None:
        assert current()
        controller.close()
        GuardedTokenStore(store, commit).save(Mock())

    connect.side_effect = exchange
    handler.request_connect()
    work.pop(0)()
    view.set_spotify_account_state.reset_mock()
    drain(work, ui)
    store.save.assert_not_called()
    refresh.assert_not_called()
    view.set_spotify_account_state.assert_not_called()


def test_disconnect_supersedes_pending_authorization(account: AccountFixture) -> None:
    _, _, view, handler, work, ui, _, _, connect, disconnect, _ = account
    captured: list[tuple[Current, Commit]] = []
    connect.side_effect = lambda current, commit: captured.append((current, commit))
    handler.request_connect()
    work.pop(0)()
    handler.request_disconnect()
    current, commit = captured[0]
    assert not current()
    store = Mock()
    with pytest.raises(SpotifyAuthError, match="cancelled"):
        GuardedTokenStore(store, commit).save(Mock())
    drain(work, ui)
    disconnect.assert_called_once()
    store.save.assert_not_called()
    assert "disconnected" in state(view).message


def test_offline_transition_cancels_sign_in_and_clears_busy(account: AccountFixture) -> None:
    controller, _, view, handler, work, ui, online, _, connect, _, _ = account
    handler.request_connect()
    online[0] = False
    controller.network_changed()
    drain(work, ui)
    connect.assert_not_called()
    assert not state(view).busy
    assert not state(view).online
    assert state(view).error


def test_completed_hidden_action_does_not_restore_navigation(account: AccountFixture) -> None:
    _, session, view, handler, work, ui, _, _, _, _, refresh = account
    handler.request_connect()
    work.pop(0)()
    session.deactivate()
    view.set_spotify_account_state.reset_mock()
    ui.pop(0)()
    view.set_spotify_account_state.assert_not_called()
    refresh.assert_not_called()


def test_shared_view_retirement_only_cancels_its_own_action(account: AccountFixture) -> None:
    controller, session, _, handler, work, ui, _, save, _, _, _ = account
    other = SpotifyAccountBinding(controller)
    other_view = Mock()
    other.activate(other_view)
    handler.request_configure("changed")
    other.deactivate()
    drain(work, ui)
    save.assert_called_once_with("changed")
    session.close()


def test_old_requests_remain_retired_after_reactivation(account: AccountFixture) -> None:
    _, session, view, handler, work, ui, _, save, _, _, _ = account
    session.deactivate()
    session.activate(view)
    handler.request_configure("obsolete")
    drain(work, ui)
    save.assert_not_called()


def test_failure_is_rendered_and_allows_retry(account: AccountFixture) -> None:
    _, _, view, handler, work, ui, _, _, connect, _, _ = account
    connect.side_effect = RuntimeError("authorization rejected")
    handler.request_connect()
    drain(work, ui)
    assert state(view).error and not state(view).busy
    assert "authorization rejected" in state(view).message
    connect.side_effect = None
    handler.request_connect()
    drain(work, ui)
    assert not state(view).error


def test_empty_configuration_does_not_write(account: AccountFixture) -> None:
    _, _, view, handler, work, ui, _, save, _, _, _ = account
    handler.request_configure("  ")
    drain(work, ui)
    save.assert_not_called()
    assert state(view).error


def test_activation_failure_retires_partially_bound_view(account: AccountFixture) -> None:
    controller, _, _, _, _, _, _, _, _, _, _ = account
    controller.close()
    session, view = SpotifyAccountBinding(controller), Mock()
    with pytest.raises(RuntimeError, match="closed"):
        session.activate(view)
    assert view.set_spotify_account_handler.call_args.args == (None,)
