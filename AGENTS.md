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
- The user runs the full quality gate locally: `python scripts/quality_gate.py`.
  It includes automatic project-wide dependency checks and stricter weather
  checks; new frontend files are discovered automatically. Do not run the full
  gate or broad test suites unless the user explicitly asks. Report changes as
  awaiting user validation until the user supplies passing results.
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

## Keep agent usage economical

- Keep responses and progress updates brief. Summarize results instead of dumping
  logs, and read only the files and output needed for the task.
- Use focused checks when necessary to resolve a specific uncertainty or failure.
  Avoid repeating passing checks unless subsequent changes affect their coverage.
  For documentation-only changes, review the diff; do not run test suites.
- Continue adding meaningful tests for behavior changes, but leave their broad
  execution and the full quality gate to the user. Clearly distinguish checks
  actually run from checks still pending; never claim unrun tests passed.
- Provide the exact local validation command and any necessary device steps at
  handoff. When diagnosing user-run failures, request the failing check and relevant
  error excerpt rather than the entire log.
- Resolve material UI and workflow choices before substantial implementation.
  Apply routine fixes autonomously within the agreed scope.

## Discuss major changes before implementation

The user requires discussion and explicit agreement before major changes, including
architecture redesigns, separate packages or distributions, new dependencies,
build/install changes, public API changes, and substantial workflow changes.
Explain the proposed scope and consequences first, then wait for the user's
answer. Do not treat an unanswered preference question as authorization. Routine
fixes within an agreed scope can proceed. Apply this preference in every Codex
session working on this repository.
