# Native Game Launcher

This controller provides a small, UI-independent layer for launching native Linux games from OpenRoadCode.

Games are described in `config/games.toml`. Commands are stored as argument arrays and are passed directly to `subprocess.Popen`; the launcher does not invoke a shell.

## Component test

List configured games:

```bash
python -m controllers.games.component_test.game_launcher_cli --list
```

Launch Extreme Tux Racer after installing it on the target:

```bash
python -m controllers.games.component_test.game_launcher_cli --game "Extreme Tux Racer"
```

The initial controller intentionally does not contain vehicle-motion policy or UI behavior. Those concerns can be layered above the launcher so the process-management code remains reusable.
