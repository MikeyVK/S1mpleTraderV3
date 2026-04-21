<!-- docs\development\issue283\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-21T00:00Z updated= -->
# submit_pr + PRStatusCache + BranchMutatingTool - Planning

**Status:** READY FOR IMPLEMENTATION
**Version:** 1.1
**Last Updated:** 2026-04-21
**Design reference:** [design-submit-pr-prstatus-enforcement.md](design-submit-pr-prstatus-enforcement.md) v1.2
**Research reference:** [research-submit-pr-impact-analysis.md](research-submit-pr-impact-analysis.md) v2.0

---

## 1. Purpose

Executable implementation plan for issue #283 after the submit_pr redesign. This planning document is the active implementation baseline and turns the approved design into a compact 5-cycle sequence that is readable for humans and precise enough for `save_planning_deliverables`.

The planning is explicitly **FLAG DAY**: no backward-compat shims, no dual paths, and no legacy tests left behind after implementation.

---

## 2. Scope

**In Scope:**
- `submit_pr` as the only public PR-creation workflow tool
- `PRStatusCache` and `IPRStatusReader` / `IPRStatusWriter`
- `tool_category` support in `BaseTool`, `BranchMutatingTool`, `EnforcementRule`, and `EnforcementRunner`
- `check_pr_status` and `check_phase_readiness` enforcement
- rollout to all 18 branch-mutating tools
- `merge_pr` cache-clear behavior
- removal of old ready-phase enforcement path and old sequential-flow tests
- documentation rewrites from `create_pr` workflow to `submit_pr`

**Out of Scope:**
- GitHub branch protection rules
- non-agent audit trail beyond existing approvals
- unrelated MCP server refactors

---

## 3. Prerequisites

1. Branch `refactor/283-ready-phase-enforcement` is active.
2. Workflow phase is `planning`.
3. Research v2.0 and design v1.2 are the approved inputs.
4. Old issue-283 `planning_deliverables` history is archived as legacy before writing the new plan.

---

## 4. Summary

Five compact TDD cycles are sufficient for this implementation. The split is intentionally coarse enough to stay human-readable, but still disciplined enough to give each cycle a small, verifiable exit.

| Cycle | Focus | Why it stands alone |
|------|-------|---------------------|
| C1 | Contract surface | Establishes the new types and schema boundaries before behavior changes |
| C2 | Enforcement + wiring | Makes policy gates and PR-status enforcement real at runtime |
| C3 | submit_pr execution | Delivers the new atomic path and removes the old ready-phase path |
| C4 | Branch lockdown rollout | Applies the new category model to all mutating tools and merge exit |
| C5 | Flag-day cleanup | Deletes legacy behavior, rewrites tests/docs, and proves clean break |

---

## 5. Dependencies

- C2 depends on C1.
- C3 depends on C1 + C2.
- C4 depends on C2 + C3.
- C5 depends on C1-C4.
- No safe parallel track is planned; this is a flag-day branch and sequential execution reduces cleanup risk.

---

## 6. Cycle Plan

### Cycle 1 - Contract Surface

**Goal:** Introduce the new contract surface without changing runtime behavior yet.

**Files likely touched:**
- `mcp_server/tools/base.py`
- `mcp_server/config/schemas/enforcement_config.py`
- `mcp_server/core/interfaces/__init__.py`
- `mcp_server/state/pr_status_cache.py`
- `mcp_server/tools/pr_tools.py`

**Deliverables:**
1. `BaseTool` supports `tool_category`; `BranchMutatingTool` exists as a zero-method ABC.
2. `EnforcementRule` accepts `tool_category` and validates `tool` OR `tool_category` for tool events.
3. `IPRStatusReader`, `IPRStatusWriter`, and `PRStatus` enum exist in `core/interfaces/__init__.py`.
4. `SubmitPRInput` and `SubmitPRTool` scaffolding exist; `CreatePRTool` remains internal-only by design.
5. `PRStatusCache` implementation exists in `state/pr_status_cache.py`.

**Exit criteria:**
- Unit tests for schema/interface surface pass.
- Startup validation can load the new schema types without runtime fallback hacks.

