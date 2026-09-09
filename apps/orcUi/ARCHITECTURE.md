# ORC UI Architecture

## Principles

OpenRoadCode separates contracts for behavior, CSS for presentation, and composition for ownership. The Tk shell must not construct transport, decoder, presenter, or external-process infrastructure. Feature composition wires existing application services to presentation adapters. Runtime objects own their resources and expose explicit lifecycle operations.

## Entry point and assembly

`python -m apps.orcUi` enters `main.py`, which calls `create_orc_ui_composition().run()`. The compatibility export of `OrcUiApp` remains available from `main.py`.

`composition/application.py` is the top-level composition root. It creates `OrcUiApplicationRuntime`, then `CoreComposition`, and configures RADIO, GAMES, and MEDIA. It returns `OrcUiComposition`, which owns the core, application runtime, and media composition.

```
main.py
  -> composition/application.py
       -> OrcUiApplicationRuntime
            -> application runtime manager
            -> radio and media application services
       -> composition/core.py
            -> MapRuntime
            -> OrcUiApp(map_runtime=...)
            -> StateIngressRuntime
       -> composition/radio.py
       -> composition/games.py
       -> composition/media.py
```

The application runtime owns background application services and managed launchers. The core composition owns the shell-facing map and state-ingress infrastructure. Feature composition owns feature-specific screen construction and wiring. Do not move concrete service construction back into `main.py` or `OrcUiApp`.

## Core shell and state flow

`OrcUiApp` owns the Tk window, shell chrome, structural HOME content, screen registration and navigation, theme switching, widget placement, and UI lifecycle. It consumes `MapRuntimeIf` and UI-ready presentation states. It does not create ZeroMQ subscribers, message decoders, presenters, or map-renderer launchers.

`core_runtime.py` contains the shell-facing runtime adapters. `MapRuntime` owns the external map-renderer launcher and supplies its display and parent-window arguments. `StateIngressRuntime` owns the message dispatcher and subscriber, registers automotive and navigation topic decoders, invokes the vehicle/navigation presenters, and schedules UI-ready state delivery onto the Tk thread.

```
ZeroMQ -> MessageDispatcher -> contract decoder -> presenter
                                                   |
                                                   v
                                           Tk scheduler
                                                   |
                                                   v
                              OrcUiApp.apply_*_state(...)
                                                   |
                                  visible structural panels
```

Vehicle, position, and attitude are distinct presentation states. The shell forwards them to the relevant context rail, vehicle, and off-road widgets. It must not decode transport payloads or couple position state to a particular GPS implementation. Background callbacks must not manipulate Tk widgets directly. Closing guards prevent queued work from updating destroyed widgets.

HOME, context rail, and other structural content are not required to become registered screens. Registered feature screens use the shell's screen-host and navigation interfaces. This distinction avoids inventing screen lifecycle machinery for every widget.

## Feature composition

`composition/radio.py` wires the radio screen, radio application service, and external SDR++ theme synchronization. The radio frontend owns Tk presentation and X11 embedding, while the application runtime owns managed process lifecycle. Theme changes must not unnecessarily restart or detach an active SDR++ session.

`composition/media.py` wires the shared Spotify service, local player, image cache, lyrics client, music-video controller, MEDIA hub, Spotify screen, browser-backed YouTube/Netflix screens, and HOME now-playing widget. `MediaComposition.close()` releases its owned video resource. The shared Spotify state service is not duplicated for HOME and MEDIA. See [`frontends/tk/media/README.md`](../../frontends/tk/media/README.md) for media-specific behavior.

`composition/games.py` registers the games frontend. The Games screen creates the runtime host and requests semantic launch/stop behavior. Platform launch adapters own environment-specific compatibility. In particular, Termux/proot renderer choices, environment overrides, and X11 title/class fallbacks live under `games.termux_proot` configuration and are consumed only by the Debian/proot backend. Native Debian does not inherit those compatibility settings. Shared X11 embedding remains generic and positions a successfully reparented client at the runtime-host origin.

New features should follow the same pattern: construct dependencies in composition, expose behavior through contracts, keep presentation in the frontend, and assign resource cleanup to the owner.

## Theme ownership

`theme_runtime.py` resolves the active `ThemeBundle` from the CSS files in `ui/theme`. CSS supplies the visual source of truth for shell and feature chrome. Components receive the active bundle or a provider and repaint when the theme changes. Do not introduce local dark/light palettes or translate old colors into new colors at runtime.

Intentional provider brand colors are separate from ORC chrome. Spotify actions and progress accents use Spotify green; the surrounding card, text, borders, and controls follow the active CSS theme. HOME now-playing receives the live theme provider rather than a fixed dark bundle.

Browser-backed media also passes the preferred color scheme to Chromium. A change of ORC mode relaunches the managed browser with the corresponding preference, preserving its dedicated profile while reloading the configured media URL. The website ultimately controls its own rendering; a browser preference is not a guarantee that every site will honor it. See [`frontends/tk/media/README.md`](../../frontends/tk/media/README.md) for media-specific behavior.

## Lifecycle and cleanup

`OrcUiComposition.run()` schedules deferred application startup, starts core state ingress, runs the Tk shell, and closes resources in nested `finally` blocks. Cleanup order is media, core, then application runtime. Core cleanup closes ingress before stopping the map renderer. The factory also closes already-created resources when assembly fails.

The shell owns UI restart signaling. Runtime resources must be closed before process replacement. Do not add independent shutdown paths or duplicate background startup loops inside feature screens. A resource should have one clear owner and an idempotent close/stop operation where appropriate.

## Developer workflow

From the repository root, use the active virtual environment and run:

```bash
python -m unittest discover -s apps/orcUi/composition/unit_test -p 'test_*.py'
python -m unittest discover -s apps/orcUi/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/application_runtime/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/games/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/x11/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/media/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/radio/unit_test -p 'test_*.py'
python -m apps.orcUi
```

The focused suites exercise assembly, ownership, state ingress, map adapter behavior, lifecycle failure cleanup, game backend isolation, X11 embedding geometry, and feature theme behavior. They do not replace an X11 integration test. On Termux, launch from the configured X11 session with the required broker, navigation, and external services available. Test HOME, NAVIGATION/map, VEHICLE, OFF-ROAD live state, MEDIA, browser color modes, RADIO embedding, GAMES embedding, theme transitions, and UI restart.

Before merging a substantial runtime refactor, review the complete branch diff for unrelated changes, run the focused suites, and perform the GUI smoke test. A passing mocked test is not proof that external processes or Tk/X11 integration work.

## Maintenance rules

Keep `main.py` as an entry point. Keep concrete dependency construction in composition or runtime factories. Keep transport and presentation conversions outside the shell. Keep theme values sourced from CSS, except deliberate brand accents. Preserve existing service ownership rather than constructing duplicate controllers. Add tests for lifecycle and state delivery when changing wiring. Update this document when ownership or assembly changes.