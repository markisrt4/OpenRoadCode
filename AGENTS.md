# Repository instructions

## UI contracts are part of completing a feature

- Before wiring new UI behavior, define or extend toolkit-independent state and
  semantic request interfaces under `ui/`. Use immutable state and normalized SI
  values; frontends own display units and formatting.
- Widgets implement presentation contracts and emit requests through handler
  contracts. Do not call concrete controllers, providers, service clients, or
  transports from widgets. Do not inspect their private state.
- Controllers own business logic, workers, caching, retry, playback, and stale
  callback handling. Controllers must not import GUI frameworks or frontends.
- Composition roots construct dependencies, bind contracts, and own cleanup.
  Platform adapters may implement contracts for native rendering; keep transport
  and process access inside those adapters, outside widget code.
- Add meaningful contract and behavior tests alongside the feature, including
  hide/close and stale completion behavior when asynchronous work is involved.
  Update the affected documentation in the same change.
- Run `python scripts/quality_gate.py` before declaring a feature complete. It
  includes automatic project-wide dependency checks and stricter weather checks.
  New frontend files are discovered automatically.
- `scripts/ui_boundary_exceptions.json` records exact pre-existing dependencies,
  not permission for new ones. Do not regenerate, expand, or add exceptions merely
  to make CI pass. Fix new violations. When removing old dependencies, shrink the
  corresponding entries; the gate rejects stale entries. Any necessary adapter
  exception must have a specific architectural justification and be called out
  for review.
- Static checks enforce import direction, not every possible runtime interaction.
  Review contract use and lifecycle behavior as well; passing CI alone does not
  prove that all UI behavior follows contracts.

## Cloud development

Use the existing checkout in the task environment; do not create a worktree unless
requested. Preserve unrelated user changes. Use the repository-supported setup
and test commands. For device instructions, switch to the intended branch before
pulling or testing.

## Independently replaceable UI

The `openroad-ui-contracts` distribution must contain only `ui/`, with no ORC
runtime dependencies. Run `python scripts/check_standalone_ui.py` after changing
contracts. New UI packages import contracts and toolkit libraries; ORC-side
composition imports the new UI and supplies handlers/presenters. Do not require a
new frontend to import `apps.orcUi`, concrete controllers, configuration, messaging,
or native renderer clients. See `ui/README.md` for installation and the remaining
legacy boundary audit.
