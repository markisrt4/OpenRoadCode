# orcUi Architecture

## Purpose

`apps/orcUi` is the application assembly and runtime layer for the integrated OpenRoadCode UI. It is not the Tk frontend itself.

OpenRoadCode deliberately separates semantic UI contracts, reusable behavior, frontend rendering, and application composition so that a feature can be presented by Tk, web, Android, or another frontend without moving its controller logic into the application shell.

## Dependency boundaries

`ui/` is the toolkit-independent semantic boundary. Contracts there describe user intent, presentation state, semantic identifiers, and narrow frontend-facing behavior. Code in `ui/` must not depend on Tkinter, application composition, transport implementations, controllers, or hardware implementations.

`controllers/` owns reusable behavior and integration logic. Long-lived workers, state synchronization, protocol behavior, playback coordination, and similar reusable behavior do not belong in `orcUi` or in a concrete frontend.

`frontends/<frontend>/` owns concrete presentation. For Tk specifically, `frontends/tk` is the reusable Tk ecosystem. Feature packages such as `frontends/tk/media`, `frontends/tk/radio`, `frontends/tk/automotive`, and `frontends/tk/games` should depend on narrow contracts rather than on one application shell.

`frontends/tk/orc_ui` is intentionally application-specific. It owns the integrated orcUi Tk root window, shell chrome, HOME layout, context rail, structural navigation/vehicle/off-road panels, power dialog, and other Tk presentation that exists specifically because of the orcUi layout.

`apps/orcUi` owns assembly, application-specific runtime adapters, presenters used by the assembly, and resource lifecycle. Composition may select a concrete frontend implementation, but Tk widgets and Tk-specific rendering do not belong in this package.

The intended direction is:

```text
ui contracts
    ↑
controllers / reusable application services
    ↑
frontend implementations
    ↑
application composition
```

A concrete composition root is allowed to know which frontend it selected. Reusable controllers and UI contracts must not know which application or frontend selected them.

## Entry point and assembly

`python -m apps.orcUi` enters `main.py`, which does one thing: create the application composition and run it. It does not re-export the concrete Tk shell.

```text
apps/orcUi/main.py
  -> composition/application.py
       -> OrcUiApplicationRuntime
       -> composition/core.py
            -> MapRuntime
            -> SystemLifecycleController
            -> SystemVolumeHandler
            -> frontends/tk/orc_ui/OrcUiApp
            -> StateIngressRuntime
       -> composition/radio.py
            -> reusable Tk radio presentation
       -> composition/games.py
            -> reusable Tk games presentation
       -> composition/media.py
            -> reusable Tk media presentation
```

`OrcUiComposition` owns the top-level graph and shutdown order. Application/runtime objects own the resources they create. The Tk shell consumes injected runtime interfaces and semantic contracts rather than constructing backend infrastructure itself.

## Tk shell ownership

`frontends/tk/orc_ui/orc_ui_app.py` owns the concrete integrated Tk shell. It creates the Tk root, arranges shell chrome and structural panels, manages Tk screen hosting/navigation, paints presentation state, and runs the Tk event loop.

It must not create ZeroMQ subscribers, message decoders, audio backends, Spotify synchronization workers, browser lifecycle managers, external map renderer launchers, or host restart/poweroff implementations. Those dependencies are injected through application/runtime or UI contracts.

Structural orcUi widgets that are meaningful only inside that shell stay under `frontends/tk/orc_ui`. A widget that could reasonably be reused by another Tk application belongs in an appropriate feature package under `frontends/tk` instead.

## Reusing Tk for another application

`frontends/tk` is not uniquely tailored to orcUi. A future independent Tk application should create its own application-specific package, for example:

```text
frontends/tk/
    automotive/
    media/
    radio/
    games/
    ... reusable Tk features ...

    orc_ui/
        orc_ui_app.py
        ... orcUi-specific layout ...

    alternate_ui/
        alternate_ui_app.py
        ... alternate layout ...
```

That alternate shell can reuse the existing controllers, `ui/` contracts, and generic Tk feature packages. Reusable Tk screens use `TkScreenHostIf`, so another Tk shell can host them by implementing that narrow interface rather than inheriting from or depending on `OrcUiApp`.

