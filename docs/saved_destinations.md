# Home and Work destinations

The navigation installer offers optional Home/Work setup after installing the
navigation stack. Run it as the same user who runs ORC, without sudo. With the
ORC Python environment active, setup can also be run from the repository root:

```bash
git switch orc-ui-polish
python -m scripts.installers.setup_destinations
```

Enter a full address, select the correct match from the existing offline search
database, and confirm the address and coordinates. Setup never silently chooses
the first result. If address data is missing or incompatible, enter latitude and
longitude in degrees instead. No online geocoding service or new dependency is
introduced; setup uses the existing whiptail toolkit.

Canceling input, selection, or confirmation abandons that destination draft.
Each confirmed destination is saved independently; leaving the outer menu keeps
destinations already confirmed in that session. Skipping setup changes nothing.

Home and Work open popups in Navigation with the address, Navigate, and Close.
Opening a popup does not start a route. Old searches and popups are cleared first.
Leave and reopen Navigation, or restart ORC, after changing addresses externally.

## Storage and compatibility

The file is `$XDG_CONFIG_HOME/openroadcode/destinations.toml`, defaulting to
`~/.config/openroadcode/destinations.toml`. Installed `navigation.toml` remains
runtime policy. Do not commit actual addresses.

```toml
version = 1

[home]
label = "Home"
address = "123 Example Street, Exampletown"
latitude_rad = 0.5
longitude_rad = -1.0
```

An optional `[work]` table uses the same fields. Stored coordinates are radians;
the installer accepts and displays degrees. Text has normalized whitespace.
Coordinates must be finite and within geographic bounds. Updates validate the
existing file, preserve the other destination, and atomically replace it with
mode 0600. Malformed or unsupported files are never overwritten by setup.

TOML takes precedence for each configured Home/Work entry. Missing entries fall
back to existing JSON favorites; arbitrary favorites continue using JSON. Invalid
or unreadable TOML logs a warning and falls back to legacy favorites. There is no
destructive migration. Default backend Home/Work setters also write TOML; injected
JSON-only stores retain their behavior.

Setup accepts `--config PATH` and `--search-db PATH` overrides. Otherwise it uses
the shared navigation data resolver, including `OPENROADCODE_DATA_ROOT` and
Linux/Termux defaults.

## Contracts and validation

`SavedDestination` and `DestinationSetupRequestHandlerIf` under `ui/navigation`
define immutable SI values and current/search/save requests.
`DestinationSetupUiIf` describes terminal presentation. The TUI uses only these
contracts; the controller owns search, the config module owns storage, and the
installer composition root constructs the whiptail adapter and closes the
geocoder. MapFavorite and PointOfInterest carry optional address text. Navigation
uses the existing POI popup and route request contracts without reading TOML.

Focused checks:

```bash
git switch orc-ui-polish
python -m unittest -q \
  config.unit_test.test_saved_destinations \
  controllers.navigation.unit_test.test_destination_setup_controller \
  controllers.navigation.unit_test.test_saved_destination_favorites \
  frontends.tui.unit_test.test_destination_setup \
  scripts.installers.unit_test.test_setup_destinations \
  apps.orcUi.frontend.tk.unit_test.test_saved_destination_controls
```

The existing NavigationPanel test was also updated. With UI dependencies available:

```bash
git switch orc-ui-polish
python -m pytest -q apps/orcUi/frontend/tk/unit_test/test_navigation_panel.py
```

On the device, configure both destinations, reopen Navigation, and verify their
popup addresses. Close without routing, then use Navigate. Cancel an edit and
verify the previous destination remains available. The user runs the full quality
gate separately.
