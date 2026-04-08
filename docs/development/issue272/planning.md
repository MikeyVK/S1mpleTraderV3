<!-- docs\development\issue272\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-08T19:37Z updated= -->
# Planning: ScopeDecoder wrong phase on child branches (#272)

**Status:** DRAFT  
**Version:** 1.3  
**Last Updated:** 2026-04-08

---

## Purpose

Fix a structural bug where `ScopeDecoder.detect_phase()` reports the parent-branch phase on
child branches, plus two preventive measures to avoid recurrence via merge contamination.

## Scope

**In Scope:**
- `mcp_server/core/phase_detection.py` — precedence inversion in `detect_phase()`
- `.gitattributes` — new file with `merge=ours` for `state.json`
- `mcp_server/tools/pr_tools.py` — restrict `MergePRInput.merge_method` pattern
- Related tests in:
  - `tests/mcp_server/core/test_phase_detection.py`
  - `tests/mcp_server/unit/tools/test_pr_tools.py`
  - `tests/mcp_server/unit/tools/test_github_extras.py`
  - `tests/mcp_server/unit/adapters/test_github_adapter.py`

**Out of Scope:**
- `git_adapter.py` `get_recent_commits()` — not the root cause, no change
- `state_reconstructor.py` — `fallback_to_state=False` path is unaffected by C1
- `get_state()` state reconstruction (issue #231)
- `phase_contracts` SSOT (issue #271)
- Local git rebase or cherry-pick operations
- Fixing main's contaminated `state.json` (no-op: `initialize_project` overwrites it)

## Prerequisites

1. Research approved (`docs/development/issue272/research.md`, commit `82ce1299`)
2. `state.json` is tracked in git (`git ls-files .st3/state.json` confirmed)
3. `test_phase_detection.py` baseline: all existing tests green (confirmed via full suite 2657 passed)
4. Historical merge pattern: true merge only, except PR #277 (mistake in previous session)
---

## Summary

Three minimal, targeted fixes that resolve the root cause:

1. **C1 — Precedence inversion**: `detect_phase()` evaluates `state.json` before commit-scope.
   This fixes the core bug: on a fresh child branch the last commit is from the parent,
   carrying a `P_PHASE` scope. State.json holds the correct initialised phase.

2. **C2 — `merge_method` restriction**: `MergePRInput` only accepts `"merge"`.
   Squash merges bypass the `merge=ours` driver and rewrite commit history so that
   `get_recent_commits()` shows a different picture than the phase flow expects.

3. **C3 — `.gitattributes`**: `merge=ours` on `.st3/state.json` prevents merge commits
   from introducing the merge-partner's branch state.

---

## Dependencies

### Dependency Analysis — Parallel vs. Sequential

```
C1  (phase_detection.py)  ─────────────────────────►  independent
C2  (pr_tools.py)         ─────────────────────────►  independent, but requires updating 3 test files
C3  (.gitattributes)      ─────────────────────────►  independent of code
```

**Runtime logical dependencies:**

| From | To | Type        | Notes                                                                          |
|------|----|-------------|--------------------------------------------------------------------------------|
| C3   | C1 | Preventive  | C3 meaningful once state.json is authoritative (C1). Preferred order, no hard dep. |
| C2   | C3 | Preventive  | C2 disallows squash, preserving C3's `merge=ours` driver.                      |
| C1   | —  | Independent | No external code dependency                                                    |
| C2   | —  | Independent | Pydantic field change, no impact on C1/C3                                      |
| C3   | —  | Independent | Creating `.gitattributes` has no test impact                                   |

**Test dependencies (what breaks after C2 GREEN, before REFACTOR):**

| File                       | Line    | Reason                                         | Action in REFACTOR |
|----------------------------|---------|------------------------------------------------|--------------------|
| `test_pr_tools.py`         | 70, 74  | `merge_method="squash"` now invalid            | → `"merge"`        |
| `test_github_extras.py`    | 124,131 | `merge_method="squash"` now invalid            | → `"merge"`        |
| `test_github_adapter.py`   | 160     | assert expects `merge_method="squash"`         | → `"merge"`        |

**Recommended execution order:**

```
C1 → full test suite → C2 → full test suite → C3
```

Rationale:
- **C1 first**: fixes the core bug; all existing tests use `fallback_to_state=False`
  or absent scope — no regression expected from the inversion.
- **C2 next**: independent of C1. REFACTOR step updates three test files. Deliberately after C1
  so that any C1 regression is not masked by failing C2 tests.
- **C3 last**: no code test required, only `git check-attr` verification. No test run
  is affected; safest as the final step.

---

## TDD Cycles

### Cycle 1: Precedence inversion in `ScopeDecoder.detect_phase()`

**Goal:**  
`detect_phase()` evaluates `state.json` before commit-scope when `fallback_to_state=True`.
State.json holds the initialised phase of the current branch. A commit-scope on the parent
must not override the child phase.

**Affected files:**
- Implementation: `mcp_server/core/phase_detection.py` — method `detect_phase()` (~line 106–125)
- Test: `tests/mcp_server/core/test_phase_detection.py`

**Tests:**

*RED — new failing tests:*

```python
def test_detect_phase_state_json_wins_over_commit_scope(tmp_path):
    """state.json takes precedence over commit-scope (core of the bugfix)."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"current_phase": "planning", "workflow_name": "bug"}))
    decoder = ScopeDecoder(state_path=state_file)
    # commit_message carries a valid phase-scope (P_RESEARCH) — from parent branch
    commit_message = "docs(P_RESEARCH): finalize research doc"

    result = decoder.detect_phase(commit_message, fallback_to_state=True)

    # Expected: state.json wins (planning), NOT commit-scope (research)
    assert result["workflow_phase"] == "planning"
    assert result["source"] == "state.json"
    assert result["confidence"] == "medium"


def test_detect_phase_fallback_false_still_uses_commit_scope(tmp_path):
    """fallback_to_state=False uses commit-scope exclusively (state_reconstructor path)."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"current_phase": "planning", "workflow_name": "bug"}))
    decoder = ScopeDecoder(state_path=state_file)
    commit_message = "docs(P_RESEARCH): finalize research doc"

    result = decoder.detect_phase(commit_message, fallback_to_state=False)

    # fallback_to_state=False: commit-scope wins, state.json ignored
    assert result["workflow_phase"] == "research"
    assert result["source"] == "commit-scope"
```

*GREEN — minimal change in `detect_phase()`:*

Current order in `mcp_server/core/phase_detection.py`:
```python
# Try commit-scope first (PRIMARY for context tools)
if commit_message:
    scope_result = self._parse_commit_scope(commit_message)
    if scope_result:
        return scope_result
# Fallback to state.json (SECONDARY)
if fallback_to_state:
    state_result = self._read_state_json()
    if state_result:
        return state_result
```

New order (swap the two blocks):
```python
# PRIMARY: state.json (authoritative current branch state)
if fallback_to_state:
    state_result = self._read_state_json()
    if state_result:
        return state_result
# SECONDARY: commit-scope (used by state_reconstructor with fallback_to_state=False)
if commit_message:
    scope_result = self._parse_commit_scope(commit_message)
    if scope_result:
        return scope_result
```

Update docstring and class-level `Precedence:` comment.

*REFACTOR:*
- `run_quality_gates(scope="files", files=["mcp_server/core/phase_detection.py"])`
- Grep: confirm no other callers rely on the old order (state_reconstructor uses `fallback_to_state=False` — unchanged)

**Success Criteria:**
- New test `test_detect_phase_state_json_wins_over_commit_scope` passes
- New test `test_detect_phase_fallback_false_still_uses_commit_scope` passes
- All existing tests in `test_phase_detection.py` remain green
- `test_workflow_cycle_e2e.py` (uses `fallback_to_state=False` exclusively) remains green


### Cycle 2: Restrict `MergePRInput.merge_method` to `"merge"`

**Goal:**  
Prevent squash or rebase merges from being executed via the `merge_pr` tool. Squash merges
bypass the `merge=ours` driver and produce a single commit without a merge parent.
Rebase has no use case in this project.

**Affected files:**
- Implementation: `mcp_server/tools/pr_tools.py` — `MergePRInput.merge_method` (line 126)
- New tests: `tests/mcp_server/unit/tools/test_pr_tools.py`
- Files to update (REFACTOR): `test_pr_tools.py:70,74`, `test_github_extras.py:124,131`, `test_github_adapter.py:160`

**Tests:**

*RED — new failing tests (add to `test_pr_tools.py`):*

```python
def test_merge_pr_input_rejects_squash() -> None:
    """squash is no longer a valid merge_method."""
    with pytest.raises(ValidationError):
        MergePRInput(pr_number=1, merge_method="squash")


def test_merge_pr_input_rejects_rebase() -> None:
    """rebase is no longer a valid merge_method."""
    with pytest.raises(ValidationError):
        MergePRInput(pr_number=1, merge_method="rebase")
```

Both tests fail now: current pattern `^(merge|squash|rebase)$` allows squash and rebase.

*GREEN — minimal change in `mcp_server/tools/pr_tools.py` line 126:*

```python
# Old:
merge_method: str = Field(
    default="merge", description="Merge strategy", pattern="^(merge|squash|rebase)$"
)

# New:
merge_method: str = Field(
    default="merge",
    description="Merge strategy. Only true merge is supported to preserve git history and enable .gitattributes merge drivers.",
    pattern="^merge$",
)
```

*REFACTOR — update existing test files:*

| File                      | Line    | Old                                                     | New            |
|---------------------------|---------|---------------------------------------------------------|----------------|
| `test_pr_tools.py`        | 70      | `MergePRInput(pr_number=20, merge_method="squash")`     | `"merge"`      |
| `test_pr_tools.py`        | 74      | `merge_method="squash"`                                 | `"merge"`      |
| `test_github_extras.py`   | 124     | `MergePRInput(pr_number=8, merge_method="squash")`      | `"merge"`      |
| `test_github_extras.py`   | 131     | `merge_method="squash"`                                 | `"merge"`      |
| `test_github_adapter.py`  | 160     | `assert_called_once_with(..., merge_method="squash")`   | `"merge"`      |

Then: `run_quality_gates(scope="files", files=["mcp_server/tools/pr_tools.py"])`

**Success Criteria:**
- `test_merge_pr_input_rejects_squash` passes (ValidationError)
- `test_merge_pr_input_rejects_rebase` passes (ValidationError)
- `MergePRInput(pr_number=1, merge_method="merge")` — no error
- `MergePRInput(pr_number=1)` — no error (default `"merge"` is correct)
- All 5 updated existing tests pass


### Cycle 3: `.gitattributes` — `merge=ours` for `state.json`

**Goal:**  
Prevent `git merge` from introducing the merge-partner's `state.json` during a true merge.
With `merge=ours`, the target branch always retains its own version.

**Affected files:**
- Implementation: `.gitattributes` (new file in repo root)
- No unit test file: git merge-driver behaviour cannot be mocked at unit level

**Tests:**

No unit test applicable. Validation via CLI verification:
```
git check-attr merge .st3/state.json
# Before creating: .st3/state.json: merge: unspecified  ← "failing state"
# After creating:  .st3/state.json: merge: ours         ← "passing state"
```

*GREEN — create `.gitattributes`:*

```gitattributes
# Prevent state.json contamination during merges.
# Each branch retains its own workflow state on merge.
.st3/state.json merge=ours
```

*REFACTOR:*
- Verification: `git check-attr merge .st3/state.json` → `merge: ours`
- No quality gates applicable (no Python file)

**Success Criteria:**
- `git check-attr merge .st3/state.json` returns `merge: ours`
- File correctly tracked (`git ls-files .gitattributes`)


---

## Risks & Mitigation

- **Risk:** C1 regression on `detect_phase(commit_message=None, fallback_to_state=True)`  
  State.json fallback works correctly here: the commit-scope path short-circuits on `None`.
  - **Mitigation:** Existing test `test_fallback_to_state_json_when_commit_scope_missing` covers this path.

- **Risk:** C1 regression on `state_reconstructor.py` (`fallback_to_state=False`)  
  Explicit `False` skips the state.json block — behaviour unchanged after the inversion.
  - **Mitigation:** New test `test_detect_phase_fallback_false_still_uses_commit_scope` covers this explicitly.

- **Risk:** C2 — three existing tests fail after GREEN, before REFACTOR  
  `test_pr_tools.py:70`, `test_github_extras.py:124`, `test_github_adapter.py:160` still expect
  `merge_method="squash"`. This is the expected RED→GREEN→REFACTOR flow.
  - **Mitigation:** REFACTOR step updates all three as a fixed action.

- **Risk:** C3 — `.gitattributes merge=ours` requires a custom git driver  
  `ours` is a built-in git merge strategy; no `merge.ours.driver` configuration needed.
  - **Mitigation:** Verification via `git check-attr merge .st3/state.json` before commit.

---

## Milestones

- C1 green + quality gates: core bug fixed; `detect_phase()` correct on child branches
- C2 green + tests updated: merge enforcement active; full test suite green
- C3 done + git check-attr verified: all three preventive measures active
- Full test suite green: ready for integration phase transition

## Related Documentation
- **[docs/development/issue272/research.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue272/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-08 | Agent | Initial scaffold |
| 1.2 | 2026-04-08 | Agent | Cycles renumbered to match execution order: old C3 (merge_method) → C2, old C2 (.gitattributes) → C3 |
| 1.3 | 2026-04-08 | Agent | Translated to English (Prime Directive 5); removed hardcoded test count from C1 success criteria |