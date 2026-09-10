# orcUi Architecture Audit

This temporary branch audits ownership boundaries without changing product behavior intentionally.

## Completed ownership corrections

- Host restart and poweroff no longer belong to `OrcUiApp`. They flow through the toolkit-independent `ui.system.SystemLifecycleRequestHandlerIf` contract to `SystemLifecycleController`, and host actions execute only after top-level cleanup.
- Map style installation no longer belongs to `OrcUiApp`. Theme intent is passed through `MapRuntimeIf.set_theme()`, and the map runtime owns renderer-specific style installation.
- Shell volume buttons no longer mutate prototype-local state. `OrcUiApp` implements `VolumeUiIf`, emits requests through the existing `VolumeRequestHandlerIf`, and `SystemVolumeHandler` bridges those semantic contracts to the audio controller.
- Long-lived Spotify state synchronization and reusable local Web Player lifecycle now live under `controllers/spotify`. Tk consumers import those controller-owned types directly. `apps/orcUi` retains only host-specific composition/factory wiring and no longer carries compatibility re-export modules for Spotify controller behavior.
- Icons are semantic UI data. `ui.icon.IconId` is toolkit-independent; each frontend maps those identifiers to its own SVG, CSS, native asset, Unicode glyph, or other rendering mechanism. Tk-specific glyph choices live under `frontends/tk`, not in shared UI contracts.
- Menu icon metadata now carries semantic icon identifiers instead of embedding Tk-oriented presentation in `ui/menu`.

## Contract audit rule

`ui/` is the toolkit-independent contract boundary. A contract belongs there only when it expresses semantic presentation state or user intent that can be consumed by every frontend without importing Tk, browser, transport, process, filesystem, controller, or hardware concepts.

Frontend-specific rendering belongs under `frontends/<frontend>`. Controller behavior belongs under `controllers`. Process/resource ownership belongs to the runtime or composition object that creates it.

## Remaining verification

- Review the final branch diff for accidental product behavior changes and stale compatibility code.
- Run focused unit tests plus repository quality checks.
- Run the Termux/X11 smoke test, including HOME, theme changes, volume, MEDIA/Spotify, RADIO, GAMES, map rendering, restart, and shutdown behavior.

No merge should occur until those verification gates pass.
