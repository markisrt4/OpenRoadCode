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

To launch one destination in the real Car UI shell:

```bash
venv/bin/python -m apps.carUi.test.screen_test_runner spotify
```

Supported destination arguments are `spotify`, `lighting`, `weather`,
`fm_radio`, `scanner`, `aircraft`, and `offroad_dashboard`.

The main-menu `Gauges` page includes the embedded off-road dashboard. Its IMU
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
