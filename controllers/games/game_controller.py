"""Coordinate game inventory, installation, caching, and semantic UI state."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ui.games import GameStatus, GameUiState, GamesRequestHandlerIf, GamesUiIf

from .game_installer_if import GameInstallerIf
from .game_inventory_cache import GameInventoryCache
from .game_types import GameDefinition

GameLaunchHandler = Callable[[GameDefinition, GameInstallerIf], None]
GameStopHandler = Callable[[], None]
WorkScheduler = Callable[[Callable[[], None]], None]
UiScheduler = Callable[[Callable[[], None]], None]


class GameController(GamesRequestHandlerIf):
    """Own game lifecycle state independently of any concrete UI toolkit."""

    def __init__(
        self,
        games: Sequence[GameDefinition],
        installers: Sequence[GameInstallerIf],
        cache: GameInventoryCache | None = None,
        run_work: WorkScheduler | None = None,
        run_ui: UiScheduler | None = None,
        launch_game: GameLaunchHandler | None = None,
        stop_game: GameStopHandler | None = None,
    ) -> None:
        self._games = tuple(games)
        self._games_by_id = {game.name: game for game in self._games}
        self._installers = tuple(installers)
        self._installers_by_id = {installer.backend_id: installer for installer in self._installers}
        self._cache = cache or GameInventoryCache()
        self._run_work = run_work or (lambda work: work())
        self._run_ui = run_ui or (lambda work: work())
        self._launch_game = launch_game
        self._stop_game = stop_game
        self._ui: GamesUiIf | None = None
        self._installed: dict[str, GameInstallerIf] = {}
        self._available: dict[str, GameInstallerIf] = {}
        self._status: dict[str, GameStatus] = {}
        self._inventory_loading = False
        self._active_game_id: str | None = None
        self._launch_pending = False
        self._stop_pending = False

        cached = self._cache.load()
        for game in self._games:
            if not game.enabled:
                self._status[game.name] = GameStatus.DISABLED
                continue
            backend = self._installers_by_id.get(cached.get(game.name, ""))
            if backend is not None:
                self._installed[game.name] = backend
                self._available[game.name] = backend
                self._status[game.name] = GameStatus.READY
            else:
                self._status[game.name] = GameStatus.CHECKING

    def set_games_ui(self, games_ui: GamesUiIf | None) -> None:
        """Attach a games UI and wire its semantic request handler."""
        self._ui = games_ui
        if games_ui is None:
            return
        games_ui.set_games_request_handler(self)
        self._publish()

    def start(self) -> None:
        """Publish cached state immediately and scan only unresolved games."""
        self._publish_status("Checking games…")
        self._publish()
        self._scan_inventory(verify_cached=False)

    def request_refresh_games(self) -> None:
        """Handle a request for a complete inventory refresh."""
        if self._inventory_loading:
            return
        self._publish_status("Refreshing games…")
        self._scan_inventory(verify_cached=True)

    def request_install_game(self, game_id: str) -> None:
        """Handle a semantic install request."""
        game = self._games_by_id.get(game_id)
        backend = self._available.get(game_id)
        if game is None or backend is None or self._status.get(game_id) == GameStatus.INSTALLING:
            return
        self._status[game_id] = GameStatus.INSTALLING
        self._publish_status(f"Installing: {game.name}…")
        self._publish()
        self._run_work(lambda: self._install_worker(game, backend))

    def request_launch_game(self, game_id: str) -> None:
        """Handle a launch request after the frontend has created its runtime host."""
        game = self._games_by_id.get(game_id)
        backend = self._installed.get(game_id)
        if (
            game is None
            or backend is None
            or self._launch_game is None
            or self._launch_pending
            or self._stop_pending
            or self._active_game_id is not None
        ):
            return
        self._launch_pending = True
        self._publish_status(f"Launching: {game.name}…")
        try:
            self._launch_game(game, backend)
        except Exception as error:
            self._launch_pending = False
            self._status[game_id] = GameStatus.ERROR
            self._publish_status(f"Launch failed: {error}")
            self._publish()
            return
        self._launch_pending = False
        self._active_game_id = game_id
        self._status[game_id] = GameStatus.RUNNING
        self._publish_status(f"Playing: {game.name}")
        self._publish()

    def request_stop_game(self) -> None:
        """Stop the active game without waiting for its process on the UI thread."""
        if self._stop_pending:
            return
        active_game_id = self._active_game_id
        if active_game_id is None:
            active_game_id = next(
                (game_id for game_id, status in self._status.items() if status == GameStatus.RUNNING),
                None,
            )
        if self._stop_game is None:
            self._finish_stop(active_game_id, None)
            return
        self._stop_pending = True
        self._publish_status("Stopping game…")
        self._run_work(lambda: self._stop_worker(active_game_id))

    def _stop_worker(self, active_game_id: str | None) -> None:
        error: Exception | None = None
        try:
            assert self._stop_game is not None
            self._stop_game()
        except Exception as exc:
            error = exc
        self._run_ui(lambda: self._finish_stop(active_game_id, error))

    def _finish_stop(self, active_game_id: str | None, error: Exception | None) -> None:
        self._stop_pending = False
        self._active_game_id = None
        if active_game_id is not None and self._status.get(active_game_id) == GameStatus.RUNNING:
            self._status[active_game_id] = GameStatus.READY
        if error is not None:
            self._publish_status(f"Stop failed: {error}")
        else:
            self._publish_status("Choose a game")
        self._publish()

    def _scan_inventory(self, verify_cached: bool) -> None:
        if self._inventory_loading:
            return
        self._inventory_loading = True
        unresolved = tuple(
            game for game in self._games
            if game.enabled and (verify_cached or game.name not in self._installed)
        )
        if not unresolved:
            self._inventory_loading = False
            self._publish_status("Choose a game")
            return
        for game in unresolved:
            if self._status.get(game.name) != GameStatus.INSTALLING:
                self._status[game.name] = GameStatus.CHECKING
        self._publish()
        self._run_work(lambda: self._inventory_worker(unresolved, verify_cached))

    def _inventory_worker(self, games: Sequence[GameDefinition], verify_cached: bool) -> None:
        inventory: dict[str, tuple[GameInstallerIf | None, GameInstallerIf | None]] = {}
        for game in games:
            installed_backend = None
            available_backend = None
            for installer in self._installers:
                try:
                    if installed_backend is None and installer.is_installed(game):
                        installed_backend = installer
                    if available_backend is None and installer.is_available(game):
                        available_backend = installer
                except (OSError, RuntimeError):
                    continue
            inventory[game.name] = (installed_backend, available_backend)
        self._run_ui(lambda: self._inventory_finished(inventory, verify_cached))

    def _inventory_finished(
        self,
        inventory: dict[str, tuple[GameInstallerIf | None, GameInstallerIf | None]],
        verify_cached: bool,
    ) -> None:
        for game_id, (installed_backend, available_backend) in inventory.items():
            if self._status.get(game_id) == GameStatus.INSTALLING:
                continue
            if installed_backend is not None:
                self._installed[game_id] = installed_backend
                self._available[game_id] = available_backend or installed_backend
                self._status[game_id] = GameStatus.READY
            else:
                if verify_cached:
                    self._installed.pop(game_id, None)
                if available_backend is not None:
                    self._available[game_id] = available_backend
                    self._status[game_id] = GameStatus.AVAILABLE
                else:
                    self._available.pop(game_id, None)
                    self._status[game_id] = GameStatus.UNAVAILABLE
        self._inventory_loading = False
        self._save_cache()
        self._publish_status("Choose a game")
        self._publish()

    def _install_worker(self, game: GameDefinition, backend: GameInstallerIf) -> None:
        error: Exception | None = None
        try:
            backend.install(game)
            if not backend.is_installed(game):
                error = RuntimeError(f"Installed package, but {game.command[0]} was not found")
        except Exception as exc:
            error = exc
        self._run_ui(lambda: self._install_finished(game, backend, error))

    def _install_finished(
        self,
        game: GameDefinition,
        backend: GameInstallerIf,
        error: Exception | None,
    ) -> None:
        if error is not None:
            self._status[game.name] = GameStatus.ERROR
            self._publish_status(f"Install failed: {error}")
            self._publish()
            return
        self._installed[game.name] = backend
        self._available[game.name] = backend
        self._status[game.name] = GameStatus.READY
        self._save_cache()
        self._publish_status(f"Installed: {game.name}")
        self._publish()

    def _save_cache(self) -> None:
        values = {game_id: backend.backend_id for game_id, backend in self._installed.items()}
        try:
            self._cache.save(values)
        except OSError:
            pass

    def _publish_status(self, message: str) -> None:
        if self._ui is not None:
            self._ui.set_games_status(message)

    def _publish(self) -> None:
        if self._ui is None:
            return
        self._ui.set_games(
            tuple(
                GameUiState(
                    game_id=game.name,
                    name=game.name,
                    description=game.description,
                    category=game.category,
                    icon=game.icon,
                    status=self._status[game.name],
                    backend_id=(self._installed.get(game.name) or self._available.get(game.name)).backend_id
                    if (self._installed.get(game.name) or self._available.get(game.name)) is not None
                    else None,
                )
                for game in self._games
            )
        )
