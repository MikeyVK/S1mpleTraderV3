<!-- docs\development\issue283\research-submit-pr-impact-analysis.md -->
<!-- template=research version=8b7bb3ab created=2026-04-16T06:37Z updated= -->
# submit_pr Atomic Tool — Impact Analysis & Findings

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-16

---

## Scope

**In Scope:**
submit_pr tool design rationale, production code impact, test inventory impact, documentation reference inventory, post-submit gap analysis, enforcement pipeline changes

**Out of Scope:**
Full enforcement on all file-modification tools (separate issue), GitHub branch protection rules, post-PR lockdown implementation beyond submit_pr scope

---

## Problem Statement

The current sequential flow (git_add_or_commit → create_pr) suffers from a chicken-and-egg problem: neutralize_to_base() restores .st3/state.json to the merge-base version, causing the subsequent create_pr enforcement to read the wrong phase and block PR creation. A new atomic submit_pr tool is needed to combine phase check, neutralization, commit, push, and PR creation into a single operation.

## Research Goals

- Map complete impact of replacing create_pr with submit_pr across production code, tests, configuration, and documentation
- Analyze the post-submit pre-merge security gap and identify mitigations
- Determine NoteContext/messaging preservation strategy
- Provide actionable scope assessment for design and implementation phases

---

## Background

Issue #283 implements ready-phase enforcement via Model 1 branch-tip neutralization. Cycles C1-C10 are complete. During ready-phase testing, the kip-ei (chicken-and-egg) problem was discovered: neutralize_to_base() in git_add_or_commit restores state.json to merge-base, and the subsequent create_pr call reads that corrupted state. Three solutions were evaluated: (A) worktree restore (dirty), (B) HEAD commit message detection (fragile), (C) atomic submit_pr tool (architecturally sound). User chose option C.

## Related Documentation
- **[docs/development/issue283/research-ready-phase-enforcement.md (SUPERSEDED)][related-1]**
- **[docs/development/issue283/research-model1-branch-tip-neutralization.md (SUPERSEDED)][related-2]**
- **[docs/development/issue283/research-git-add-or-commit-regression.md (SUPERSEDED)][related-3]**
- **[docs/development/issue283/design-ready-phase-enforcement.md (SUPERSEDED)][related-4]**
- **[docs/development/issue283/design-git-add-commit-regression-fix.md (SUPERSEDED)][related-5]**
- **[docs/development/issue283/planning-ready-phase-enforcement.md (SUPERSEDED)][related-6]**
- **[docs/development/issue283/planning.md (SUPERSEDED)][related-7]**

<!-- Link definitions -->

[related-1]: docs/development/issue283/research-ready-phase-enforcement.md (SUPERSEDED)
[related-2]: docs/development/issue283/research-model1-branch-tip-neutralization.md (SUPERSEDED)
[related-3]: docs/development/issue283/research-git-add-or-commit-regression.md (SUPERSEDED)
[related-4]: docs/development/issue283/design-ready-phase-enforcement.md (SUPERSEDED)
[related-5]: docs/development/issue283/design-git-add-commit-regression-fix.md (SUPERSEDED)
[related-6]: docs/development/issue283/planning-ready-phase-enforcement.md (SUPERSEDED)
[related-7]: docs/development/issue283/planning.md (SUPERSEDED)

---

## Findings

### 1. The Chicken-and-Egg Problem (Root Cause)

The current ready-phase completion requires **two sequential tool calls**, each with its own `NoteContext`:

```
Call 1: git_add_or_commit(workflow_phase="ready")
  → Pre-enforcement: exclude_branch_local_artifacts → ExclusionNote
  → Execute: reads ExclusionNote → neutralize_to_base({state.json, deliverables.json})
  → Result: state.json restored to merge-base version (wrong issue, wrong phase)

Call 2: create_pr(head="feature/42", base="main")
  → Pre-enforcement: check_merge_readiness → reads state.json → sees wrong phase
  → BLOCKED: "PR creation requires phase 'ready'. Current phase: 'documentation'."
```

**Why it's unsolvable with the current two-tool architecture:**
- `NoteContext` is per-tool-call (fresh instance in `server.py:handle_call_tool`)
- After neutralize, `state.json` belongs to main's version — there's no way to recover it
- `transition_phase` also fails because `state.json` now references a different issue
- Even `force_phase_transition` fails: "Project plan not found for issue 283"

### 2. Proposed Solution: `submit_pr` Atomic Tool

`submit_pr` performs the entire ready-phase completion in a single tool call:

| Step | Operation | Source |
|------|-----------|--------|
| 1 | Read `state.json` (still intact) | `_read_current_phase()` |
| 2 | Phase gate: `current_phase == pr_allowed_phase` | `_handle_check_merge_readiness` logic |
| 3 | Net-diff check: branch-local artifacts against base | `_has_net_diff_for_path()` |
| 4 | `neutralize_to_base()` for tracked artifacts | `GitAdapter.neutralize_to_base()` |
| 5 | Commit with scope `chore(P_READY): neutralize...` | `GitManager.commit_with_scope()` |
| 6 | Push to remote | `GitAdapter.push()` |
| 7 | Create PR via GitHub API | `GitHubManager.create_pr()` |

