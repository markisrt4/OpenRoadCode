# SPDX-License-Identifier: MIT

"""Prove the configured type gate rejects contract drift and invalid callers."""

from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_ui_types import main


ROOT = Path(__file__).resolve().parents[2]


def check_source(tmp_path, source):
    path = tmp_path / "contract_example.py"
    path.write_text(source)
    return subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(ROOT / "pyproject.toml"),
         "--cache-dir", str(tmp_path / "cache"), str(path)],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
    )


def test_gate_accepts_supported_route_binding_and_typed_caller(tmp_path):
    result = check_source(tmp_path, """
from controllers.navigation.navigation_route_request_handler import NavigationRouteRequestHandler
from ui.navigation import GeoPoint, RouteRequestHandlerIf
from ui.navigation.route_types import TravelMode

def bind(adapter: NavigationRouteRequestHandler) -> RouteRequestHandlerIf:
    return adapter

def navigate(handler: RouteRequestHandlerIf) -> None:
    handler.request_start_route(GeoPoint(0, 0), TravelMode.AUTO)
""")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("source,error_code", [
    ("""
def untyped_binding(handler):
    return handler
""", "[no-untyped-def]"),
    ("""
from ui.navigation import RouteRequestHandlerStub
from ui.navigation.route_types import TravelMode
from ui import UiWidget

class BrokenWidget(RouteRequestHandlerStub, UiWidget):
    def request_start_route(self, destination: str, travel_mode: TravelMode) -> None:
        pass
""", "[override]"),
    ("""
from ui.navigation import GeoPoint, RouteRequestHandlerIf
from ui.navigation.route_types import TravelMode

def navigate(handler: RouteRequestHandlerIf) -> None:
    handler.request_start_route(GeoPoint(0, 0), (), TravelMode.AUTO)
""", "[call-arg]"),
    ("""
from ui.navigation import GeoPoint, RouteRequestHandlerIf

def navigate(handler: RouteRequestHandlerIf) -> None:
    handler.request_start_route(GeoPoint(0, 0), "auto")
""", "[arg-type]"),
    ("""
from collections.abc import Callable
from ui.ui_dispatcher_if import UiDispatcherIf

class BrokenDispatcher:
    def dispatch_ui(self, callback: str) -> None:
        pass

    def schedule_ui_callback(self, delay_ms: int, callback: Callable[[], None]) -> object:
        return None

    def cancel_ui_callback(self, callback_id: object) -> None:
        pass

def bind(dispatcher: BrokenDispatcher) -> UiDispatcherIf:
    return dispatcher
""", "[return-value]"),
])
def test_gate_rejects_incompatible_contracts_and_calls(tmp_path, source, error_code):
    result = check_source(tmp_path, source)
    assert result.returncode == 1, result.stdout + result.stderr
    assert error_code in result.stdout, result.stdout + result.stderr


def test_missing_mypy_fails_instead_of_silently_skipping(monkeypatch, capsys):
    monkeypatch.setattr("scripts.check_ui_types.importlib.util.find_spec", lambda name: None)
    assert main() == 1
    assert "requirements-dev.txt" in capsys.readouterr().err


def test_gate_accepts_actual_games_bindings(tmp_path):
    result = check_source(tmp_path, """
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_launcher_if import GameLauncherIf
from controllers.games.games_session import GamesSession
from frontends.tk.games.games_screen import GamesScreen
from ui.games import GamesSessionIf, GamesRuntimeUiIf

def launcher(value: GameLauncher) -> GameLauncherIf:
    return value

def session(value: GamesSession) -> GamesSessionIf:
    return value

def surface(value: GamesScreen) -> GamesRuntimeUiIf:
    return value
""")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("source,error_code", [
    ("""
from controllers.games.game_launcher_if import GameLauncherIf
from controllers.games.game_types import GameDefinition

def launch(launcher: GameLauncherIf, game: GameDefinition) -> None:
    launcher.launch(game, ("game",), on_exit=lambda code: None)
""", "[arg-type]"),
    ("""
from collections.abc import Callable
from ui.games import GamesRuntimeUiIf

class BrokenSurface:
    def show_runtime_host(self, on_resize: Callable[[int, int], None]) -> str:
        return "native host"
    def hide_runtime_host(self) -> None:
        pass
    def set_runtime_loading(self, loading: bool) -> None:
        pass

def bind(value: BrokenSurface) -> GamesRuntimeUiIf:
    return value
""", "[return-value]"),
])
def test_gate_rejects_games_contract_drift(tmp_path, source, error_code):
    result = check_source(tmp_path, source)
    assert result.returncode == 1, result.stdout + result.stderr
    assert error_code in result.stdout, result.stdout + result.stderr


def test_gate_accepts_actual_radio_bindings(tmp_path):
    result = check_source(tmp_path, """
from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
from controllers.radio.streaming_radio_controller import StreamingRadioController
from frontends.tk.radio.streaming_radio_panel import StreamingRadioPanel
from ui.radio.streaming_radio_session_if import StreamingRadioSessionIf, StreamingRadioUiIf
from ui.radio.streaming_radio_state_source_if import StreamingRadioStateSourceIf

def session(value: StreamingRadioBrowser) -> StreamingRadioSessionIf:
    return value

def view(value: StreamingRadioPanel) -> StreamingRadioUiIf:
    return value

def summary(value: StreamingRadioController) -> StreamingRadioStateSourceIf:
    return value
""")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("source,error_code", [
    ("""
from ui.radio.streaming_radio_session_if import StreamingRadioRequestHandlerIf

def play(handler: StreamingRadioRequestHandlerIf) -> None:
    handler.request_play(12)
""", "[arg-type]"),
    ("""
from ui.radio.streaming_radio_state_source_if import StreamingRadioStateSourceIf

class BrokenStateSource:
    def snapshot(self) -> str:
        return "playing"

def bind(value: BrokenStateSource) -> StreamingRadioStateSourceIf:
    return value
""", "[return-value]"),
])
def test_gate_rejects_radio_contract_drift(tmp_path, source, error_code):
    result = check_source(tmp_path, source)
    assert result.returncode == 1, result.stdout + result.stderr
    assert error_code in result.stdout, result.stdout + result.stderr


def test_gate_rejects_rf_request_contract_drift(tmp_path):
    result = check_source(tmp_path, """
from ui.radio.rf_radio_if import RfRadioSession

def tune(session: RfRadioSession) -> None:
    session.request("tune up")
""")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "[arg-type]" in result.stdout
