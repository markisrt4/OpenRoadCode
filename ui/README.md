# UI Contracts

`ui` defines the toolkit-independent presentation contracts and value objects
shared by applications, controllers, and concrete frontends. Code in this
package must not import Tkinter, Qt, application composition, controllers, or
hardware implementations.

## Dependency boundary

```text
applications/controllers/frontends -> ui
ui                                 -> Python standard library
```

Interfaces use the `*UiIf` or `*RequestHandlerIf` suffix. A UI interface
describes data a view can display; a request-handler interface describes
semantic user intent emitted by that view. Implementations should inherit only
the narrow contracts required by the screen or panel they represent.

## Package map

- `automotive/` contains vehicle, trip, body, tire, connection, and diagnostics
  presentation contracts.
- `lighting/` contains complete lighting state and lighting request contracts.
- `media/` contains media state plus playback, track, seek, and volume requests.
- `menu/` contains toolkit-independent menu-page and menu-tile models.
- `navigation/` contains position, orientation, ground-track, translation,
  angular-velocity, map, turn-by-turn route, and lane-guidance contracts.

Map and routing contracts are provider-neutral. A future MapLibre frontend may
render `MapState`, while a Valhalla adapter may produce `RouteGeometry`,
`RouteGuidanceState`, and `LaneGuidance`; neither product API belongs in `ui`.
- `radio/` contains receiver state, presets, tuning, playback, and application
  radio requests.
- `system/` contains diagnostics, status, top-bar, and system-volume contracts.
- Root modules contain cross-cutting screen, navigation, focus, action,
  dispatcher, event-handler, and frontend lifecycle contracts.

## Screens and panels

A screen is a navigable destination and implements `ScreenUiIf`. A screen can
compose any number of panels. A panel is a non-navigable region within a screen
or persistent shell chrome. Domain screens additionally implement only the
data contract they need, such as `MediaUiIf` or `LightingUiIf`.

The contracts intentionally do not prescribe widget types, layout, threading,
or event-loop behavior. Those decisions belong to a concrete frontend.

Normalized physical-input contracts are intentionally not UI contracts. They
live under `input_events`; `UiAction` remains here because it represents
toolkit-independent semantic UI intent after controller mapping.

## Stubs

`*_stub.py` classes provide inert or state-recording implementations for demos,
tests, and unavailable integrations. They implement the same public contracts
but do not introduce toolkit dependencies.

## Documentation and tests

Public methods in `*_if.py` modules document each parameter and non-`None`
return value with Doxygen commands. From the repository root, run:

```bash
venv/bin/python scripts/check_doxygen_contracts.py
venv/bin/python -m unittest discover -s ui/unit_test -p 'test_*.py'
doxygen Doxyfile
```

Generated API documentation is written under `build/doxygen/html`.
