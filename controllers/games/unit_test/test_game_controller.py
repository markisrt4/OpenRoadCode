from __future__ import annotations

from pathlib import Path

from controllers.games.game_controller import GameController
from controllers.games.game_inventory_cache import GameInventoryCache
from controllers.games.game_types import GameDefinition
from ui.games import GameStatus


class FakeInstaller:
    def __init__(self, backend_id: str, *, installed: bool = False, available: bool = True) -> None:
        self._backend_id = backend_id
        self.installed = installed
        self.available = available
        self.install_error: Exception | None = None

    @property
    def backend_id(self) -> str:
        return self._backend_id

    def is_available(self, game: GameDefinition) -> bool:
        return self.available

    def is_installed(self, game: GameDefinition) -> bool:
        return self.installed

    def install(self, game: GameDefinition) -> None:
        if self.install_error is not None:
            raise self.install_error
        self.installed = True

    def launch_command(self, game: GameDefinition):
        return game.command


class StubGamesUi:
    def __init__(self) -> None:
        self.games = ()
        self.status = ""
        self.handler = None

    def set_games(self, games) -> None:
        self.games = tuple(games)

    def set_games_status(self, message: str) -> None:
        self.status = message

    def set_games_request_handler(self, handler) -> None:
        self.handler = handler

    def state(self, game_id: str):
        return next(game for game in self.games if game.game_id == game_id)


def _game() -> GameDefinition:
    return GameDefinition(name="KMines", command=("kmines",), description="Minesweeper")


def test_cached_game_is_ready_without_backend_probe(tmp_path: Path) -> None:
    cache = GameInventoryCache(tmp_path / "inventory.json")
    cache.save({"KMines": "termux"})
    installer = FakeInstaller("termux", installed=False, available=False)
    ui = StubGamesUi()
    controller = GameController([_game()], [installer], cache=cache)
    controller.set_games_ui(ui)

    controller.start()

    assert ui.state("KMines").status is GameStatus.READY
    assert ui.state("KMines").backend_id == "termux"


def test_uncached_available_game_becomes_available(tmp_path: Path) -> None:
    installer = FakeInstaller("debian", installed=False, available=True)
    ui = StubGamesUi()
    controller = GameController([_game()], [installer], cache=GameInventoryCache(tmp_path / "inventory.json"))
    controller.set_games_ui(ui)

    controller.start()

    assert ui.state("KMines").status is GameStatus.AVAILABLE
    assert ui.state("KMines").backend_id == "debian"


def test_install_transitions_through_installing_to_ready_and_caches(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    installer = FakeInstaller("debian", installed=False, available=True)
    ui = StubGamesUi()
    queued = []
    controller = GameController(
        [_game()],
        [installer],
        cache=GameInventoryCache(path),
        run_work=queued.append,
    )
    controller.set_games_ui(ui)
    controller.start()
    queued.pop(0)()

    controller.request_install_game("KMines")

    assert ui.state("KMines").status is GameStatus.INSTALLING
    assert ui.status == "Installing: KMines…"
    queued.pop(0)()
    assert ui.state("KMines").status is GameStatus.READY
    assert GameInventoryCache(path).load() == {"KMines": "debian"}


def test_failed_install_is_error_and_not_cached(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    installer = FakeInstaller("debian", installed=False, available=True)
    installer.install_error = RuntimeError("apt exploded")
    ui = StubGamesUi()
    controller = GameController([_game()], [installer], cache=GameInventoryCache(path))
    controller.set_games_ui(ui)
    controller.start()

    controller.request_install_game("KMines")

    assert ui.state("KMines").status is GameStatus.ERROR
    assert "apt exploded" in ui.status
    assert GameInventoryCache(path).load() == {}


def test_ui_requests_are_wired_to_controller(tmp_path: Path) -> None:
    ui = StubGamesUi()
    controller = GameController([_game()], [], cache=GameInventoryCache(tmp_path / "inventory.json"))

    controller.set_games_ui(ui)

    assert ui.handler is controller
