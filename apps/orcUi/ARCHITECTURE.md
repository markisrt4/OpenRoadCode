# ORC UI Architecture

## Principles

OpenRoadCode separates contracts for behavior, CSS for presentation, and composition for ownership. The Tk shell must not construct transport, decoder, presenter, worker, browser, or external-process infrastructure. Feature composition wires application/controller services to presentation adapters. Runtime objects own their resources and expose explicit lifecycle operations.

`ui/` is the toolkit-independent semantic boundary. Contracts there describe user intent, presentation state, and semantic identifiers. They must remain consumable by Tk, web, Android, or another frontend without importing toolkit-specific rendering or backend implementation details.

## Entry point and assembly

`python -m apps.orcUi` enters `main.py`, which calls `create_orc_ui_composition().run()`. The compatibility export of `OrcUiApp` remains available from `main.py`.

`composition/application.py` is the top-level composition root. It creates `OrcUiApplicationRuntime`, then `CoreComposition`, and configures RADIO, GAMES, and MEDIA. `OrcUiComposition` owns those top-level objects and defines shutdown order.

```
main.py
  -> composition/application.py
       -> OrcUiApplicationRuntime
            -> application runtime manager
            -> radio and media application services
       -> composition/core.py
            -> MapRuntime
            -> SystemLifecycleController
            -> SystemVolumeHandler / audio controller
            -> OrcUiApp(semantic handlers + runtime interfaces)
            -> StateIngressRuntime
       -> composition/radio.py
       -> composition/games.py
       -> composition/media.py
```

The application runtime owns background application services and managed launchers. Core composition owns shell-facing map, system lifecycle, system volume, and state-ingress wiring. Feature composition owns feature-specific screen construction and wiring. Do not move concrete service construction back into `main.py` or `OrcUiApp`.

## Core shell and state flow

`OrcUiApp` owns the Tk window, shell chrome, structural HOME content, screen registration and navigation, theme intent, widget placement, and Tk lifecycle. It consumes runtime interfaces and UI contracts. It does not create ZeroMQ subscribers, message decoders, presenters, host lifecycle commands, audio backends, Spotify workers, browsers, or map-renderer launchers.

`core_runtime.py` contains shell-facing runtime adapters. `MapRuntime` owns the external map-renderer launcher and renderer-specific theme/style installation. `StateIngressRuntime` owns the message dispatcher and subscriber, registers automotive and navigation topic decoders, invokes the vehicle/navigation presenters, and schedules UI-ready state delivery onto the Tk thread.

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

## System intent contracts

System controls use semantic contracts from `ui.system` rather than direct platform operations.

Volume requests flow from the shell through `VolumeRequestHandlerIf`; normalized volume and mute state return through `VolumeUiIf`. `SystemVolumeHandler` owns the translation to the concrete audio controller. The shell therefore does not know about `wpctl`, PipeWire, PulseAudio, sinks, or platform commands.

Restart and poweroff requests flow through `SystemLifecycleRequestHandlerIf`. `SystemLifecycleController` records the requested action but does not execute it while Tk and feature resources are still alive. `OrcUiComposition.run()` closes application-owned resources first, then dispatches the deferred host action. This prevents process replacement from bypassing normal cleanup.

## Semantic icons

Shared UI models use `ui.icon.IconId`, not Unicode glyphs, SVG paths, image filenames, CSS classes, or Tk assets. An icon identifier describes meaning such as `POWER`, `CAMERA`, or `VOLUME_MUTED`; it does not prescribe rendering.

Each frontend owns the mapping from `IconId` to its native representation. Tk mappings live under `frontends/tk`; a web frontend may map the same identifier to SVG/CSS, and Android may map it to a native drawable. Menu metadata follows the same rule. This keeps icons digestible by every UI without forcing one frontend's presentation technology onto another.

## Feature composition

`composition/radio.py` wires the radio screen, radio application service, and external SDR++ theme synchronization. The radio frontend owns Tk presentation and X11 embedding, while the application runtime owns managed process lifecycle. Theme changes must not unnecessarily restart or detach an active SDR++ session.

