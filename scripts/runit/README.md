# OpenRoadCode runit services

These service definitions provide the Termux counterpart to the Linux service
installers under `scripts/systemd/`.

They supervise the same production runtime wrappers under `scripts/runtime/`:

- `openroadcode-broker` runs the ZeroMQ message broker.
- `openroadcode-navigation` runs the navigation service using
  `config/runtime.termux.toml`.

## Install

Termux requires the `termux-services` package:

```bash
pkg install termux-services
```

After installing the package, restart the Termux shell once so its service
environment is initialized. Then, from the OpenRoadCode repository:

```bash
./scripts/runit/install_termux_services.sh
```

The installer links the repository service definitions into
`$PREFIX/var/service/`. The links intentionally point back into the repository,
so service definitions remain version controlled and update with `git pull`.

## Control

```bash
sv up openroadcode-broker
sv up openroadcode-navigation

sv status openroadcode-broker
sv status openroadcode-navigation

sv down openroadcode-navigation
sv down openroadcode-broker
```

The navigation service uses `venv-termux/bin/python` when present and
`config/runtime.termux.toml`. The broker uses the same Termux virtual
environment and the normal production broker entry point.
