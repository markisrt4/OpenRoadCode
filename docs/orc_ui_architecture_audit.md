# ORC architecture audit — current master

Audited **only GitHub `master` at `1e75a6ad9b8a2f459fb9a7d0d31c817ca15a35ff`**,
the merge of PR #30 (`weather-radar`). GitHub returned this SHA before and after
the audit on 2026-10-05. This supersedes the earlier local `work` checkout audit.

Master has substantially cleaner contracts and ownership than the previous
checkout. Its static UI gates pass, but confirmed behavior/ownership defects and
documented legacy coupling remain. It cannot be certified as contract-clean.

## Scope and source verification

Git network access was unavailable. The GitHub connector supplied the exact
master tree; **all 1,804 tracked file contents** in `/workspace/orc-master-audit`
were checked against their Git blob hashes. Local objects were reused only when
their hashes matched master. No feature-branch-only or uncommitted files were
included. The original working checkout was preserved.

The structural scan covered **971 production Python files** across apps,
controllers, frontends, ui, common, config, services, messaging, protocols,
hardware_io, input_events, networking, and security. Tests/generated/deprecated
directories were excluded. Nested and relative imports were included. One legacy
file, `hardware_io/potentiometer/MultiTurnPot.py:17`, could not be parsed because
of inconsistent indentation; it is already excluded from Ruff. The other 970
were parsed.

Manual review focused on composition, lifecycle, UI contracts, Weather/radar,
navigation/routing, connectivity, media/radio/Games, extension seams, and gate
coverage. This is not line-by-line verification of every driver or C++ renderer.
References below refer to this pinned master tree.

## Findings

### 1. High: startup rollback and cleanup skip owned resources

**Confirmed with fault injection.**

- `apps/orcUi/composition/application.py:273`: a later factory failure closes
  places/radar/overlays/core/runtime, but not successfully created media, Games,
  or Weather compositions. Injecting a Weather startup failure confirmed that
  `media.close()` and `games.shutdown()` were never called.
- `apps/orcUi/composition/core.py:64`: connectivity close is outside the cleanup
  `try/finally` chain. If it raises, all subsequent core cleanup is skipped.
- `apps/orcUi/composition/weather.py:45`: screen-controller close failure skips
  radar tile HTTP service close.
- `apps/orcUi/application_runtime.py:44`: streaming-radio stop failure skips media
  and managed-application cleanup. These three cleanup failures were reproduced.
- `apps/orcUi/composition/core.py:112`: only shell construction is protected;
  later volume/ingress/publisher/trip construction failures do not unwind previous
  acquisitions. Earlier resource creation also precedes that protected block.

Normal-run cleanup already uses nested `finally` blocks for many resources, but
the guarantee is inconsistent. Failed startup/shutdown can leave sockets, workers,
or processes alive.

Recommendation: register cleanup after each successful acquisition, unwind the
entire graph on failure, and attempt every close even when another fails. Use
ExitStack or equivalent explicit ownership. Add failure tests at acquisition and
cleanup boundaries. Provide a public idempotent shell shutdown operation: core
cleanup currently does not explicitly destroy Tk when startup fails before
`app.run()`'s cleanup executes.

### 2. High: dispatcher contract and worker-to-Tk handoff are incomplete

`ui/ui_dispatcher_if.py` requires `dispatch_ui`, scheduling, and cancellation.
Composition passes OrcUiApp to Weather controllers and TooltipFactory as that
dispatcher, but **OrcUiApp has no `dispatch_ui` method**. Current consumers mainly
use scheduling, so the missing method is an extension/substitution failure rather
than proof of a current call-site crash.

`apps/orcUi/frontend/tk/orc_ui_app.py:205` calls Tk `after` directly. Workers reach
it from `controllers/weather/weather_screen_controller.py:89`, city/model/route
weather controllers, `controllers/weather/radar_replay_controller.py:325`, and
`frontends/tk/games/games_screen.py:65` plus embedding completions.

Generation checks reject stale callback bodies, but do not protect the scheduling
call itself. The forecast worker schedules even after close. Cross-thread Tk
requests may block or raise when the event loop is starting/stopping. These paths
were confirmed in code; a live Tk shutdown race was not reproduced.

Recommendation: implement thread-safe queue-backed `dispatch_ui`, drain only on
the frontend thread, and document timer scheduling's caller requirements. Use it
for worker results and reject submissions after shutdown. StateIngressRuntime
already demonstrates this queue pattern. Test contract substitution and late work.

### 3. Medium: route interface promises unsupported or ignored behavior

`controllers/navigation/navigation_route_request_handler.py` implements the full
RouteRequestHandlerIf, but non-empty waypoint requests, alternative selection,
and explicit recalculation raise NotImplementedError. At line 103, voice mute
discards its argument. Waypoint editing changes local state unused by startup.

