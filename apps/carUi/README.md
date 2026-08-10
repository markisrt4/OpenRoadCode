# Car UI Application

`apps/carUi` is the application-specific assembly for the OpenRoadCode vehicle
interface. Concrete Tk widgets live under `frontends/tk`; toolkit-independent
display and request contracts live under `ui`.

## Architecture

```text
main.py
  -> car_ui_startup.py          startup policy and dependency construction
  -> CarUiDependencies          ownership and cleanup
  -> CarUiFrontend              Tk shell, navigation, and event loop
       -> CarUiComposition      screens, presenters, managers, and input wiring
       -> CarUiScreenFactoryIf  frontend-specific screen construction
       -> car_ui_routes.py      application destinations
       -> car_ui_menu_catalog.py
```

The dependency direction is:

```text
apps/carUi -> frontends + ui + input_events + controllers + hardware_io
frontends  -> ui + input_events
controllers -> ui + input_events + hardware_io
```

`frontends` must not import `apps.carUi`, controllers, or hardware
implementations. Its input queue uses only neutral contracts from
`input_events`.

## Main components

- `car_ui_frontend.py` owns the window shell and implements `UiIf`,
  `UiEventHandlerIf`, `ScreenNavigatorIf`, and the Tk screen-host operations.
- `car_ui_composition.py` connects screens, presenters, managers, and inputs.
- `car_ui_frontend_if.py` defines the toolkit-neutral shell surface consumed by
  composition.
- `ui/menu/` owns toolkit-independent `MenuPage` and `MenuTile` models; the Tk
  menu renderer only decides how those models are displayed.
- `screens/car_ui_screen_factory_if.py` keeps concrete screen construction
  behind a replaceable frontend boundary.
- `car_ui_startup.py` selects concrete runtime dependencies and configures the
  branded startup splash.
- `car_ui_dependencies.py` owns constructed resources and performs idempotent,
  best-effort cleanup.
- `screens/` contains Car UI destinations. Screens receive narrow hosts and
  services rather than the complete application object.
- `runtime/` translates Car UI configuration into controllers, launchers, and
  hardware adapters.
- Root `config/runtime.toml` is the shared deployment profile used
  by both Car UI and Car TUI; its schema is documented in
  `config/README.md`.
- `frontends/common/input/` queues hardware-originated `InputEvent` values for
  delivery on the selected frontend's event-loop thread.
- `input_events/` owns the physical-input events and handler contract shared by
  adapters, controllers, frontend queues, and application composition.
- `radio/` coordinates application radio sessions with the generic radio UI
  contracts and reusable Tk radio frontend.
- `screens/offroad_dashboard_screen.py` hosts the reusable automotive panel,
  starts IMU navigation only while visible, and uses Car UI's existing position
  source rather than opening a second GPS connection.
- `screens/vehicle_gauges_screen.py` hosts the reusable vehicle gauge panel. It
  accepts an optional `VehicleStateSourceIf` and owns connection and polling
  only while that destination is visible.

Composition uses `UiDispatcherIf` for immediate and delayed event-loop work.
It does not call Tk's `after()` or access Tk widgets directly. The current
`TkCarUiScreenFactory` creates the Tk destinations; another frontend can supply
its own factory while retaining the application routes and composition logic.

## Resource ownership

`CarUiDependencies.close()` stops rotary encoders and active radio controllers,
closes configured keyboard readers, stops standalone pushbuttons, and then
closes lighting and position-source resources. Cleanup is idempotent and
continues if one resource reports an error.

Startup uses an ownership stack. If dependency construction fails partway
through, already-created resources are released in reverse construction order.

External companion applications such as SDR++, ADS-B dashboards, and weather
dashboards are controlled by their explicit launcher and system actions. A
normal UI window close does not indiscriminately terminate unrelated display
processes.

## UI contracts

Application composition consumes `CarUiFrontendIf`, `CarUiScreenFactoryIf`,
and `UiDispatcherIf`. Persistent shell panels implement `TopBarUiIf`,
`StatusUiIf`, and `VolumeUiIf`. Navigable destinations implement `ScreenUiIf`;
screens that present domain data additionally implement only the relevant
contract, such as `MediaUiIf` or `LightingUiIf`. The current implementations
use Tk, while these contracts allow another frontend to provide its own shell,
dispatcher, renderer, and screen factory.

Physical keyboard ownership is expressed through `KeyboardReaderIf`.
`KeyboardInputAdapter` translates normalized key names into the same input
pipeline used by rotary encoders and standalone pushbuttons.

## Run

From the repository root:

```bash
CARUI_SPLASH=0 \
CARUI_GEOMETRY=1024x600 \
CARUI_FULLSCREEN=0 \
venv/bin/python -m apps.carUi.main
```

