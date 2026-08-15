# Native Game Launcher

This controller provides a small, UI-independent layer for launching native Linux games from OpenRoadCode.

Games are described in `config/games.toml`. Commands are stored as argument arrays and are passed directly to `subprocess.Popen`; the launcher does not invoke a shell.

## Component test

Run the interactive component test from the repository root:

```bash
python3 -m controllers.games.component_test.game_launcher_cli
```

The menu can list configured games, launch an enabled game, report the running game, and stop it. Quitting the component test also stops a game that it launched.

List configured games without entering the interactive menu:

```bash
python3 -m controllers.games.component_test.game_launcher_cli --list
```

Launch Extreme Tux Racer directly after installing it on the target:

```bash
python3 -m controllers.games.component_test.game_launcher_cli --game "Extreme Tux Racer"
```

Games must be installed separately on the target system. A game also must have `enabled = true` in `config/games.toml` before the interactive launcher will start it.

The controller intentionally does not contain vehicle-motion policy or UI behavior. Those concerns can be layered above the launcher so the process-management code remains reusable.
