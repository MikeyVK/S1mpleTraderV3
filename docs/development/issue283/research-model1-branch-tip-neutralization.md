<!-- docs\development\issue283\research-model1-branch-tip-neutralization.md -->
<!-- template=research version=manual created=2026-04-15T00:00Z updated=2026-04-15 -->
# Research — Model 1 branch-tip neutralization gap (Issue #283)

**Status:** FINAL  
**Version:** 2.0  
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
- Implementation cycle shapes (planning phase)

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

To satisfy the Model 1 invariant, the ready-commit must neutralize the branch tip against the
merge-base of HEAD and BASE. A single command handles both cases (path absent from or present
on the merge-base tree):

    git restore --source=<MERGE_BASE_SHA> --staged --worktree -- <path>

- Path **absent** from the merge-base tree → removed from index and working tree.
- Path **present** in the merge-base tree → index and working tree reset to merge-base version.

In both cases, `git diff --name-only MERGE_BASE(HEAD,BASE)..HEAD -- path` is empty after the
operation. No `git ls-tree` precondition check is needed; the merge-base variant eliminates
the two-branch conditional entirely. This logic is encapsulated in
`GitAdapter.neutralize_to_base(paths, base)` (see D1).

This is the operation that the ready-commit must perform instead of (not in addition to) the
`skip_paths` mechanism for the terminal-phase route.

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
2. Call `GitAdapter.neutralize_to_base(excluded_paths, resolved_base)` (see D1).
   One command per path: `git restore --source=<merge_base_sha> --staged --worktree -- path`.
   Handles both "absent from BASE" and "present on BASE" — no `git ls-tree` check needed.
3. Then commit with `files=None` and `skip_paths=frozenset()` (see D2c).
   The neutralization IS the commit content; staging is correct after step 2.

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

## Decisions

All open questions answered 2026-04-15 (user + architectural principles review).

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | `neutralize_to_base` in `GitAdapter` vs. direct calls | **Optie A — `GitAdapter.neutralize_to_base(paths, base)`** | All git subprocesses route through `GitAdapter` (§10 Cohesion). The per-path existence check is eliminated entirely: `git restore --source=MERGE_BASE --staged --worktree -- path` handles both "absent from base" (removes from index+worktree) and "present on base" (restores to base version) in one command. |
| 2 | Where does `git ls-tree BASE -- path` live? | **Eliminated** | The merge-base approach (V1) makes the per-path existence check unnecessary. `git restore --source=MERGE_BASE` is a single command that covers both cases without a precondition check. |
| 3 | `EnforcementRunner` injectie: `default_base_branch: str` vs. `GitConfig` | **`default_base_branch: str`** | §1.4 ISP: inject only what is used. §9 YAGNI: no abstraction for a concern with one implementation today. `EnforcementRunner` needs one scalar value, not the full config. |
| 4 | Commit message formaat neutralisatie-commit | **Optie C — vaste template, dynamische BASE** | `chore(P_READY): neutralize branch-local artifacts to '{resolved_base}'`. Scope (`P_READY`) maakt de commit herkenbaar in history. `resolved_base` is dynamisch. `params.message` van de caller wordt in de terminal-phase route genegeerd — de neutralisatie-commit heeft een vaste semantische betekenis. |
| 5 | Bestaande `skip_paths` tests bewaren of vervangen? | **Optie B + §14-correctie** | `test_git_adapter_skip_paths.py`: klasse `TestGitAdapterSkipPaths` (mock-ordering) verwijderen — architectuurschuld per §14 (test koppelt aan implementatiemechanisme, niet aan contract). Klasse `TestGitAdapterSkipPathsIntegration` (real-git, zero-delta bewijs) bewaren. Beide integratie-testbestanden (`test_git_add_commit_ready_phase_c3.py`, `test_git_add_commit_regression_c6.py`) worden vervangen door Model 1 contracttests. |

---

## Design

### D1 — `GitAdapter.neutralize_to_base(paths, base)`

**Bestand:** `mcp_server/adapters/git_adapter.py`

Nieuwe publieke methode naast de bestaande `restore()` en `commit()`:

```python
def neutralize_to_base(self, paths: frozenset[str], base: str) -> None:
    """Align each path in `paths` to the state at the merge-base of HEAD and `base`.

    Runs git merge-base HEAD <base> once, then for each path:
        git restore --source=<merge_base_sha> --staged --worktree -- <path>

    Behaviour per path:
    - Path absent in merge-base tree  → removed from index and working tree.
    - Path present in merge-base tree → index and working tree set to merge-base version.

    Postcondition: git diff --name-only <merge_base_sha>..HEAD -- <path>
    produces no output for any path in `paths`.

    Raises:
        ExecutionError: if git merge-base or git restore fails.
    """
    merge_base_result = _run_git_command(  # reuse existing helper pattern
        ...["merge-base", "HEAD", base]...
    )
    if merge_base_result.returncode != 0:
        raise ExecutionError(
            f"git merge-base failed for base='{base}': {merge_base_result.stderr.strip()}"
        )
    merge_base_sha = merge_base_result.stdout.strip()

    for path in paths:
        try:
            self.repo.git.restore(f"--source={merge_base_sha}", "--staged", "--worktree", "--", path)
        except Exception as e:
            raise ExecutionError(
                f"git restore --source={merge_base_sha} failed for '{path}': {e}"
            ) from e
```

**Noot:** `_run_git_command` is gedefinieerd in `enforcement_runner.py`, niet in `git_adapter.py`.
`GitAdapter` gebruikt `self.repo.git.*` (GitPython). De `merge-base` aanroep wordt via
`self.repo.git.execute(["git", "merge-base", "HEAD", base])` of `self.repo.git.merge_base("HEAD", base)`
aangeroepen — exacte aanroep conform bestaande patronen in `git_adapter.py`.

---

### D2 — `GitCommitInput` en `GitCommitTool.execute()`

**Bestand:** `mcp_server/tools/git_tools.py`

**D2a — `GitCommitInput`:** voeg één veld toe:

```python
base: str | None = Field(
    default=None,
    description=(
        "Target base branch for ready-phase neutralization. "
        "Resolved from state.json parent_branch when omitted, "
        "then falls back to git_config.default_base_branch."
    ),
)
```

**D2b — `GitCommitTool.execute()` — base resolutie:**

```python
# 3-tier base resolution (terminal-phase route only)
resolved_base: str = (
    params.base
    or (
        self._state_engine.get_state(current_branch).parent_branch
        if self._state_engine is not None
        else None
    )
    or self.manager.git_config.default_base_branch
)
```

**D2c — `GitCommitTool.execute()` — route-selectie:**

```python
excluded_paths = frozenset(n.file_path for n in ctx.of_type(ExclusionNote))

if excluded_paths:
    # Terminal-phase route: neutralize branch tip to merge-base, then commit.
    # params.message is intentionally ignored — the neutralization commit has
    # a fixed semantic meaning expressed in the generated message.
    self.manager.adapter.neutralize_to_base(excluded_paths, resolved_base)
    commit_hash = self.manager.commit_with_scope(
        workflow_phase=workflow_phase,
        message=f"neutralize branch-local artifacts to '{resolved_base}'",
        note_context=ctx,
        commit_type="chore",
        files=None,          # git add . — neutralized paths already staged correctly
        skip_paths=frozenset(),
    )
else:
    # Normal route: commit as requested.
    commit_hash = self.manager.commit_with_scope(
        workflow_phase=workflow_phase,
        message=params.message,
        note_context=ctx,
        sub_phase=params.sub_phase,
        cycle_number=params.cycle_number,
        commit_type=commit_type,
        files=params.files,
        skip_paths=frozenset(),
    )
```

**Toelichting `files=None` in terminal route:** na `neutralize_to_base` staan de
uitgesloten paden correct in de staging area (merge-base versie, of verwijderd).
`git add .` staged vervolgens alle overige werkdirectory-wijzigingen. Dit is het juiste
gedrag: de ready-commit is een complete snapshot-commit, niet een selectieve commit.

---

### D3 — `EnforcementRunner.__init__` + `_handle_check_merge_readiness`

**Bestand:** `mcp_server/managers/enforcement_runner.py`

**D3a — constructor:**

```python
def __init__(
    self,
    workspace_root: Path,
    config: EnforcementConfig,
    registry: EnforcementRegistry | dict[str, ActionHandler] | None = None,
    merge_readiness_context: MergeReadinessContext | None = None,
    default_base_branch: str = "main",  # injected from git_config at composition root
) -> None:
    ...
    self._default_base_branch = default_base_branch
```

**D3b — `_handle_check_merge_readiness` — base fallback:**

```python
# VOOR:
base = str(context.get_param("base") or "main")
# NA:
base = str(context.get_param("base") or self._default_base_branch)
```

**D3c — remediation messaging (Gap 4):**