An X11 display must be available through `DISPLAY` or `CARUI_DISPLAY`.

Car UI detects `linux-dev`, Raspberry Pi 4, and Raspberry Pi 5 deployments to
select platform services such as audio control. Override detection when needed:

```bash
OPENROAD_RUNTIME_TARGET=linux-dev venv/bin/python -m apps.carUi.main
```

The installer target should normally match this runtime target. Linux
development hosts use `pactl`; native Pi targets use PipeWire/WirePlumber and
`wpctl`. Spotify consumes the resulting media-volume contract and contains no
platform-specific command selection.

Browser-hosted media can use a different X display from radio and auxiliary
applications. Set `runtime.media_display` in `config/runtime.toml`, or override
it for one launch with `CARUI_MEDIA_DISPLAY`. When neither is set,
`linux-dev` follows the active `$DISPLAY` and Pi targets use
`runtime.remote_display`.

```bash
CARUI_MEDIA_DISPLAY=:2 venv/bin/python -m apps.carUi.main
```

Weather and ADS-B browser dashboards use `runtime.auxiliary_display`, which
defaults to `:0`. Override it for one launch when the dashboard belongs on a
different desktop:

```bash
CARUI_AUXILIARY_DISPLAY=:2 venv/bin/python -m apps.carUi.main
```

Only one auxiliary dashboard occupies a display at a time. Launching Weather
closes an open ADS-B browser window, and vice versa. Each kiosk provides a
Return control that closes the dashboard and restores the Car UI main menu.
When `auxiliary.weather_dashboard.preload` is enabled, CarUi starts the
Streamlit server and refreshes a persistent Open-Meteo snapshot in background
workers after normal startup completes. Streamlit reads the snapshot from
`~/.cache/openroadcode/weather`, renders cached data immediately, and falls
back to stale data if a later refresh fails.

### Position provider

Car UI uses gpsd by default. To use a browser on the same computer as the
position provider instead:

```bash
CARUI_POSITION_SOURCE=browser \
CARUI_SPLASH=0 \
venv/bin/python -m apps.carUi.main
```

When initialization completes, the terminal prints the browser page URL. Open
`http://localhost:8765/`, select **Share location**, and grant location
permission. See [runtime/README.md](runtime/README.md#browser-position-source)
for configuration, a simulated-position test, and remote-browser limitations.

The last valid fix is persisted by default and restored immediately on the
next startup. Restored coordinates are labeled as last-known data and are used
for initial display, weather lookup, and map centering—not live speed, course,
or movement. Configure this through `[position_cache]` in
`config/runtime.toml`; deployment overrides are available through
`CARUI_POSITION_CACHE`, `CARUI_POSITION_CACHE_DIRECTORY`, and
`CARUI_POSITION_CACHE_MAX_AGE_SECONDS`.

To launch one destination in the real Car UI shell:

```bash
venv/bin/python -m apps.carUi.test.screen_test_runner spotify
```

Supported destination arguments are `spotify`, `netflix`, `youtube`,
`lighting`, `weather`, `fm_radio`, `scanner`, `aircraft`,
`offroad_dashboard`, and `vehicle_gauges`.

The Spotify destination retains album-art backgrounds and accents, cached
artwork, synchronized lyrics, seek and volume controls, and optional YouTube
music-video playback. Netflix and YouTube remain separate browser-backed media
destinations on the Media menu.

The main-menu `Gauges` page includes the configurable vehicle cluster and
the embedded off-road dashboard. The vehicle screen displays disconnected
gauges until a `VehicleStateSourceIf` is supplied in Car UI dependencies. Its IMU
defaults can be overridden before launch:

```bash
CARUI_IMU_ADDRESS=0x68 \
CARUI_IMU_FILTER_TIME_CONSTANT=0.5 \
venv/bin/python -m apps.carUi.main
```

## Test

```bash
venv/bin/python scripts/run_tests.py unit
venv/bin/python scripts/run_tests.py integration
```

Hardware-related suites may require optional platform packages such as
`evdev`.

Position-source tests can be run independently:

```bash
venv/bin/python -m unittest \
  controllers.navigation.unit_test.test_browser_position_source \
  apps.carUi.unit_test.test_position_source_factory \
  apps.carUi.unit_test.test_position_status_presenter
```

## Documentation

The toolkit-independent contract guide is in [`ui/README.md`](../../ui/README.md),
and reusable frontend conventions are in
[`frontends/README.md`](../../frontends/README.md). Build and validate the API
reference from the repository root:

```bash
venv/bin/python scripts/check_doxygen_contracts.py
doxygen Doxyfile
```
