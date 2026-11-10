# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct and bind all Games dependencies at the application boundary."""

from collections.abc import Callable
from pathlib import Path
import threading

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from common.resource_cleanup import ResourceCleanup
from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_installer_factory import create_game_installers
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition
from controllers.games.games_session import GamesSession
from frontends.tk.games import GamesScreen
from frontends.x11.x11_window_embedder import X11WindowEmbedder


def _load_games() -> list[GameDefinition]:
    config = Path(__file__).resolve().parents[3] / "config" / "games.toml"
    try:
        return load_game_catalog(config)
    except (OSError, KeyError, TypeError, ValueError):
        return []


def _run_work(work: Callable[[], None]) -> None:
    threading.Thread(target=work, daemon=True).start()


def configure_games(app: OrcUiApp) -> GamesScreen:
    """Create dependencies and transfer their cleanup to the registered screen."""
    with ResourceCleanup() as cleanup:
        session = GamesSession(
            _load_games(), create_game_installers(), GameLauncher(), X11WindowEmbedder(),
            run_work=_run_work, run_ui=app.dispatch_ui,
        )
        cleanup.callback(session.close)
        screen = GamesScreen(
            app, session=session, theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
        )
        app.register_screen("GAMES", screen)
        cleanup.release()
    return screen
