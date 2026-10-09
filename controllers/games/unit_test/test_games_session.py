"""Exercise native runtime ownership and stale completion behavior without Tk/X11."""

from collections import deque
import threading
from unittest.mock import Mock

import pytest

from controllers.games.game_inventory_cache import GameInventoryCache
from controllers.games.game_installer_if import GameInstallerIf
from controllers.games.game_launcher_if import GameLauncherIf
from controllers.games.game_types import GameDefinition
from controllers.games.games_session import GamesSession
from ui.games import GameStatus, GamesUiIf
from ui.games.game_window_embedder_if import GameWindowEmbedderIf
from ui.games.games_session_if import GamesRuntimeUiIf


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "controllers.games.game_controller.GameInventoryCache",
        lambda: GameInventoryCache(tmp_path / "inventory.json"),
    )
    game = GameDefinition("Mines", ("mines",))
    backend = Mock(spec=GameInstallerIf)
    backend.backend_id = "test"
    backend.is_installed.return_value = True
    backend.is_available.return_value = True
    backend.launch_command.return_value = ("runtime", "mines")
    backend.window_selectors.return_value = ("Mines", "mines")
    backend.relax_window_size_hints.return_value = True
    launcher = Mock(spec=GameLauncherIf)
    launcher.process_id = 42
    embedder = Mock(spec=GameWindowEmbedderIf)
    embedder.supported.return_value = True
    work, ui = deque(), deque()
    session = GamesSession(
        [game], [backend], launcher, embedder, run_work=work.append, run_ui=ui.append,
    )
    view = Mock(spec=GamesRuntimeUiIf)
    view.show_runtime_host.return_value = (99, 800, 480)
    inventory = Mock(spec=GamesUiIf)
    session.activate(inventory, view)
    work.popleft()()  # Inventory discovery.
    ui.popleft()()
    handler = inventory.set_games_request_handler.call_args.args[0]
    return session, launcher, embedder, view, inventory, handler, work, ui


def drain(queue):
    while queue:
        queue.popleft()()


def launch(runtime):
    runtime[5].request_launch_game("Mines")


