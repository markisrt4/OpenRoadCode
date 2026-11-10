"""Composition releases its Games session if screen registration fails."""

from unittest.mock import Mock

import pytest

from apps.orcUi.composition.games import configure_games


def test_registration_failure_closes_session_without_replacing_original_error(monkeypatch):
    session = Mock()
    session.close.side_effect = RuntimeError("cleanup failed")
    app = Mock()
    app.register_screen.side_effect = ValueError("registration failed")
    monkeypatch.setattr("apps.orcUi.composition.games.GamesSession", lambda *a, **k: session)
    monkeypatch.setattr("apps.orcUi.composition.games._load_games", lambda: [])
    monkeypatch.setattr("apps.orcUi.composition.games.create_game_installers", lambda: [])
    with pytest.raises(ValueError, match="registration failed") as error:
        configure_games(app)
    session.close.assert_called_once()
    assert any("cleanup failed" in note for note in error.value.__notes__)