The unsupported operations and ignored mute were reproduced with injected
clients. Existing callers restricted to start/cancel need not hit these gaps.

Recommendation: implement the capabilities or split baseline routing from
waypoint/alternative/recalculation/voice capabilities. Let views discover support;
add behavioral contract tests instead of only checking ABC method presence.

### 4. Medium: screen-host back-action contract is silently ignored

`frontends/tk/tk_screen_host_if.py:48` promises to configure and show a back
action. `apps/orcUi/frontend/tk/orc_ui_app.py:198` discards it. Spotify and
BrowserMediaScreen supply feature callbacks.

Architecture documentation acknowledges the product choice, but primary
destination navigation does not implement an arbitrary back callback.

Recommendation: expose a working shell back action or make it an optional
capability with a screen-owned fallback.

### 5. Medium: seven upward imports remain

| Master module | Application import | Gate treatment |
| --- | --- | --- |
| `controllers/navigation/google_earth_map_presentation.py:8` | `apps.launchers.google_earth_launcher` | Legacy exception |
| `controllers/video/netflix_player.py:11` | `apps.launchers.browser_launcher` | Legacy exception |
| `controllers/video/youtube_player.py:11` | `apps.launchers.browser_launcher` | Legacy exception |
| `frontends/tk/automotive/fuel_level_gauge.py:11` | `apps.common.uiTheme` | Not prohibited by frontend rule |
| `frontends/tk/automotive/vehicle_gauge_panel.py:18` | `apps.common.uiTheme` | Not prohibited by frontend rule |
| `frontends/tk/automotive/vehicle_gauge_theme.py:10` | `apps.common.uiTheme` | Not prohibited by frontend rule |
| `frontends/tk/automotive/vehicle_gauge_widgets.py:10` | `apps.common.uiTheme` | Not prohibited by frontend rule |

Their application-package placement reverses documented dependency direction.
Master moved launcher contracts and several shared value types into ui, but
automotive gauge themes remain application-owned.

Recommendation: inject platform launchers into controllers and relocate gauge
theme models/defaults to neutral contracts or reusable frontend ownership.
Remove migrated exceptions; do not expand the baseline to conceal coupling.

### 6. Medium: extension contracts do not cover actual consumers

GamesScreen constructs concrete GameLauncher, GameController, installers, and
catalog policy; composition injects only host/theme. This is recorded legacy debt.

The existing `controllers/games/game_launcher_if.py:12` declares only
`launch(game)`, stop, and is_running. GamesScreen calls
`launch(game, command, on_exit=...)` and reads process_id at lines 147–153.
Injecting that base interface alone would not supply the actual consumed API.

SpotifyScreen/BrowsePanel still depend on concrete SpotifyStateService and
SpotifyLocalPlayer; streaming-radio widgets depend on concrete controller/service
operations. Duck typing permits some replacement, but lacks stable narrow public
contracts for these consumers.

Recommendation: define the required game-process capability and inject it along
with catalog/installers/orchestration. Add narrow Spotify state/library/local
playback and radio state/request protocols. Reuse semantic request ABCs; avoid
one large base class. Native embedding belongs in explicit frontend adapters.

### 7. Medium: browser embedding can block the frontend loop

`frontends/tk/media/browser_media_screen.py:128` runs launch/embedding inside a
scheduled UI callback. Line 140 calls X11WindowEmbedder synchronously. That
adapter has an eight-second default timeout and polls with sleeps while finding
a window (`frontends/x11/x11_window_embedder.py:16`).

Slow/missing windows can stall the UI for the search interval. Scheduling a
callback defers execution but does not make it asynchronous. This finding is from
source inspection, not a measured GUI stall.

Recommendation: run launch/discovery in an owned worker/native adapter and return
completion through the thread-safe dispatcher. Keep Tk geometry/widget operations
on its thread and test hide/cancel during launch.

### 8. Medium: boundary checks still permit application coupling

The project gate correctly validates **588 modules with 53 exact legacy import
exceptions across 22 modules**, including count and stale-entry enforcement.

But `scripts/check_ui_boundaries.py:14` prohibits specific application runtime/
composition prefixes for frontends rather than apps generally. Its API accepts
both `from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl` and
`from apps.common.uiTheme import VehicleGaugeTheme` in a reusable frontend. Both
were reproduced. The four automotive imports therefore have no baseline entries.

Also, `apps/orcUi/composition/media.py:257` accesses the shell's private
`_active_screen`. Import checks cannot establish behavior/protocol compliance,
and permissive Mock collaborators can hide missing methods.

