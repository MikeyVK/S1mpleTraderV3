<!-- docs\development\issue283\research-model1-branch-tip-neutralization.md -->
<!-- template=research version=manual created=2026-04-15T00:00Z updated= -->
# Research — Model 1 branch-tip neutralization gap (Issue #283)

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-15

---

## Purpose

Capture the verified post-C6 gap between the current implementation and the accepted Model 1 invariant. This document does NOT restate C1–C6; it focuses solely on what C1–C6 left unresolved.

## Scope

**In Scope:**
- Why `skip_paths` + `git restore --staged` does not satisfy the Model 1 invariant
- Verified git evidence from the active branch
- Exact code gaps with file/line references
- Base-branch resolution requirements
- Accepted product decision (Model 1 invariant, binding)

**Out of Scope:**
- Full C1–C6 design history (see `design-git-add-commit-regression-fix.md` v11.0)
- Any question already answered by C1–C6: `NoteContext`, `EnforcementRunner`, `BaseTool`, `skip_paths` primitive, `_has_net_diff_for_path`, config-boundary closure
- Implementation proposal or cycle shapes (design phase)

## Prerequisites

Read before starting design:
1. `docs/development/issue283/design-git-add-commit-regression-fix.md` v11.0 — full C1–C6 design baseline
2. `docs/development/issue283/SESSIE_OVERDRACHT_20260415_MODEL1_READY_PREP.md` — Model 1 decision record

---

## Background

C1–C6 is fully implemented. 2762 tests pass. All five original defects (A–E) are resolved per the design v11.0 specification. The `create_pr` gate now uses `_has_net_diff_for_path` (`git diff --name-only merge_base..HEAD -- path`) as its proxy.

Despite C6 being complete, `create_pr` is still blocked on this branch. The gate fires correctly — it is detecting a genuine invariant violation, not a false positive.

---

## Verified Gap — Design v11.0 Assumption Was Too Narrow

### The assumption in design v11.0

Design v11.0, Defect E correction:

> "A path can be tracked locally and yet never appear in any commit, because the `git restore --staged`
> postcondition (§3.8) removes it from staging before every commit. The proxy therefore blocks
> `create_pr` despite zero contamination risk."

This reasoning assumed that `git restore --staged` would prevent artifacts from appearing in the
`git diff --name-only merge_base..HEAD` output. It does — but only for paths that were **never
committed on the branch in any prior commit**.

On this active branch, `.st3/state.json` and `.st3/deliverables.json` appear in earlier commits
(before the ready-phase). `git restore --staged` removes a file's pending delta from the staging
area for the *current commit only*. The file remains in the branch's HEAD tree, inherited via the
parent commit chain. Once a file is in the tree, `git diff merge_base..HEAD` keeps finding it as
long as it differs from the merge-base.

### Live evidence (2026-04-15, branch `refactor/283-ready-phase-enforcement`)

```powershell
# merge-base confirmation
git ls-tree main -- .st3/state.json .st3/deliverables.json
# output: (empty — both files are absent from main)

# net diff confirms gate fires correctly
$mb = git merge-base HEAD main
git diff --name-only "$mb..HEAD" -- .st3/state.json .st3/deliverables.json
# output:
# .st3/deliverables.json
# .st3/state.json
```

Both artifacts are absent from `main`. Both appear in the branch tree (from earlier commits).
The `create_pr` gate is reporting a real invariant violation, not a false positive.

### Root cause of the gap

`skip_paths` + `git restore --staged` is a **commit-level exclusion**: it removes a path's
delta from the up-coming commit's staging area. It does not delete or roll back the path in
the HEAD tree.

The `create_pr` gate checks **branch-tip state vs. base**: does merging this branch into BASE
change BASE's state for this path? Because the path is in the HEAD tree and absent from BASE,
the answer is yes — the gate fires.

The two mechanisms address different layers and do not compose into the Model 1 invariant:

| Mechanism | Layer | Effect |
|-----------|-------|--------|
| `skip_paths` + `git restore --staged` | Staging area (index) | No delta in the current commit |
| `git diff --name-only merge_base..HEAD -- path` | Branch tree vs. merge-base | Path present in HEAD tree but absent from merge-base → non-empty |