`create_pr` (the class) stays as production code but is **not registered** as an MCP tool.

### 3. Production Code Impact

| File | Change Required |
|------|----------------|
| `mcp_server/tools/pr_tools.py` | Add `SubmitPRTool` + `SubmitPRInput`. `CreatePRTool` retained for internal use, removed from MCP registration |
| `mcp_server/server.py` | Register `SubmitPRTool` instead of `CreatePRTool` in tool list |
| `mcp_server/managers/enforcement_runner.py` | `check_merge_readiness` handler unchanged — called internally by `SubmitPRTool.execute()` |
| `.st3/config/enforcement.yaml` | `tool: create_pr` → `tool: submit_pr` OR remove rule (enforcement becomes internal) |
| `mcp_server/tools/git_tools.py` | Terminal-route neutralize logic (lines 370-395 in `GitCommitTool.execute()`) → extracted to shared utility or moved to `SubmitPRTool` |

**Key architectural decision**: Whether enforcement stays in `enforcement.yaml` (consistent with all other tools) or moves internal to `SubmitPRTool.execute()` (simpler, since the check and action are now atomic).

### 4. NoteContext / Messaging Preservation

The `NoteContext` lifecycle does not change fundamentally:
- `submit_pr` gets its own `NoteContext` instance (same as any tool call)
- `ExclusionNote` and `SuggestionNote` are produced within that single context
- `CommitNote` records the neutralization commit hash
- No cross-tool-call `NoteContext` sharing is needed

The current messaging classes (`ExclusionNote`, `SuggestionNote`, `CommitNote`) remain intact. The only change is that they are all produced and consumed within one tool call instead of two.

### 5. Test Inventory Impact

**60+ test methods across 11 files. Categorized impact:**

#### 5a. Tests That Break (must rewrite for `submit_pr` flow)

| File | Methods | Reason |
|------|---------|--------|
| `tests/mcp_server/integration/test_ready_phase_enforcement.py` | 7 + 1 fixture | Test the two-tool sequential flow (commit → create_pr) |
| `tests/mcp_server/integration/test_create_pr_merge_readiness_c6.py` | 5 + 1 fixture | Test `create_pr` enforcement in isolation |
| `tests/mcp_server/integration/test_model1_branch_tip_neutralization.py` | 3 | Test the neutralize → create_pr sequence |

#### 5b. Tests That Need Update (enforcement event name change)

| File | Methods | Reason |
|------|---------|--------|
| `tests/mcp_server/unit/managers/test_enforcement_runner_c3.py` | 11 | Test `check_merge_readiness` handler — event name may change |
| `tests/mcp_server/unit/managers/test_enforcement_runner_c9_default_base.py` | 10 | Test default base branch in enforcement context |
| `tests/mcp_server/unit/managers/test_enforcement_runner_unit.py` | 6 | Unit tests for enforcement runner |

#### 5c. Tests That Likely Survive (internal CreatePRTool stays)

| File | Methods | Reason |
|------|---------|--------|
| `tests/mcp_server/unit/tools/test_git_tools_c8_terminal_route.py` | 11 | Tests terminal-route neutralize in GitCommitTool — depends on refactor scope |
| `tests/mcp_server/unit/tools/test_pr_tools.py` | 5 | Tests CreatePRTool mechanics (may survive if class stays) |
| `tests/mcp_server/unit/tools/test_pr_tools_config.py` | 1 | Tests CreatePRInput.apply_default_base_branch — survives |
| `tests/mcp_server/unit/test_server.py` | 2 | create_pr-specific tests in server test |
| `tests/mcp_server/unit/test_github_extras.py` | 1 | Tests GitHub manager PR creation |
| `tests/mcp_server/unit/managers/test_enforcement_runner.py` | 9 | General enforcement runner tests |

#### 5d. New Tests Required

- `test_submit_pr_atomic_flow.py` — end-to-end: phase check → neutralize → commit → push → PR
- `test_submit_pr_enforcement.py` — enforcement integration (phase gate, net-diff)
- `test_submit_pr_error_handling.py` — partial failure recovery (what if push fails after commit?)

### 6. Post-Submit Pre-Merge Gap Analysis (CRITICAL)

After `submit_pr` executes, the branch is in a "neutralized" state. Investigation reveals:

#### 6a. Phase Guard Bypass Vulnerability

`build_phase_guard` in `git_tools.py` (lines 43-74) has an early return:

```python
if data.get("branch") != branch:
    return  # state.json belongs to a different branch — skip
```

After neutralize: `state.json.branch == "main"` (merge-base version), but `current_branch == "feature/42"`. Mismatch → guard skips → **any workflow_phase commits are accepted without validation**.

#### 6b. Unenforceable Tools

