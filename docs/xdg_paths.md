# OpenRoadCode XDG Paths

OpenRoadCode uses the XDG Base Directory Specification for per-user configuration, persistent application data, cache data, and runtime state. Path resolution is centralized in `common/xdg_paths.py`.

## Directory layout

| Purpose | Environment variable | Default ORC directory |
| --- | --- | --- |
| Configuration | `XDG_CONFIG_HOME` | `~/.config/openroadcode` |
| Persistent data | `XDG_DATA_HOME` | `~/.local/share/openroadcode` |
| Cache | `XDG_CACHE_HOME` | `~/.cache/openroadcode` |
| State | `XDG_STATE_HOME` | `~/.local/state/openroadcode` |

The environment variable specifies the base directory. OpenRoadCode appends `openroadcode` and any component-specific subdirectory. An unset, empty, or relative XDG override falls back to the standard home-relative directory. The helpers return paths without creating directories; the component that writes data owns directory creation.

## Linux and Termux

The same Python path-resolution logic is used on native Linux and Termux. When XDG variables are unset, paths are relative to the current process's home directory. The directory structure is therefore identical, although the actual home directory differs.

On Linux, the defaults are:

```text
~/.config/openroadcode
~/.local/share/openroadcode
~/.cache/openroadcode
~/.local/state/openroadcode
```

On native Termux, the defaults are:

```text
$HOME/.config/openroadcode
$HOME/.local/share/openroadcode
$HOME/.cache/openroadcode
$HOME/.local/state/openroadcode
```

For a standard Termux installation, `$HOME` is normally `/data/data/com.termux/files/home`. A Debian proot process may have a different home directory and environment. Its XDG paths are resolved in that process's own environment, not automatically shared with native Termux. Set the relevant XDG variables explicitly when two environments must use the same data location.

For example, either platform can override the data root before launching ORC:

```bash
export XDG_DATA_HOME="$HOME/orc-data"
PYTHONPATH=. python -m apps.orcUi
```

Persistent application data then resolves under `$HOME/orc-data/openroadcode`. This does not relocate system installation paths or override an explicitly configured absolute component path.

## What belongs where

Configuration contains user-editable settings and preferences. Persistent data contains information that should survive cache cleanup, such as browser profiles and saved favorites. Cache contains information that can be regenerated, such as media artwork and temporary discovery results. State contains runtime-generated information such as application logs.

A browser profile is persistent data because it may contain retained sessions and preferences. It must not be treated as disposable artwork cache. Likewise, logs belong in state rather than cache. Components should use the appropriate shared helper instead of constructing home-relative paths independently.

```python
from common.xdg_paths import openroadcode_cache_dir, openroadcode_data_dir

artwork_dir = openroadcode_cache_dir("media-art")
profile_dir = openroadcode_data_dir("browser", "spotify")
```

The exact component directory names are defined by their owners. The shared helpers establish the base-directory policy, not a single mandatory layout for every component.

## System paths

XDG paths apply to per-user application files. System installation and runtime configuration remain separate. Typical Linux locations include `/opt/openroadcode` and `/etc/openroadcode`. On Termux, equivalent installation paths generally live under `$PREFIX`.

These are not automatically replaced by XDG user directories. Existing installation, service, and explicit configuration overrides remain separate from the per-user path policy.

## Existing data and explicit overrides

The XDG update changes default path resolution; it is not a general-purpose data migration tool. When an XDG variable is customized, a component may resolve to a different directory.

Before changing an established installation, inspect the relevant environment variables and application configuration. Preserve existing browser profiles, favorites, navigation datasets, and other durable data. Do not delete old directories until the application has been verified against the new location.

## Development and validation

The shared helper tests cover standard defaults, absolute environment overrides, and invalid relative overrides. Application and component tests should exercise their own path defaults and explicit overrides without writing to the developer's real home directory.

Run the focused tests from the repository root:

```bash
PYTHONPATH=. python -m unittest -v common.unit_test.test_xdg_paths
```

For a broader regression check:

```bash
PYTHONPATH=. python -m unittest discover -v
```

## Related documentation

- [Streaming Radio](streaming_radio.md)
- [Termux development target](../development/termux/README.md)
- [Project README](../README.md)