### Cycle 2 - Enforcement Pipeline + Composition Root

**Goal:** Make the new policy model executable.

**Files likely touched:**
- `mcp_server/managers/enforcement_runner.py`
- `.st3/config/enforcement.yaml`
- `mcp_server/server.py`

**Deliverables:**
1. `EnforcementRunner` dispatches by `tool_category` as well as tool name.
2. `_handle_check_pr_status` and `_handle_check_phase_readiness` exist and are registered.
3. `PRStatusCache` is wired into `server.py`, `EnforcementRunner`, `SubmitPRTool`, and `MergePRTool`.
4. `.st3/config/enforcement.yaml` contains the new `branch_mutating` rule and `submit_pr` readiness gate.

**Exit criteria:**
- Unit tests cover `tool_category` dispatch and both new handlers.
- Startup/config validation fails fast on unknown categories or invalid rules.

### Cycle 3 - submit_pr Atomic Flow

**Goal:** Ship the new happy path and remove the old ready-phase execution path.

**Files likely touched:**
- `mcp_server/tools/pr_tools.py`
- `mcp_server/tools/git_tools.py`
- `mcp_server/server.py`

**Deliverables:**
1. `SubmitPRTool.execute()` performs phase read, net-diff check, neutralize, commit, push, create PR, cache OPEN.
2. `CreatePRTool` is no longer instantiated in `server.py` (the composition root); the class remains in `pr_tools.py` as internal utility used by `SubmitPRTool` (per design decision D2).
3. The terminal-route neutralization code is removed from `GitCommitTool`.
4. `git_add_or_commit` in ready phase is blocked; ready-phase completion is exclusive to `submit_pr`.
5. `CreatePRTool` class still exists in `pr_tools.py`; `SubmitPRTool` delegates PR creation to it internally.

**Exit criteria:**
- Integration tests prove `submit_pr` happy path and partial-failure recovery behavior.
- No public tool path remains for the old `git_add_or_commit -> create_pr` sequence.

### Cycle 4 - Branch Lockdown Rollout

**Goal:** Enforce post-PR lockdown consistently across the full mutating surface.

**Files likely touched:**
- `mcp_server/tools/base.py`
- tool modules containing the 18 branch-mutating tools
- `mcp_server/tools/pr_tools.py`

**Deliverables:**
1. All 18 targeted mutating tools inherit from `BranchMutatingTool`; a dedicated test in the lockdown suite inventories all 18 by name.
2. `MergePRTool` stays explicitly exempt and writes `PRStatus.ABSENT` only after successful merge.
3. Integration coverage proves mutating tools are blocked after `submit_pr` while `merge_pr` remains allowed.
4. Save/update planning deliverables tools are included in the blocked mutating set; this is proven via integration test coverage in `test_pr_status_lockdown.py`, not via design document reference.

**Exit criteria:**
- Tool inventory matches the design's 18-tool set exactly (verified by name in integration test).
- Integration tests prove post-PR lockdown and merge escape hatch semantics.

### Cycle 5 - Flag-Day Cleanup

**Goal:** Finish the clean break and remove every legacy artifact of the old workflow.

**Files likely touched:**
- `tests/mcp_server/integration/test_ready_phase_enforcement.py` (rewrite for new submit_pr flow)
- `tests/mcp_server/unit/integration/test_all_tools.py` (remove CreatePRTool public-tool registration)
- documentation refs to `create_pr`
- any old enforcement/config leftovers

**Deliverables:**
1. Legacy enforcement rules (`exclude_branch_local_artifacts`, `create_pr -> check_merge_readiness`) are deleted.
2. Tests that model the old sequential ready-phase public flow are removed or fully rewritten; this covers both `test_ready_phase_enforcement.py` (integration) and the public-tool registration in `test_all_tools.py`.
3. Documentation references are updated from public `create_pr` workflow to `submit_pr` workflow.
4. Full suite + quality gates pass with no legacy compatibility path left in production code.

**Exit criteria:**
- Grep closure confirms no public workflow docs/tests still prescribe `git_add_or_commit -> create_pr`.
- Full test suite and branch quality gates pass.

---

## 7. Risks and Controls