`composition/media.py` wires the shared Spotify service, local player, image cache, lyrics client, music-video controller, MEDIA hub, Spotify screen, browser-backed YouTube/Netflix screens, and HOME now-playing widget. `MediaComposition.close()` releases its owned video resource. The shared Spotify state service is not duplicated for HOME and MEDIA.

Long-lived Spotify state synchronization and local Web Player behavior live under `controllers/spotify`, not `apps/orcUi`. Those components own command queues, worker threads, Spotify API coordination, browser-backed player lifecycle, playback transfer, and related state synchronization. ORC UI composition constructs/wires them; Tk consumes their presentation-facing state.

`composition/games.py` registers the games frontend. The Games screen creates the runtime host and requests semantic launch/stop behavior. Platform launch adapters own environment-specific compatibility. Termux/proot renderer choices, environment overrides, and X11 title/class fallbacks remain backend concerns rather than shell concerns.

New features should follow the same pattern: construct dependencies in composition, expose behavior through contracts, keep presentation in the frontend, and assign resource cleanup to the object that creates the resource.

## Theme ownership

`theme_runtime.py` resolves the active `ThemeBundle` from the CSS files in `ui/theme`. CSS supplies the visual source of truth for shell and feature chrome. Components receive the active bundle or a provider and repaint when the theme changes. Do not introduce local dark/light palettes or translate old colors into new colors at runtime.

`OrcUiApp` owns theme intent. Renderer-specific consequences do not belong in the shell. For example, the shell calls `MapRuntimeIf.set_theme()` and the map runtime performs MapLibre style installation. This same rule applies to future frontend/runtime-specific theme effects.

Intentional provider brand colors are separate from ORC chrome. Spotify actions and progress accents may use Spotify green; surrounding card, text, borders, and controls follow the active CSS theme.

## Lifecycle and cleanup

`OrcUiComposition.run()` schedules deferred application startup, starts core state ingress/system state, runs the Tk shell, and closes resources in nested `finally` blocks. Games are stopped before media, then core and application runtime are closed. Core cleanup closes ingress before stopping the map renderer. The factory also closes already-created resources when assembly fails.

Host restart/poweroff is deliberately deferred until normal cleanup completes. Do not add independent shutdown paths inside feature screens. A resource should have one clear owner and an idempotent close/stop operation where appropriate.

## Developer workflow

From the repository root, use the active virtual environment and run:

```bash
python -m unittest discover -s apps/orcUi/composition/unit_test -p 'test_*.py'
python -m unittest discover -s apps/orcUi/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/system/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/audio/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/spotify/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/application_runtime/unit_test -p 'test_*.py'
python -m unittest discover -s controllers/games/unit_test -p 'test_*.py'
python -m unittest discover -s ui/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/x11/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/media/unit_test -p 'test_*.py'
python -m unittest discover -s frontends/tk/radio/unit_test -p 'test_*.py'
python -m apps.orcUi
```

The focused suites exercise assembly, ownership, semantic contracts, state ingress, map adapter behavior, lifecycle failure cleanup, game backend isolation, X11 embedding geometry, icon mapping, and feature theme behavior. They do not replace an X11 integration test. On Termux, test HOME, NAVIGATION/map, VEHICLE, OFF-ROAD live state, MEDIA/Spotify, RADIO embedding, GAMES embedding, volume, theme transitions, UI restart, and shutdown.

Before merging a substantial runtime refactor, review the complete branch diff for unrelated changes, run the focused suites and repository quality checks, and perform the GUI smoke test. A passing mocked test is not proof that external processes or Tk/X11 integration work.

## Maintenance rules

Keep `main.py` as an entry point. Keep concrete dependency construction in composition or runtime factories. Keep transport and presentation conversions outside the shell. Keep shared icons semantic and frontend rendering local. Keep theme values sourced from CSS except deliberate brand accents. Preserve existing service ownership rather than constructing duplicate controllers. Add tests for lifecycle, state delivery, and contract wiring when changing ownership. Update this document when ownership or assembly changes.
