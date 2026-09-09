# orcUi Architecture Audit

This temporary branch audits ownership boundaries without changing product behavior intentionally.

## Current findings

- Host restart and poweroff were owned by `OrcUiApp`; they now flow through a toolkit-independent lifecycle request contract and execute only after top-level cleanup.
- Map style installation was invoked directly by `OrcUiApp`; it now belongs to `MapRuntime` behind `MapRuntimeIf.set_theme()`.
- The shell's volume buttons previously changed local prototype state only. `ui.system` already had the correct system-volume contracts, so the shell now consumes those contracts through a reusable controller-layer handler.
- `ui/` remains the toolkit-independent contract boundary. New contracts belong there only when they express semantic presentation state or user intent independent of Tk, controllers, transports, or hardware.

## Remaining audit targets

- Move long-lived Spotify state and local-player runtime behavior out of `apps/orcUi` into controller/service ownership.
- Review `apps/orcUi` for other backend, transport, process, filesystem, or worker ownership that belongs below composition.
- Review `ui/` for duplicate contracts, application-specific concepts, toolkit leakage, and contracts that encode implementation rather than semantic intent.
- Update `apps/orcUi/ARCHITECTURE.md` after ownership changes stabilize.

No merge should occur until focused unit tests, repository quality checks, and a Termux/X11 smoke test pass.