---

## Accepted Product Decision — Model 1 (Binding)

**Decided: 2026-04-15. Source: `SESSIE_OVERDRACHT_20260415_MODEL1_READY_PREP.md`.**

> For every `artifact.path` in `MergeReadinessContext.branch_local_artifacts`:  
> After the ready-phase cleanup commit, merging the child branch into the base branch
> must not change the base's state for these paths.
>
> Concretely: `git diff --name-only MERGE_BASE(HEAD, BASE)..HEAD -- artifact.path`
> must be empty immediately after the ready-phase cleanup commit.

**Corollary (accepted):** the child branch may retain the full history of these files in its
commit log. The history is preserved. Only the branch-tip state is neutralized before PR merge.

This invariant is distinct from and stronger than "this path has no delta in the most recent
commit". `skip_paths` satisfies the weaker condition; Model 1 requires the stronger one.

---

## Required Operation — Branch-Tip Neutralization

To satisfy the Model 1 invariant, the ready-commit must explicitly align the branch tip to BASE
for each excluded path. The operation is determined by whether the path exists on BASE:

| Condition | Required operation | Result |
|-----------|-------------------|--------|
| `git ls-tree BASE -- path` empty (path absent from BASE) | `git rm -- path` | Path removed from tree; merge brings nothing |
| `git ls-tree BASE -- path` non-empty (path present on BASE) | `git restore --source=BASE --staged --worktree -- path` | Path in tree equals BASE version; merge is a no-op |

After either operation, `git diff --name-only MERGE_BASE(HEAD,BASE)..HEAD -- path` is empty.

This is the operation that the ready-commit must perform instead of (not in addition to) the
`skip_paths` mechanism for the terminal-phase route.

`GitAdapter.restore(files, source)` is already the correct building block for the second case.
The first case (`git rm`) is not currently wrapped by `GitAdapter`.

---

## Code Gap Map

### Gap 1 — `GitCommitTool.execute()`: staging exclusion instead of branch-tip neutralization

**File/location:** `mcp_server/tools/git_tools.py`, `GitCommitTool.execute()`, lines ~352–361

**Current code:**
```python
excluded_paths = frozenset(n.file_path for n in ctx.of_type(ExclusionNote))
commit_hash = self.manager.commit_with_scope(
    ...
    skip_paths=excluded_paths,
)
```

**Gap:** when `ExclusionNote` entries are present (i.e., terminal-phase enforcement ran), the
tool performs staging exclusion. It must instead perform branch-tip neutralization:
1. Resolve `BASE` (see Gap 2).
2. For each excluded path: determine whether it exists on `BASE` via `git ls-tree BASE -- path`.
3. If absent from `BASE`: `git rm -- path`.
4. If present on `BASE`: `git restore --source=BASE --staged --worktree -- path`.
5. Then commit (no `skip_paths` for these paths — the neutralization IS the commit content).

**Trigger:** presence of `ExclusionNote` entries in `NoteContext` is the correct branch-point.
No additional phase detection is needed in `execute()`.

### Gap 2 — `GitCommitTool` has no base-branch resolution

**File/location:** `mcp_server/tools/git_tools.py`, `GitCommitInput` (~line 218), `GitCommitTool.execute()` (~line 312)

**Current state:** `GitCommitInput` has no `base` field. `GitCommitTool` has no base-branch logic.

**Required:** three-tier resolution chain in `execute()`:
1. `params.base` — explicit caller-provided override (requires adding `base: str | None` to `GitCommitInput`)
2. `_state_engine.get_state(current_branch).parent_branch` — from `BranchState` (already injected)
3. `self.manager.git_config.default_base_branch` — from `GitConfig`

This chain is consistent with `GetParentBranchTool` (lines ~692–710) and `CreatePRInput.apply_default_base_branch()`.

### Gap 3 — `EnforcementRunner.__init__` hardcodes `"main"` as base fallback

**File/location:** `mcp_server/managers/enforcement_runner.py`, `_handle_check_merge_readiness()`, line ~330:
```python
base = str(context.get_param("base") or "main")
```

