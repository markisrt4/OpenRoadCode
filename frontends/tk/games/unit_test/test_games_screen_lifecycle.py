"""Verify presentation delegates ownership and retires resize/loading state."""

from unittest.mock import Mock

import pytest

from frontends.tk.games.games_screen import GamesScreen
from ui.games import GamesSessionIf


@pytest.fixture
def screen(monkeypatch):
    host = Mock()
    host.schedule_ui_callback.return_value = "resize"
    session = Mock(spec=GamesSessionIf)
    panel = Mock()
    panel.show_runtime_host.return_value = (1, 800, 480)
    monkeypatch.setattr("frontends.tk.games.games_screen.GamesPanel", lambda *a, **k: panel)
    result = GamesScreen(
        host, session=session, theme_bundle=lambda: Mock(), theme_mode=lambda: Mock(),
    )
    return result, host, session, panel


def test_show_binds_only_supplied_session_and_presentation(screen):
    view, host, session, panel = screen
    assert not session.mock_calls
    view.show()
    session.activate.assert_called_once_with(panel, view)
    host.activate_screen.assert_called_once_with(view)
    session.deactivate.assert_called_once()


def test_resize_is_debounced_and_uses_supplied_host_callback(screen):
    view, host, session, panel = screen
    view.show()
    resize = Mock()
    assert view.show_runtime_host(resize) == (1, 800, 480)
    notify = panel.show_runtime_host.call_args.args[0]
    notify(900, 500)
    notify(1000, 600)
    host.cancel_ui_callback.assert_called_with("resize")
    resize.assert_not_called()
    host.schedule_ui_callback.call_args.args[1]()
    resize.assert_called_once_with(1000, 600)


def test_hide_cancels_pending_resize_and_drops_late_timer(screen):
    view, host, session, panel = screen
    view.show()
    resize = Mock()
    view.show_runtime_host(resize)
    panel.show_runtime_host.call_args.args[0](900, 500)
    timer = host.schedule_ui_callback.call_args.args[1]
    view.hide()
    timer()
    resize.assert_not_called()
    host.cancel_ui_callback.assert_called_with("resize")
    assert view._panel is None


def test_shutdown_closes_session_even_when_detachment_fails(screen):
    view, host, session, panel = screen
    session.deactivate.side_effect = RuntimeError("detach failed")
    label = Mock()
    view._loading_label = label
    with pytest.raises(RuntimeError, match="detach failed"):
        view.shutdown()
    label.destroy.assert_called_once()
    session.close.assert_called_once()
    view.shutdown()
    view.show()
    session.close.assert_called_once()
    session.activate.assert_not_called()


def test_activation_failure_retires_binding(screen):
    view, host, session, panel = screen
    session.activate.side_effect = RuntimeError("inventory failed")
    with pytest.raises(RuntimeError, match="inventory failed"):
        view.show()
    assert session.deactivate.call_count == 2
    assert view._panel is None
