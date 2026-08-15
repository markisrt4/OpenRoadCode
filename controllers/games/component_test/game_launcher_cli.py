"""CLI smoke test for the native Linux game launcher."""

import argparse
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_launcher import GameLauncher


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

    if args.list or not args.game:
        for game in games:
            state = "enabled" if game.enabled else "disabled"
            print(f"{game.name} [{state}] - {game.description}")
        return 0

    game = next((candidate for candidate in games if candidate.name == args.game), None)
    if game is None:
        raise SystemExit(f"unknown game: {args.game}")

    launcher = GameLauncher()
    print(f"Launching {game.name}: {' '.join(game.command)}")
    launcher.launch(game)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
