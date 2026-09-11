# ORC UI Architecture

## Principles

OpenRoadCode separates contracts for behavior, CSS for presentation, and composition for ownership. The Tk shell must not construct transport, decoder, presenter, or external-process infrastructure. Feature composition wires existing application services to presentation adapters. Runtime objects own their resources and expose explicit lifecycle operations.

## Entry point and assembly

`python -m apps.orcUi` enters `main.py`, which calls `create_orc_ui_composition().run()`. The compatibility export of `OrcUiApp` remains available from `main.py`.

`composition/application.py` is the top-level composition root. It creates `OrcUiApplicationRuntime`, then `CoreComposition`, and configures RADIO, GAMES, and MEDIA. It returns `OrcUiComposition`, which owns the core, application runtime, and media composition.

```mermaid
flowchart TD
    main["main.py"] --> appComposition["composition/application.py"]
    appComposition --> runtime["OrcUiApplicationRuntime"]
    runtime --> manager["Application runtime manager"]
    runtime --> services["Radio + media application services"]
    appComposition --> core["composition/core.py"]
    core --> map["MapRuntime"]
    core --> app["OrcUiApp(map_runtime=...)"]
    core --> ingress["StateIngressRuntime"]
    appComposition --> radio["composition/radio.py"]
    appComposition --> games["composition/games.py"]
    appComposition --> media["composition/media.py"]

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcService fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;
    class main,appComposition,app,radio,games,media orcApp;
    class runtime,manager,services,core,ingress orcService;
    class map orcController;
```mermaid
flowchart LR
    zmq["ZeroMQ"] --> dispatcher["MessageDispatcher"] --> decoder["Contract decoder"] --> presenter["Presenter"]
    presenter --> scheduler["Tk scheduler"] --> app["OrcUiApp.apply_*_state(...)"] --> panels["Visible structural panels"]

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcService fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;
    class zmq,dispatcher,decoder orcMessage;
    class presenter orcController;
    class scheduler,app,panels orcApp;
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