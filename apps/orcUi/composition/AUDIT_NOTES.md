# orcUi Architecture Audit

This temporary branch audits ownership boundaries without changing product behavior intentionally.

## Completed ownership corrections

- Host restart and poweroff no longer belong to the Tk shell. They flow through the toolkit-independent `ui.system.SystemLifecycleRequestHandlerIf` contract to `SystemLifecycleController`, and host actions execute only after top-level cleanup.
- Map style installation no longer belongs to the Tk shell. Theme intent is passed through `MapRuntimeIf.set_theme()`, and the map runtime owns renderer-specific style installation.
- Shell volume buttons emit requests through `VolumeRequestHandlerIf`; `SystemVolumeHandler` bridges those semantic contracts to the audio controller and returns normalized state through `VolumeUiIf`.
- Long-lived Spotify state synchronization and reusable local Web Player lifecycle live under `controllers/spotify`. `apps/orcUi` retains application-specific composition/factory wiring rather than compatibility re-exports of controller behavior.
- Icons are semantic UI data. `ui.icon.IconId` is toolkit-independent; each frontend maps those identifiers to its native rendering.
- Menu icon metadata carries semantic identifiers instead of Tk-oriented presentation.
- The integrated orcUi Tk shell and its structural panels live under `apps/orcUi/frontend/tk`, because they are both Tk-specific and application-specific.
- `frontends/tk` is reserved for reusable Tk implementations and does not own orcUi-specific shell layout.
- Radio Tk presentation has moved to `frontends/tk/radio`; remaining app coupling there is tracked for follow-up cleanup.
- The obsolete app-local shifter gauge was removed in favor of the themed implementation under `frontends/tk/automotive`.
- Tk-specific orcUi shell tests live with `apps/orcUi/frontend/tk`.
- `apps/orcUi/main.py` is composition-only; the historical `OrcUiApp` export and `home_shell.py` compatibility alias were removed.
- Feature composition no longer imports `tkinter` merely to express widget factory types. The composition root selects the concrete Tk frontend without making Tk widget types part of the application assembly API.

## Boundary rules

`ui/` is the toolkit-independent contract boundary. A contract belongs there only when it expresses semantic presentation state or user intent that can be consumed by every frontend without importing Tk, browser, transport, process, filesystem, controller, or hardware concepts.

`frontends/tk` means reusable presentation implemented with Tk. It is not synonymous with `orcUi`. Reusable Tk screens should depend on `TkScreenHostIf` or other narrow contracts, not on `OrcUiApp`.

`apps/orcUi/frontend/tk` contains the concrete Tk implementation of the integrated orcUi shell and shell-specific layout. A future independent Tk UI should own its shell under its own `apps/<application>/frontend/tk` package and reuse the generic Tk feature packages.

Controller behavior belongs under `controllers`. Process/resource ownership belongs to the runtime or composition object that creates it. `apps/orcUi` is the application assembly/runtime layer and may select reusable frontend implementations at its composition edge.

## Remaining verification

- Review the final branch diff for accidental product behavior changes and stale imports.
- Run focused application, controller, UI-contract, and Tk frontend tests plus repository quality checks.
- Run the Termux/X11 smoke test, including HOME, theme changes, volume, MEDIA/Spotify, RADIO, GAMES, map rendering, restart, and shutdown behavior.

No merge should occur until those verification gates pass.