def test_launch_uses_actual_launcher_contract_and_embedding_selectors(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    assert launcher.launch.call_args.args[1] == ("runtime", "mines")
    assert callable(launcher.launch.call_args.kwargs["on_exit"])
    view.set_runtime_loading.assert_called_once_with(True)
    drain(work)
    embedder.embed.assert_called_once_with(
        42, 99, 800, 480, window_name="Mines", window_class="mines",
        relax_size_hints=True,
    )
    assert view.set_runtime_loading.call_count == 1  # Worker cannot call the view.
    drain(ui)
    assert view.set_runtime_loading.call_args.args == (False,)
    assert inventory.set_games.call_args.args[0][0].status is GameStatus.RUNNING


def test_hide_before_embedding_drops_native_work_and_late_process_exit(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    exited = launcher.launch.call_args.kwargs["on_exit"]
    session.deactivate()
    inventory.set_games_request_handler.assert_called_with(None)
    view.reset_mock()
    exited()
    drain(work)
    drain(ui)
    embedder.embed.assert_not_called()
    launcher.stop.assert_called_once()
    embedder.clear.assert_called_once()
    assert not view.mock_calls


def test_queued_embed_completion_cannot_touch_reactivated_destination(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    work.popleft()()  # Successful embed completion queued.
    session.deactivate()
    next_view = Mock(spec=GamesRuntimeUiIf)
    next_inventory = Mock(spec=GamesUiIf)
    session.activate(next_inventory, next_view)
    drain(work)
    drain(ui)
    assert not next_view.mock_calls
    assert next_inventory.set_games.call_args.args[0][0].status is GameStatus.READY


def test_old_exit_does_not_stop_a_new_launch(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    old_exit = launcher.launch.call_args.kwargs["on_exit"]
    handler.request_stop_game()
    drain(work)
    drain(ui)
    handler.request_launch_game("Mines")
    old_exit()
    drain(ui)
    assert launcher.stop.call_count == 1
    assert inventory.set_games.call_args.args[0][0].status is GameStatus.RUNNING


def test_embed_failure_stops_process_and_restores_inventory(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    embedder.embed.side_effect = RuntimeError("native host disappeared")
    launch(runtime)
    drain(work)
    drain(ui)
    drain(work)
    drain(ui)
    launcher.stop.assert_called_once()
    view.hide_runtime_host.assert_called_once()
    assert inventory.set_games.call_args.args[0][0].status is GameStatus.READY


def test_missing_platform_support_does_not_launch_or_create_host(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    embedder.supported.return_value = False
    launch(runtime)
    launcher.launch.assert_not_called()
    view.show_runtime_host.assert_not_called()
    assert inventory.set_games.call_args.args[0][0].status is GameStatus.ERROR


def test_failed_launch_releases_native_resources_and_restores_view(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launcher.launch.side_effect = OSError("executable missing")
    launch(runtime)
    drain(work)
    drain(ui)
    launcher.stop.assert_called_once()
    embedder.clear.assert_called_once()
    view.hide_runtime_host.assert_called_once()
    assert inventory.set_games.call_args.args[0][0].status is GameStatus.ERROR


def test_close_attempts_all_native_cleanup_and_is_idempotent(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    launcher.stop.side_effect = RuntimeError("stop failed")
    with pytest.raises(RuntimeError, match="stop failed"):
        session.close()
    embedder.clear.assert_called_once()
    session.close()
    drain(work)
    drain(ui)
    embedder.embed.assert_not_called()
    launcher.stop.assert_called_once()
    with pytest.raises(RuntimeError, match="closed"):
        session.activate(inventory, view)


def test_stale_resize_after_hide_is_not_sent_to_native_adapter(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    drain(work)
    drain(ui)
    session.resize(1024, 600)
    session.deactivate()
    drain(work)
    drain(ui)
    embedder.resize.assert_not_called()


def test_stop_cannot_clear_adapter_while_embedding_is_in_flight(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    entered, release, stop_started = threading.Event(), threading.Event(), threading.Event()
    def embed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return 1
    embedder.embed.side_effect = embed
    launch(runtime)
    embed_thread = threading.Thread(target=work.popleft())
    embed_thread.start()
    assert entered.wait(3)
    session.deactivate()
    stop = work.popleft()
    def stop_work():
        stop_started.set()
        stop()
    stop_thread = threading.Thread(target=stop_work)
    stop_thread.start()
    assert stop_started.wait(3)
    try:
        embedder.clear.assert_not_called()
        launcher.stop.assert_not_called()
    finally:
        release.set()
        embed_thread.join(3)
        stop_thread.join(3)
    assert not embed_thread.is_alive() and not stop_thread.is_alive()
    embedder.clear.assert_called_once()
    view.reset_mock()
    drain(ui)
    assert not view.mock_calls


def test_stop_requested_before_hide_cannot_stop_a_replacement_session(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    drain(work)
    drain(ui)
    handler.request_stop_game()  # Stop worker is queued but has not started.
    session.deactivate()
    session.activate(inventory, view)
    drain(work)
    drain(ui)
    assert launcher.stop.call_count == 1
    assert not work


def test_close_releases_native_resources_even_when_ui_detachment_fails(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    inventory.set_games_request_handler.side_effect = RuntimeError("detach failed")
    with pytest.raises(RuntimeError, match="detach failed"):
        session.close()
    launcher.stop.assert_called_once()
    embedder.clear.assert_called_once()


def test_delayed_duplicate_cleanup_cannot_stop_a_new_process(runtime):
    session, launcher, embedder, view, inventory, handler, work, ui = runtime
    launch(runtime)
    drain(work)
    drain(ui)
    entered, release = threading.Event(), threading.Event()
    def stop():
        entered.set()
        assert release.wait(3)
    launcher.stop.side_effect = stop
    handler.request_stop_game()
    stop_thread = threading.Thread(target=work.popleft())
    stop_thread.start()
    assert entered.wait(3)
    try:
        session.deactivate()  # Queues another cleanup while the stop is in flight.
    finally:
        release.set()
        stop_thread.join(3)
    assert not stop_thread.is_alive()
    drain(ui)
    session.activate(inventory, view)
    next_handler = inventory.set_games_request_handler.call_args.args[0]
    next_handler.request_launch_game("Mines")
    drain(work)  # Retired cleanup must not stop the newly launched process.
    drain(ui)
    assert launcher.stop.call_count == 1
    assert launcher.launch.call_count == 2
    assert embedder.embed.call_count == 2
    assert inventory.set_games.call_args.args[0][0].status is GameStatus.RUNNING