| Tool | `enforcement_event` | Status |
|------|---------------------|--------|
| `safe_edit_file` | NOT SET | No enforcement |
| `scaffold_artifact` | NOT SET | No enforcement |
| `create_file` | NOT SET | No enforcement |
| `git_push` | NOT SET | No enforcement |
| `git_restore` | NOT SET | No enforcement |
| `merge_pr` | NOT SET | No enforcement |

#### 6c. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Agent makes commits after submit_pr | Medium | Phase guard bypass allows it, but agent instructions prohibit post-PR commits. PR review catches unexpected changes. |
| Agent pushes extra commits to PR | Medium | No `git_push` enforcement, but agent instructions only use `git_push` during development phases |
| Agent merges without approval | Low | `merge_pr` has no enforcement, but agent.md **mandates human approval** before merge |
| Non-agent actor modifies branch | Low | Out of scope — GitHub branch protection rules cover this |

#### 6d. Recommended Mitigations (in-scope vs. out-of-scope)

**In-scope for this issue:**
- `submit_pr` is the ONLY public-facing PR tool (removes `create_pr` from agent visibility)
- Agent instructions updated to reflect `submit_pr` as the terminal workflow action

**Out-of-scope (separate issue recommended):**
- Add `enforcement_event` to `safe_edit_file`, `scaffold_artifact`, `git_push`, `merge_pr`
- Post-PR lockdown mechanism (state flag or GitHub API query)
- Fix phase guard to not skip on branch mismatch after neutralize

### 7. Documentation Reference Inventory

**Total: ~50 references to `create_pr` across the codebase.**

| Category | Count | Key Files |
|----------|-------|-----------|
| Agent instructions | 5 refs | `agent.md` (4), `.github/.copilot-instructions.md` (1) |
| MCP reference docs | 11 refs | `docs/reference/mcp/tools/github.md` (4), `docs/reference/mcp/MCP_TOOLS.md` (5), `docs/reference/mcp/tools/README.md` (2) |
| Architecture docs | 8+ refs | `VSCODE_AGENT_ORCHESTRATION.md`, `08_naming_landscape.md` |
| Issue #283 design suite | 19+ refs | All design/research/planning docs (SUPERSEDED) |
| Other docs | 10+ refs | `GAP_ANALYSIS_IMPLEMENTATION_PLAN.md`, `SAFE_EDIT_TOOL_FLOW_ENFORCEMENT.md`, issue99 analysis |
| Configuration | 1 ref | `.st3/config/enforcement.yaml` (line 24) |
| Source code | 10 refs | `mcp_server/tools/pr_tools.py` (7 to name + enforcement_event) |
| Tests | 15+ refs | `test_pr_tools_config.py`, `test_enforcement_runner_c3.py`, `test_create_pr_merge_readiness_c6.py` |

### 8. Design Decisions Required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Enforcement via yaml or internal? | A) `submit_pr` in enforcement.yaml (consistent) B) Internal check in execute() (simpler) | **B**: The check-and-act are now atomic; yaml routing adds overhead without benefit |
| D2 | `create_pr` class fate | A) Delete entirely B) Keep as internal utility | **B**: Keep for `submit_pr` to delegate PR creation to |
| D3 | Terminal-route in GitCommitTool | A) Remove entirely B) Keep for backward compat | **A**: No longer needed — neutralize moves to `submit_pr` |
| D4 | `git_add_or_commit` in ready phase | A) Block ready-phase commits B) Allow but skip neutralize | **A**: Ready-phase commits are now handled by `submit_pr` only |
| D5 | `exclude_branch_local_artifacts` enforcement rule | A) Remove from enforcement.yaml B) Keep but repurpose | **A**: Neutralize is now internal to `submit_pr` |
| D6 | Post-PR gap enforcement | A) In-scope for #283 B) Separate issue | **B**: Separate issue — current mitigations (agent instructions + PR review) suffice |

---

## Conclusions

1. **`submit_pr` is architecturally sound** — it eliminates the chicken-and-egg problem by making phase check and neutralization atomic within a single tool call.

2. **Scope is significant but bounded** — ~5 production files, ~25 test methods to rewrite/update, ~50 documentation references. The core enforcement logic (`check_merge_readiness`, `neutralize_to_base`) is reused, not rewritten.

3. **NoteContext mechanism is fully preserved** — no changes to `ExclusionNote`, `SuggestionNote`, or `CommitNote`. They just live within one tool context instead of two.

4. **Post-submit gap is real but manageable** — the phase guard bypass after neutralize is a known vulnerability, but it's mitigated by agent instructions and PR review. Full enforcement on all tools is a separate, larger initiative.

5. **Superseded documents** — all prior research, design, and planning documents for issue #283 are superseded by this analysis. New design and planning docs should be scaffolded for the `submit_pr` approach.

---

## Open Questions

- Should `submit_pr` support `draft` PR creation?
- Should the push step be configurable (e.g., force-push support)?
- How to handle partial failure (e.g., commit succeeds but push fails)?
- Should `submit_pr` auto-detect the PR body from scaffolded artifacts (`.st3/temp/pr_*.md`)?

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-16 | Agent | Initial findings from deep impact analysis — 3 subagent explorations synthesized |