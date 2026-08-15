"""Interactive component test for the native Linux game launcher."""

import argparse
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition


def _print_games(games: list[GameDefinition]) -> None:
    for index, game in enumerate(games, start=1):
        state = "enabled" if game.enabled else "disabled"
        print(f"{index}. {game.name} [{state}] - {game.description}")


def _select_game(games: list[GameDefinition]) -> GameDefinition | None:
    _print_games(games)
    selection = input("Game number (blank to cancel): ").strip()
    if not selection:
        return None

    try:
        index = int(selection) - 1
    except ValueError:
        print("Please enter a game number.")
        return None

    if index < 0 or index >= len(games):
        print("Invalid game number.")
        return None

    return games[index]


def _interactive(games: list[GameDefinition]) -> int:
    launcher = GameLauncher()
    running_game: GameDefinition | None = None

    while True:
        if running_game is not None and not launcher.is_running():
            print(f"\n{running_game.name} exited.")
            running_game = None

        print("\nNative Game Launcher")
        print("1. List games")
        print("2. Launch game")
        print("3. Show running game")
        print("4. Stop game")
        print("q. Quit")

        choice = input("> ").strip().lower()

        if choice == "1":
            _print_games(games)
        elif choice == "2":
            if launcher.is_running():
                assert running_game is not None
                print(f"A game is already running: {running_game.name}")
                continue

            game = _select_game(games)
            if game is None:
                continue
            if not game.enabled:
                print(f"Game is disabled in the catalog: {game.name}")
                continue

            try:
                print(f"Launching {game.name}: {' '.join(game.command)}")
                launcher.launch(game)
                running_game = game
            except FileNotFoundError:
                print(f"Executable not found: {game.command[0]}")
                print("Install the game or update its command in config/games.toml.")
        elif choice == "3":
            if launcher.is_running() and running_game is not None:
                print(f"Running: {running_game.name}")
            else:
                print("No game is running.")
        elif choice == "4":
            if not launcher.is_running():
                print("No game is running.")
                running_game = None
                continue

            assert running_game is not None
            print(f"Stopping {running_game.name}...")
            launcher.stop()
            running_game = None
        elif choice in {"q", "quit", "exit"}:
            if launcher.is_running():
                assert running_game is not None
                print(f"Stopping {running_game.name} before exit...")
                launcher.stop()
            return 0
        else:
            print("Unknown selection.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/games.toml"),
        help="game catalog TOML file",
    )
    parser.add_argument("--list", action="store_true", help="list configured games")
    parser.add_argument("--game", help="exact game name to launch")
    args = parser.parse_args()

    games = load_game_catalog(args.config)

    if args.list:
        _print_games(games)
        return 0

    if args.game:
        game = next((candidate for candidate in games if candidate.name == args.game), None)
        if game is None:
            raise SystemExit(f"unknown game: {args.game}")

        launcher = GameLauncher()
        print(f"Launching {game.name}: {' '.join(game.command)}")
        launcher.launch(game)
        return 0

    return _interactive(games)


if __name__ == "__main__":
    raise SystemExit(main())
