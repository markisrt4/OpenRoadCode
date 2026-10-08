# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from frontends.tk.games.games_panel import GamesPanel
from ui.games import GameStatus, GameUiState


class GamesPanelActionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = Mock()
        self.panel = SimpleNamespace(
            _request_handler=self.handler,
            _theme=SimpleNamespace(
                ui=SimpleNamespace(
                    accent_success="#00aa00",
                    accent_primary="#0088cc",
                    text_muted="#777777",
                )
            ),
        )

    @staticmethod
    def _game(status: GameStatus) -> GameUiState:
        return GameUiState(
            game_id="five-in-a-row",
            name="Five in a Row",
            description="Board game",
            category="card_board",
            icon=None,
            status=status,
        )

    def test_ready_action_launches_using_game_id(self) -> None:
        label, action, _accent = GamesPanel._action_for(self.panel, self._game(GameStatus.READY))

        self.assertEqual(label, "PLAY")
        self.assertIsNotNone(action)
        action()

        self.handler.request_launch_game.assert_called_once_with("five-in-a-row")

    def test_available_action_installs_using_game_id(self) -> None:
        label, action, _accent = GamesPanel._action_for(self.panel, self._game(GameStatus.AVAILABLE))

        self.assertEqual(label, "INSTALL")
        self.assertIsNotNone(action)
        action()

        self.handler.request_install_game.assert_called_once_with("five-in-a-row")


if __name__ == "__main__":
    unittest.main()
