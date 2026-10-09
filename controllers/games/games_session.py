"""Own Games orchestration and serialize native operations outside presentation."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import threading

from common.resource_cleanup import close_resources
from ui.games import GamesUiIf
from ui.games.game_window_embedder_if import GameWindowEmbedderIf
from ui.games.games_session_if import GamesRuntimeUiIf

from .game_controller import GameController, WorkScheduler, UiScheduler
from .game_installer_if import GameInstallerIf
from .game_launcher_if import GameLauncherIf
from .game_types import GameDefinition


class GamesSession:
    """Bind inventory and native runtime through toolkit-neutral contracts."""

    def __init__(
        self, games: Sequence[GameDefinition], installers: Sequence[GameInstallerIf],
        launcher: GameLauncherIf, embedder: GameWindowEmbedderIf, *,
        run_work: WorkScheduler, run_ui: UiScheduler,
    ) -> None:
        self._games = tuple(games)
        self._installers = tuple(installers)
        self._launcher = launcher
        self._embedder = embedder
        self._run_work = run_work
        self._run_ui = run_ui
        self._native_lock = threading.Lock()
        self._controller: GameController | None = None
        self._view: GamesRuntimeUiIf | None = None
        self._generation = 0
        self._binding = 0
        self._closed = False
        self._stopping = False
        self._runtime_active = False
        self._native_generation = 0

    def activate(self, games_ui: GamesUiIf, runtime_ui: GamesRuntimeUiIf) -> None:
        """Bind a new visible destination; retired controllers cannot publish to it."""
        if self._closed:
            raise RuntimeError("Games session is closed")
        if self._controller is not None:
            self.deactivate()
        self._binding += 1
        binding = self._binding
        self._view = runtime_ui
        controller = GameController(
            self._games, self._installers, run_work=self._run_work, run_ui=self._run_ui,
            launch_game=self._launch, stop_game=lambda: self._stop_for_binding(binding),
        )
        self._controller = controller
        controller.set_games_ui(games_ui)
        controller.start()

    def deactivate(self) -> None:
        """Invalidate completions before releasing the frontend binding."""
        self._generation += 1
        self._binding += 1
        controller = self._controller
        self._controller = None
        self._view = None
        try:
            if controller is not None:
                controller.set_games_ui(None)
        finally:
            if self._runtime_active and not self._stopping:
                self._stopping = True
                native_generation = self._native_generation
                self._run_work(lambda: self._stop(
                    restore_view=False, native_generation=native_generation,
                ))

    def close(self) -> None:
        """Retire callbacks, then release both native resources even on failure."""
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        self._binding += 1
        controller = self._controller
        self._controller = None
        self._view = None
        def detach() -> None:
            if controller is not None:
                controller.set_games_ui(None)
        with self._native_lock:
            close_resources(detach, self._launcher.stop, self._embedder.clear)
        self._runtime_active = False

    def _launch(self, game: GameDefinition, backend: GameInstallerIf) -> None:
        view = self._view
        if view is None or self._closed:
            raise RuntimeError("Games screen is not active")
        if self._stopping or self._runtime_active:
            raise RuntimeError("A game is already running or stopping")
        if not self._embedder.supported():
            raise RuntimeError("Embedded games require xdotool")
        self._generation += 1
        generation = self._generation
        host_id, width, height = view.show_runtime_host(self.resize)
        view.set_runtime_loading(True)
        try:
            command = backend.launch_command(game)
            window_name, window_class = backend.window_selectors(game)
            relax_size_hints = backend.relax_window_size_hints(game)
            with self._native_lock:
                self._native_generation += 1
                self._launcher.launch(
                    game, command, on_exit=lambda: self._dispatch(
                        generation, self._process_exited,
                    ),
                )
                process_id = self._launcher.process_id
                if process_id is None:
                    raise RuntimeError(f"{game.name} exited immediately")
            self._runtime_active = True
            self._run_work(lambda: self._embed(
                generation, process_id, host_id, width, height,
                window_name, window_class, relax_size_hints,
            ))
        except Exception:
            self._generation += 1
            self._runtime_active = True
            self._stopping = True
            native_generation = self._native_generation
            self._run_work(lambda: self._stop(
                restore_view=False, native_generation=native_generation,
            ))
            view.set_runtime_loading(False)
            view.hide_runtime_host()
            raise

    def _dispatch(self, generation: int, callback: Callable[[], None]) -> None:
        def deliver() -> None:
            if not self._closed and generation == self._generation and self._view is not None:
                callback()
        self._run_ui(deliver)

    def _embed(
        self, generation: int, process_id: int, host_id: int, width: int, height: int,
        window_name: str | None, window_class: str | None, relax_size_hints: bool,
    ) -> None:
        try:
            with self._native_lock:
                if self._closed or generation != self._generation:
                    return
                self._embedder.embed(
                    process_id, host_id, width, height, window_name=window_name,
                    window_class=window_class, relax_size_hints=relax_size_hints,
                )
        except Exception:
            self._dispatch(generation, self._embed_failed)
        else:
            self._dispatch(generation, self._embed_succeeded)

    def _embed_succeeded(self) -> None:
        view = self._view
        if view is not None:
            view.set_runtime_loading(False)

    def _embed_failed(self) -> None:
        self._embed_succeeded()
        controller = self._controller
        if controller is not None:
            controller.request_stop_game()

    def _process_exited(self) -> None:
        controller = self._controller
        if controller is not None:
            controller.request_stop_game()

    def _stop_for_binding(self, binding: int) -> None:
        if binding == self._binding and not self._closed:
            self._stop()

    def _stop(
        self, *, restore_view: bool = True, native_generation: int | None = None,
    ) -> None:
        generation = self._generation
        native_generation = (self._native_generation if native_generation is None
                             else native_generation)
        try:
            with self._native_lock:
                if native_generation != self._native_generation:
                    return
                close_resources(self._launcher.stop, self._embedder.clear)
        finally:
            # Completion is delivered even if native cleanup raises; GameController
            # reports that error independently through its stop worker.
            self._run_ui(lambda: self._finish_stop(generation, native_generation, restore_view))

    def _finish_stop(self, generation: int, native_generation: int, restore_view: bool) -> None:
        if native_generation != self._native_generation:
            return
        self._runtime_active = False
        self._stopping = False
        if self._closed or generation != self._generation or not restore_view:
            return
        self._generation += 1
        view = self._view
        if view is not None:
            view.set_runtime_loading(False)
            view.hide_runtime_host()

    def resize(self, width: int, height: int) -> None:
        """Serialize resize with embedding and cleanup; drop stale requests."""
        generation = self._generation
        def resize_worker() -> None:
            with self._native_lock:
                if not self._closed and generation == self._generation and self._runtime_active:
                    self._embedder.resize(width, height)
        if self._view is not None and not self._closed:
            self._run_work(resize_worker)