- **Risk:** Half-migrated tool inventory leaves gaps in post-PR enforcement.
  **Control:** C4 explicitly validates the full 18-tool set by name in an integration test.
- **Risk:** Old tests keep passing against internal `CreatePRTool` and hide legacy workflow residue.
  **Control:** C5 is a mandatory flag-day cleanup cycle, not an optional polish pass. Note that unit tests for `CreatePRTool` as an internal class may legitimately remain — only tests that model the old public workflow must be removed.
- **Risk:** `planning_deliverables` cannot be saved because an older live entry still exists.
  **Control:** Legacy-mark the current live entry before calling `save_planning_deliverables`.

---

## 8. Deliverables Payload Appendix

This appendix is the compact payload model for `save_planning_deliverables`.

```json
{
  "tdd_cycles": {
    "total": 5,
    "cycles": [
      {
        "cycle_number": 1,
        "deliverables": [
          {
            "id": "C1.1",
            "description": "BaseTool exposes tool_category and BranchMutatingTool exists as zero-method ABC",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/base.py",
              "text": "class BranchMutatingTool"
            }
          },
          {
            "id": "C1.2",
            "description": "EnforcementRule schema accepts tool_category and validates tool OR tool_category",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/config/schemas/enforcement_config.py",
              "text": "tool_category"
            }
          },
          {
            "id": "C1.3",
            "description": "IPRStatusReader, IPRStatusWriter, and PRStatus enum exist in core/interfaces/__init__.py",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/core/interfaces/__init__.py",
              "text": "IPRStatusReader"
            }
          },
          {
            "id": "C1.4",
            "description": "SubmitPRInput and SubmitPRTool contract surface exists in pr_tools.py",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/pr_tools.py",
              "text": "class SubmitPRTool"
            }
          },
          {
            "id": "C1.5",
            "description": "PRStatusCache implementation exists in state/pr_status_cache.py",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/state/pr_status_cache.py",
              "text": "class PRStatusCache"
            }
          }
        ],
        "exit_criteria": "Schema/interface unit tests pass; startup can load tool_category-aware config without fallback hacks"
      },
      {
        "cycle_number": 2,
        "deliverables": [
          {
            "id": "C2.1",
            "description": "EnforcementRunner dispatches on rule.tool_category in addition to rule.tool",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/managers/enforcement_runner.py",
              "text": "rule.tool_category"
            }
          },
          {
            "id": "C2.2",
            "description": "check_pr_status handler exists and is registered",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/managers/enforcement_runner.py",
              "text": "_handle_check_pr_status"
            }
          },
          {
            "id": "C2.3",
            "description": "submit_pr readiness gate exists in enforcement.yaml",
            "validates": {
              "type": "contains_text",
              "file": ".st3/config/enforcement.yaml",
              "text": "check_phase_readiness"
            }
          },
          {
            "id": "C2.4",
            "description": "Composition root wires PRStatusCache into tools and EnforcementRunner",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/server.py",
              "text": "PRStatusCache"
            }
          }
        ],
        "exit_criteria": "tool_category dispatch and both new handlers are covered by unit tests; startup validation rejects invalid rules"
      },
      {
        "cycle_number": 3,
        "deliverables": [
          {
            "id": "C3.1",
            "description": "SubmitPRTool.execute implements the atomic flow and writes OPEN to PRStatusCache",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/pr_tools.py",
              "text": "set_pr_status"
            }
          },
          {
            "id": "C3.2",
            "description": "server.py composition root no longer instantiates CreatePRTool; SubmitPRTool replaces it in the public tool list (per design D2: CreatePRTool class remains in pr_tools.py as internal utility)",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/server.py",
              "text": "CreatePRTool("
            }
          },
          {
            "id": "C3.3",
            "description": "GitCommitTool no longer contains the terminal-route neutralization path",
            "validates": {
              "type": "absent_text",
              "file": "mcp_server/tools/git_tools.py",
              "text": "neutralize_to_base"
            }
          },
          {
            "id": "C3.4",
            "description": "Integration coverage exists for submit_pr atomic execution",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_submit_pr_atomic_flow.py",
              "text": "test_submit_pr_happy_path"
            }
          },
          {
            "id": "C3.5",
            "description": "CreatePRTool class still exists in pr_tools.py as internal utility; SubmitPRTool delegates PR creation to it",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/pr_tools.py",
              "text": "class CreatePRTool"
            }
          }
        ],
        "exit_criteria": "submit_pr happy path and partial failure tests pass; old ready-phase sequential public path no longer exists; CreatePRTool class remains as internal utility"
      },
      {
        "cycle_number": 4,
        "deliverables": [
          {
            "id": "C4.1",
            "description": "Integration test inventories all 18 mutating tools by name, proving complete rollout",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_pr_status_lockdown.py",
              "text": "test_all_18_mutating_tools_inherit_BranchMutatingTool"
            }
          },
          {
            "id": "C4.2",
            "description": "MergePRTool writes ABSENT to cache only after successful merge",
            "validates": {
              "type": "contains_text",
              "file": "mcp_server/tools/pr_tools.py",
              "text": "PRStatus.ABSENT"
            }
          },
          {
            "id": "C4.3",
            "description": "Integration coverage proves post-PR lockdown blocks mutating tools",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_pr_status_lockdown.py",
              "text": "test_branch_mutating_tools_blocked_when_pr_open"
            }
          },
          {
            "id": "C4.4",
            "description": "SavePlanningDeliverablesTool is verified as part of the blocked mutating set in the lockdown integration test",
            "validates": {
              "type": "contains_text",
              "file": "tests/mcp_server/integration/test_pr_status_lockdown.py",
              "text": "SavePlanningDeliverablesTool"
            }
          }
        ],
        "exit_criteria": "Inventory matches the 18-tool design set (by name, in test) and lockdown integration tests pass, including merge escape hatch"
      },
      {
        "cycle_number": 5,
        "deliverables": [
          {
            "id": "C5.1",
            "description": "Legacy enforcement rules are removed from enforcement.yaml",
            "validates": {
              "type": "absent_text",
              "file": ".st3/config/enforcement.yaml",
              "text": "exclude_branch_local_artifacts"
            }
          },
          {
            "id": "C5.2",
            "description": "Legacy create_pr merge-readiness rule is removed from enforcement.yaml",
            "validates": {
              "type": "absent_text",
              "file": ".st3/config/enforcement.yaml",
              "text": "check_merge_readiness"
            }
          },
          {
            "id": "C5.3",
            "description": "test_ready_phase_enforcement.py no longer models the old create_pr check_merge_readiness flow",
            "validates": {
              "type": "absent_text",
              "file": "tests/mcp_server/integration/test_ready_phase_enforcement.py",
              "text": "check_merge_readiness"
            }
          },
          {
            "id": "C5.4",
            "description": "submit_pr documentation path is present in MCP docs",
            "validates": {
              "type": "contains_text",
              "file": "agent.md",
              "text": "submit_pr"
            }
          },
          {
            "id": "C5.5",
            "description": "test_all_tools.py no longer registers CreatePRTool as a public MCP tool",
            "validates": {
              "type": "absent_text",
              "file": "tests/mcp_server/unit/integration/test_all_tools.py",
              "text": "make_create_pr_tool"
            }
          }
        ],
        "exit_criteria": "Legacy workflow grep closure is clean; full suite and branch quality gates pass"
      }
    ]
  }
}
```

---

## Related Documentation

- [design-submit-pr-prstatus-enforcement.md](design-submit-pr-prstatus-enforcement.md)
- [research-submit-pr-impact-analysis.md](research-submit-pr-impact-analysis.md)
- [planning-ready-phase-enforcement.md](planning-ready-phase-enforcement.md) - superseded predecessor

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-04-21 | Agent | QA corrections: C1.3 → validates interfaces file; C1.5 added for cache; C3.2 description clarified; C3.5 added for CreatePRTool class survival; C4.1/C4.4 validates moved from base.py/design-doc to integration test; C5.3 → test_ready_phase_enforcement.py; C5.5 added for test_all_tools.py |
| 1.0 | 2026-04-21 | Agent | New compact planning for submit_pr + PRStatusCache + BranchMutatingTool implementation |