Recommendation: prohibit reusable frontend imports from apps with narrowly
justified adapter treatment; expose public active-screen/navigation state;
add strict contract and ownership failure tests. Preserve the existing baseline
ratchet. Passing the gate means no violations beyond its policy and baseline,
not zero architectural debt.

## Earlier findings that are fixed or inapplicable on master

- WeatherScreen no longer calls WeatherController or owns refresh workers;
  WeatherScreenController owns them through state/request contracts.
- OrcUiApp no longer constructs network monitors or internet probe workers.
  Core supplies OnlineModeIf and owns ShellConnectivityController.
- Shared launcher contracts live in ui.system. AppRuntimeManager no longer imports
  its interface from apps.launchers.
- AndroidPoiActionExecutor requires an injected platform launcher.
- MapRuntimeIf lives in ui.navigation; views no longer obtain it from core_runtime.
- tinycss2 is now explicitly allowed and documented for theme parsing.
- Project-wide and Weather-specific import gates exist and run in CI.

## Sound boundaries and existing interfaces

No direct upward app/frontend imports were found in ui, common, input_events,
messaging, protocols, or hardware_io. Reusable frontends currently do not directly
import apps.orcUi. UI remains independent of GUI toolkits.

Existing useful interfaces include ScreenUiIf/TkScreen/TkScreenHostIf, Weather
screen/state/request/control interfaces, radar interfaces, NavigationPlaces
factory/session interfaces, tooltip interfaces, OnlineModeIf, MapRuntimeIf,
shared launcher protocols, and volume/system lifecycle contracts. Weather
snapshots are immutable and use SI. These are good foundations for further work.

Cross-domain public value imports and hardware/backend construction in composition
are not violations merely because they cross folders. Correct dependency direction
and ownership matter more than eliminating every cross-directory import.

## Validation

- All 1,804 tracked source files match the verified master tree.
- Ruff, module-size, project/Weather UI boundaries, Doxygen, Mermaid: passed.
  Doxygen validated 524 public interface methods.
- Focused UI/composition/Weather/system/audio/Games/Spotify/application-runtime/
  connectivity/navigation/POI/input suites: **629 passed, 37 subtests passed**;
  four socket-dependent cases deselected and three test files excluded.
- Boundary checker regressions: **9 passed**.
- A preceding focused run had 585 passes and 12 failures, all denied local HTTP
  socket creation. Those unavailable socket tests were then excluded.
- Full quality gate was attempted. Its static checks passed; tests aborted inside
  native ZeroMQ binding in the weather-city source integration test under the
  restricted sandbox. Earlier failures were present and the abort prevented a
  complete summary. **The full suite is not claimed to pass.**
- Temporary fault-injection probes confirmed findings 1, 3, 4, 8 and the missing
  dispatcher method. They did not start real Tk/hardware/backend processes.
- No live X11/Termux, provider-network, hardware, or C++ renderer checks were run.

Focused validation command, from the pinned master tree with dependencies installed:

```bash
XDG_CACHE_HOME=/tmp/orc-master-test/cache \
XDG_CONFIG_HOME=/tmp/orc-master-test/config \
XDG_DATA_HOME=/tmp/orc-master-test/data \
python -m pytest \
  ui/unit_test apps/orcUi frontends/tk frontends/common/input \
  controllers/weather/unit_test controllers/system/unit_test \
  controllers/audio/unit_test controllers/games/unit_test \
  controllers/spotify/unit_test controllers/application_runtime/unit_test \
  controllers/connectivity/unit_test controllers/navigation/unit_test \
  controllers/poi/unit_test controllers/input/unit_test \
  --ignore=apps/orcUi/unit_test/test_music_visualizer_browser.py \
  --ignore=controllers/weather/unit_test/test_radar_tile_service.py \
  --ignore=controllers/navigation/unit_test/test_browser_position_source.py \
  -k 'not test_termux_browser_defaults_to_android_playback_without_starting_capture and not test_explicit_browser_source_choice_is_preserved_on_termux and not test_same_timestamp_from_different_sources_has_separate_tiles and not test_hrrr_tiles_flow_through_local_cache_and_classic_palette' \
  -q --tb=short
```

## Remediation order

1. Fix startup rollback and exception-safe cleanup, with failure tests.
2. Complete the dispatcher contract and queue worker-to-frontend delivery.
3. Align route and back-navigation capabilities with actual behavior.
4. Migrate Games/media/radio coupling with narrow interfaces; remove the seven
   upward imports and strengthen app-import enforcement.
5. Remove UI-thread window waits and run full integration/device validation in
   an environment permitting sockets/displays.

This audit changes only the report. Major architecture/API migration requires
discussion and agreement as specified by master's AGENTS.md.