If a generic Tk component begins importing `frontends.tk.orc_ui`, that is an architecture smell. Extract the required operation into a narrow contract rather than coupling the reusable component to the orcUi shell.

## State flow

`core_runtime.py` contains shell-facing runtime adapters. `MapRuntime` owns the external map-renderer lifecycle and renderer-specific theme consequences. `StateIngressRuntime` owns message ingress, decoders, presenter invocation, and scheduling already-presented state onto the UI thread.

```text
transport -> decoder -> presenter -> UI-thread scheduler -> concrete frontend
```

Vehicle, position, and attitude remain distinct presentation states. Concrete frontend widgets receive those already-presented states. They do not decode transport payloads or assume a particular sensor implementation.

## System intent

System controls use semantic contracts from `ui.system`.

Volume requests flow through `VolumeRequestHandlerIf`; normalized volume/mute state returns through `VolumeUiIf`. `SystemVolumeHandler` translates those requests to the concrete audio controller.

Restart and poweroff requests flow through `SystemLifecycleRequestHandlerIf`. `SystemLifecycleController` records the requested action, and `OrcUiComposition` executes it only after normal resource cleanup.

## Feature composition

`composition/radio.py` wires application-owned radio services to reusable Tk radio presentation. X11/SDR++ presentation details live with the appropriate frontend/launcher implementation, while the runtime owns managed process lifetime.

`composition/media.py` wires shared Spotify services, local-player behavior, image/lyrics/video dependencies, and reusable Tk media screens. Spotify synchronization and local Web Player lifecycle remain under `controllers/spotify`.

`composition/games.py` registers the reusable Tk games frontend. Environment-specific launching and compatibility remain backend concerns.

New features should follow the same sequence: define semantic contracts, implement reusable behavior, implement presentation per frontend, then assemble concrete choices at the application composition edge.

## Theme ownership

`theme_runtime.py` resolves `ThemeBundle` values from the shared CSS-derived theme model. Concrete frontends paint those values. Runtime-specific consequences, such as installing a MapLibre style, belong to the runtime that owns that renderer rather than to the shell.

Semantic theme intent may originate from the active application shell. Provider-specific brand colors are allowed where intentional, but application chrome should continue to come from the shared theme model.

## Lifecycle

A resource has one clear owner. The object that creates a process, worker, subscriber, browser host, or other managed resource must expose and own its cleanup behavior.

`OrcUiComposition.run()` starts the assembled graph, runs the selected frontend, then closes games/media/core/application resources in defined order before executing any deferred host lifecycle action.

Do not add independent shutdown paths inside feature screens merely because reaching `subprocess` from a button is temptingly easy.

## Developer verification

From the repository root, run the focused suites relevant to the changed ownership:

```bash
python -m unittest discover -s apps/orcUi/composition/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/system/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/audio/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/spotify/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/application_runtime/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/games/unit_test -p 'test_*.py'
python -m unittest discover -s ui/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/orc_ui/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/media/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/radio/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/x11/unit_test -p 'test_*.py'
python -m apps.orcUi
```

These tests do not replace an X11 integration smoke test. On Termux/X11, exercise HOME, NAVIGATION/map, VEHICLE, OFF-ROAD state, MEDIA/Spotify, RADIO embedding, GAMES embedding, volume, theme changes, restart, and shutdown.

Before merging a substantial architecture change, review the complete branch diff for stale paths or accidental product behavior changes, run repository quality checks, and perform the GUI smoke test.

## Maintenance rules

- Keep `apps/orcUi/main.py` as a thin composition entry point.
- Keep concrete dependency construction in composition/runtime factories.
- Keep Tk rendering under `frontends/tk`.
- Keep orcUi-specific Tk layout under `frontends/tk/orc_ui`.
- Keep reusable Tk features independent of `OrcUiApp` and `frontends/tk/orc_ui`.
- Prefer `TkScreenHostIf` or another narrow contract when reusable Tk presentation needs host services.
- Keep transport decoding and backend resource ownership outside concrete frontend widgets.
- Keep shared icons semantic and frontend rendering local.
- Keep theme values sourced from the shared theme model except deliberate provider branding.
- Remove obsolete compatibility aliases when ownership changes instead of preserving architectural ambiguity indefinitely.
