# Branch and Linear issue lifecycle

## Policy

- **One Linear issue per feature/workstream.** Keep implementation steps and acceptance criteria as Markdown checkboxes in the issue description, not separate sub-issues.
- **Normal Git commands.** Branches need no Linear ID in their names; do not require a special branch creation script.
- **Multiple branches, one feature.** Record repository/branch links in the same Linear issue when work spans repositories.
- **Merge is not Done.** Merge triggers review and hardware/software verification. Mark Done only after acceptance criteria are met.
- **Research / Active / Superseded.** Classify experimental work and explicitly review superseded branches.
- **Never automatically delete branches with unmerged commits.** Require human approval for cleanup.
- **No duplicates.** Exact repository + branch identity is the reconciliation key. Ambiguous matches require review.

## Automation rollout

Phase 1: The GitHub Actions workflow `.github/workflows/branch-lifecycle.yml` runs on branch creation, pull requests, and a weekly schedule. It reports branches already included in the default branch and flags unmerged branches. It never deletes code or changes Linear issues.

Phase 2 (implemented, pending validation): The `linear-reconcile.yml` workflow uses the repository Actions secret `LINEAR_API_KEY` to match branches to existing Linear issues by exact `owner/repository:branch` reference, then by unique normalized title. For unmatched `feature/`, `fix/`, `research/`, and `experiment/` branches it creates one feature issue with a checklist. Ambiguous matches are flagged without creating issues. PR URLs are appended to the associated issue; merges never automatically mark issues Done. The workflow only becomes active once merged into the default branch. GitHub Actions secrets are never committed.

Phase 3 (pending): Add verification-state transitions and multi-repository reusable workflow callers. Do not auto-check acceptance checkboxes based on commit messages.

## Issue description template

### Goal
Describe the feature's user-visible outcome.

### Repositories and branches
- `owner/repository:branch`

### Implementation checklist
- [ ] Implement functionality
- [ ] Add or update tests
- [ ] Validate on target hardware

### Acceptance criteria
- [ ] Tests confirmed green
- [ ] Hardware / integration behavior verified
- [ ] Documentation updated

### Notes
Record architectural decisions and links to pull requests.

## Historical sub-issues

When consolidating existing subtasks, first copy their scope, completion state, and issue links into the parent description. Close redundant children only after confirming that no unique information has been lost.