**Gap:** if `default_base_branch` is not `"main"` (e.g., an epic-parent workflow), the merge-base
computation is wrong. `"main"` is not config-driven.

**Required:** inject `default_base_branch: str` into `EnforcementRunner.__init__` so the fallback
reads from `GitConfig`. `server.py` wires `git_config.default_base_branch` at construction.

### Gap 4 — `_handle_check_merge_readiness` remediation messaging refers to obsolete mechanism

**File/location:** `mcp_server/managers/enforcement_runner.py`, suggestion notes, lines ~358–368

**Current messages** describe `skip_paths` exclusion as the resolution:
> "Commit first in the ready phase to auto-exclude them"

**Gap:** the correct resolution under Model 1 is a branch-tip neutralization commit
(`git rm` or `git restore --source=BASE`), not staging exclusion. The suggestion notes
must direct the user to the correct operation.

---

## What Does NOT Change

The following C1–C6 elements are correct and must not be modified:

- `_has_net_diff_for_path` → `git diff --name-only merge_base..HEAD -- path` — correct gate proxy
- `NoteContext`, `ExclusionNote` signal, `EnforcementRunner.run()` public API — correct
- `EnforcementRunner._handle_exclude_branch_local_artifacts` writes `ExclusionNote` entries — correct
- `GitAdapter.commit(skip_paths=)` postcondition — correct as a generic primitive; continues to exist but is NOT used for excluded paths in the terminal-phase route
- Config-boundary closure (no raw `.st3/config/` paths in production) — implemented, do not reintroduce

---

## Open Questions (for design)

1. Should `GitAdapter` grow a `neutralize_to_base(paths, base)` method that handles both the
   `git rm` and `git restore --source=BASE` cases, or should `GitCommitTool` call existing
   `GitAdapter` methods directly?
2. Should `git ls-tree BASE -- path` (per-path existence check) live in `GitAdapter` or be
   an inline subprocess call in `GitCommitTool.execute()`?
3. Should `EnforcementRunner.__init__` receive `default_base_branch: str` or the full
   `GitConfig` object? The former is minimal; the latter opens the door to future config-aware
   enforcement without further injection.
4. What is the correct commit message format for the neutralization commit?
   (e.g., `chore(P_READY): neutralize branch-local artifacts to base`)
5. Are the existing `skip_paths` integration tests (`test_git_adapter_skip_paths.py`,
   `test_git_add_commit_regression_c6.py`) to be retained as coverage for the generic
   primitive, or replaced by Model 1 contract tests?

---

## Test Contract (binding — must appear in design)

The following behaviors must be covered by the new integration tests:

1. Setup: branch commits `.st3/state.json` / `.st3/deliverables.json` in one or more commits.
2. Ready-commit: `git_add_or_commit` in terminal phase.
3. Assert: `git diff --name-only MERGE_BASE(HEAD,BASE)..HEAD -- path` is empty for each excluded path.
4. Assert: `create_pr` is NOT blocked after the ready-commit.
5. Assert: commit history before the ready-commit still contains the working-state versions.
6. Assert (scenario: path absent from BASE): path is absent from HEAD tree after ready-commit.
7. Assert (scenario: path present on BASE): HEAD tree version of path equals BASE version.

---

## Related Documentation

- **[docs/development/issue283/design-git-add-commit-regression-fix.md][related-1]** — C1–C6 design (v11.0)
- **[docs/development/issue283/SESSIE_OVERDRACHT_20260415_MODEL1_READY_PREP.md][related-2]** — Model 1 decision record
- **[mcp_server/tools/git_tools.py][related-3]**
- **[mcp_server/managers/enforcement_runner.py][related-4]**
- **[mcp_server/adapters/git_adapter.py][related-5]**

<!-- Link definitions -->
[related-1]: docs/development/issue283/design-git-add-commit-regression-fix.md
[related-2]: docs/development/issue283/SESSIE_OVERDRACHT_20260415_MODEL1_READY_PREP.md
[related-3]: mcp_server/tools/git_tools.py
[related-4]: mcp_server/managers/enforcement_runner.py
[related-5]: mcp_server/adapters/git_adapter.py