```python
# VOOR (beschrijft skip_paths als fix):
note_context.produce(SuggestionNote(
    message="Commit first in the ready phase to auto-exclude them:"
))
note_context.produce(SuggestionNote(
    message='  git_add_or_commit(message="chore: prepare branch for PR")'
))

# NA (beschrijft Model 1 neutralisatie als fix):
note_context.produce(SuggestionNote(
    message=f"Run git_add_or_commit in phase '{ctx.pr_allowed_phase}' to neutralize these paths:"
))
note_context.produce(SuggestionNote(
    message=f'  git_add_or_commit(workflow_phase="{ctx.pr_allowed_phase}", message="...")'
))
note_context.produce(SuggestionNote(
    message=f"  This commit will align the branch tip to '{base}' for the excluded paths."
))
```

---

### D4 — `server.py` wiring

**Bestand:** `mcp_server/server.py`

```python
# VOOR:
self.enforcement_runner = EnforcementRunner(
    workspace_root=workspace_root,
    config=enforcement_config,
    merge_readiness_context=_merge_readiness_context,
)

# NA:
self.enforcement_runner = EnforcementRunner(
    workspace_root=workspace_root,
    config=enforcement_config,
    merge_readiness_context=_merge_readiness_context,
    default_base_branch=git_config.default_base_branch,
)
```

---

### D5 — Test strategie

**Verwijderen (architectuurschuld §14):**
- `TestGitAdapterSkipPaths` klasse in `test_git_adapter_skip_paths.py`  
  (mock-ordering tests: koppelen aan implementatiemechanisme, niet aan contract)

**Bewaren:**
- `TestGitAdapterSkipPathsIntegration` klasse in `test_git_adapter_skip_paths.py`  
  (real-git zero-delta bewijs — correct contract test)

**Vervangen:**
- `tests/mcp_server/integration/test_git_add_commit_ready_phase_c3.py` → verwijderen
- `tests/mcp_server/integration/test_git_add_commit_regression_c6.py` → verwijderen
- Vervangen door: `tests/mcp_server/integration/test_model1_branch_tip_neutralization.py`

**Toevoegen (GitAdapter unit):**
- `tests/mcp_server/unit/adapters/test_git_adapter_neutralize_to_base.py`  
  Real-git tests (geen mocks): bewijst dat `neutralize_to_base()` na afloop een leeg
  `git diff merge_base..HEAD -- path` oplevert voor zowel het "absent from base"- als
  het "present on base"-scenario.

---

## Test Contract

De volgende gedragingen moeten worden afgedekt in `test_model1_branch_tip_neutralization.py`:

**Scenario A — path absent from BASE (hoofd-scenario voor deze branch):**
1. Setup: branch commit voegt `.st3/state.json` toe (aanwezig in HEAD tree, afwezig op BASE).
2. `git_add_or_commit` aangeroepen in terminal phase (`workflow_phase="ready"`).
3. Assert: `git diff --name-only MERGE_BASE(HEAD,BASE)..HEAD -- .st3/state.json` is leeg.
4. Assert: `.st3/state.json` afwezig in HEAD tree na de neutralisatie-commit.
5. Assert: `create_pr` enforcement gate passeert (geen `ValidationError`).
6. Assert: commit history vóór de neutralisatie-commit bevat nog de werkversie.
7. Assert: commit message is `chore(P_READY): neutralize branch-local artifacts to '<BASE>'`.

**Scenario B — path present on BASE (epic-parent scenario):**
1. Setup: BASE heeft eigen versie van `.st3/state.json`; branch wijzigt die versie.
2. `git_add_or_commit` aangeroepen in terminal phase.
3. Assert: HEAD tree versie van `.st3/state.json` is gelijk aan BASE versie.
4. Assert: `git diff MERGE_BASE..HEAD -- .st3/state.json` is leeg.
5. Assert: `create_pr` gate passeert.

**Scenario C — geen ExclusionNotes (niet-terminal phase):**
1. `git_add_or_commit` in niet-terminal phase.
2. Assert: `neutralize_to_base` wordt NIET aangeroepen.
3. Assert: `params.message` wordt gebruikt als commit message.
4. Assert: `skip_paths=frozenset()` — geen `git restore --staged` aanroepen.

**GitAdapter unit (test_git_adapter_neutralize_to_base.py):**
1. `neutralize_to_base({path}, base)` op een real-git repo → `git diff merge_base..HEAD -- path` leeg.
2. Path absent from base → pad afwezig in worktree + index na aanroep.
3. Path present on base → worktree + index bevatten base-versie na aanroep.
4. Niet-nul exitcode van `git merge-base` → `ExecutionError` raised.

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
