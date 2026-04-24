<!-- docs\development\issue283\planning-ready-phase-enforcement.md -->
<!-- template=planning version=130ac5ea created=2026-04-09T16:25Z updated= -->
# Ready Phase Enforcement — Implementation Planning

**Status:** SUPERSEDED — See [README.md](README.md), [planning.md](planning.md), and [design-submit-pr-prstatus-enforcement.md](design-submit-pr-prstatus-enforcement.md)  
**Version:** 1.0  
**Last Updated:** 2026-04-09

---

## Purpose

Translate design v2.0 into concrete TDD cycles with correct sequencing, explicit dependencies, and parallelisation opportunities for sub-agent delegation.

## Scope

**In Scope:**
All implementation work defined in design v2.0 sections 2.1–2.12

**Out of Scope:**
MCPServer God Class refactor (issue #285); performance optimisation; backward compatibility layers

## Prerequisites

Read these first:
1. Design v2.0 FINAL (docs/development/issue283/design-ready-phase-enforcement.md)
2. Branch refactor/283-ready-phase-enforcement checked out
3. Full test suite green before starting (baseline)
---

## Summary

Five TDD cycles implementing the ready-phase enforcement design (v2.0) for issue #283. Covers Pydantic schema changes, YAML config updates, ConfigLoader static helper, MergeReadinessContext facade, EnforcementRunner extension, ConfigValidator cross-validation, tool enforcement_event declarations, and test blast-radius fixes.

---

## Dependencies

- C2 depends on C1 (WorkphasesConfig.get_terminal_phase() must exist before injection can call it)
- C3 depends on C1 (MergeReadinessContext uses BranchLocalArtifact from C1; PhaseContractsConfig.get_pr_allowed_phase() from C1)
- C3 also depends on C2 (server.py injection step must be present before MergeReadinessContext construction is added)
- C4 depends on C3 (handlers must be registered before enforcement_event is wired into tool dispatch)
- C5 is fully independent — can start immediately in parallel
- C5 is the only cycle that can run in parallel (start immediately after C1)

---

## TDD Cycles

```
C5 ─────────────────────────────────────────────────────────► (parallel, start immediately)

C1 ──► C2 ──┬──► C3 ──► C4 ──► (critical path)
             └──────────────────► (C3 ‖ not applicable — C4 depends on C3)

C1 ‖ C5 simultaneously.
C3 ‖ C5 once C1+C2 done (C5 still in progress).
```

---

### Cycle 1 — Pydantic Schemas + YAML Config

**Goal:** Add `terminal` field to `PhaseDefinition`; add `model_validator` + `get_terminal_phase()` to
`WorkphasesConfig`; add `BranchLocalArtifact`, `MergePolicy` models and `merge_policy` required field +
`get_pr_allowed_phase()` to `PhaseContractsConfig`; update YAML config files; fix all Pydantic
blast-radius test files (V6, V7, N_PCR_DOUBLE).

**Design refs:** §2.1, §2.2, §2.3, §2.4, §4-V6, §4-V7, §4-N_PCR_DOUBLE

**Files touched:**
| File | Change |
|------|--------|
| `mcp_server/config/schemas/workphases.py` | `PhaseDefinition.terminal: bool = False`; `WorkphasesConfig.validate_single_terminal_phase` validator; `get_terminal_phase()` method |
| `mcp_server/config/schemas/phase_contracts_config.py` | `BranchLocalArtifact`, `MergePolicy` models; `PhaseContractsConfig.merge_policy: MergePolicy` (required); `get_pr_allowed_phase()` method |
| `.st3/config/workphases.yaml` | Add `ready` phase with `terminal: true` |
| `.st3/config/phase_contracts.yaml` | Add `merge_policy` section |
| `tests/mcp_server/unit/config/test_label_startup.py` | Add `"ready": PhaseDefinition(terminal=True)` to WorkphasesConfig constructions (lines 104, 282) |
| `tests/mcp_server/test_support.py` | Add `merge_policy` to fallback `PhaseContractsConfig.model_validate` (line 238) |
| `tests/mcp_server/unit/managers/test_phase_contract_resolver.py` | Add `ready` + `merge_policy` to both inline YAML fixtures (N_PCR_DOUBLE) |
| `tests/mcp_server/unit/tools/test_force_phase_transition_tool.py` | Add `ready: terminal: true` to ~4 workspace fixtures |
| `tests/mcp_server/core/test_scope_encoder.py` | Add `ready: terminal: true` to workphases_yaml fixture |

**New tests (RED first):**
- `test_phase_definition_terminal_defaults_false` — `PhaseDefinition()` has `terminal=False`
- `test_workphases_config_validator_zero_terminal_raises` — 0 terminal phases → `ValueError`
- `test_workphases_config_validator_two_terminal_raises` — 2 terminal phases → `ValueError`
- `test_workphases_config_get_terminal_phase` — returns name of the one `terminal=True` phase
- `test_branch_local_artifact_schema` — `BranchLocalArtifact` path/reason fields
- `test_merge_policy_pr_allowed_phase` — `MergePolicy` fields
- `test_phase_contracts_config_merge_policy_required` — missing `merge_policy` → `ValidationError`
- `test_phase_contracts_config_get_pr_allowed_phase` — returns `merge_policy.pr_allowed_phase`

**Success Criteria:**
- All new schema tests GREEN
- V6 blast-radius fixes: `test_label_startup.py`, `test_force_phase_transition_tool.py`, `test_scope_encoder.py` — all GREEN
- V7: `test_support.py` fallback test GREEN
- N_PCR_DOUBLE: `test_phase_contract_resolver.py` GREEN
- Full suite passes (no regressions)

---

### Cycle 2 — ConfigLoader Static Helper + server.py Injection

**Goal:** Add `ConfigLoader._inject_terminal_phase(workflow_config, workphases_config)` as a static
method. Update `server.py` `MCPServer.__init__` to call it with the correct load → inject → validate →
construct ordering. Fix V8 phase list assertion. Verify V9 workflow_fixtures.py assertions unchanged (no file edits needed).

**Design refs:** §2.5, §4-V8, §4-V9

**Files touched:**
| File | Change |
|------|--------|
| `mcp_server/config/loader.py` | Add `@staticmethod _inject_terminal_phase(workflow_config, workphases_config) -> WorkflowConfig` |
| `mcp_server/server.py` | After `load_workflow_config()` + `load_workphases_config()`, call `ConfigLoader._inject_terminal_phase(...)` before `ConfigValidator` construction |
| `tests/mcp_server/unit/config/test_workflow_config.py` | Update phase list assertion at line 201 to include `"ready"` (V8 secondary fix) |
| `tests/mcp_server/fixtures/workflow_fixtures.py` | No changes required — `load_workflow_config()` bypass means injection never fires here. Verify existing `[-1]` and `len()` assertions remain valid (V9). |

**New tests (RED first):**
- `test_inject_terminal_phase_appends_to_all_workflows` — `_inject_terminal_phase` appends terminal phase to every workflow that lacks it
- `test_inject_terminal_phase_does_not_duplicate` — workflows already containing terminal phase are left unchanged
- `test_inject_terminal_phase_returns_new_object` — input `WorkflowConfig` is not mutated (CQS / D6)
- `test_inject_terminal_phase_no_file_io` — calling the static method without a real filesystem does not raise
- `test_load_workflow_config_does_not_inject` — `load_workflow_config()` result does NOT contain the terminal phase; guarantees injection was not re-introduced into the loader

**Success Criteria:**
- All new loader tests GREEN
- `server.py` load sequence correct: injection before ConfigValidator construction
- V8: `test_workflow_config.py` phase list assertion GREEN
- V9: `workflow_fixtures.py` no file changes required; verify `[-1]` and `len()` assertions still pass
- Full suite passes

---

### Cycle 3 — MergeReadinessContext + EnforcementRunner + ConfigValidator

**Goal:** Add `MergeReadinessContext` frozen dataclass to `phase_contract_resolver.py`; extend
`EnforcementRunner` constructor with `merge_readiness_context` parameter; add both handlers
(`_handle_exclude_branch_local_artifacts`, `_handle_check_merge_readiness`); add `enforcement.yaml`
entries; add `ConfigValidator._validate_merge_policy_phase()`; construct `MergeReadinessContext` in
`server.py` and pass to `EnforcementRunner`.

**Design refs:** §2.8, §2.9, §2.10

**Files touched:**
| File | Change |
|------|--------|
| `mcp_server/managers/phase_contract_resolver.py` | Add `MergeReadinessContext` frozen dataclass |
| `mcp_server/managers/enforcement_runner.py` | `EnforcementRunner.__init__` gains `merge_readiness_context: MergeReadinessContext \| None`; register two new handlers in `_build_default_registry()` |
| `mcp_server/config/validator.py` | Add `_validate_merge_policy_phase(phase_contracts_config, workphases_config)` |
| `mcp_server/server.py` | Construct `MergeReadinessContext`; pass to `EnforcementRunner` |
| `.st3/config/enforcement.yaml` | Add `git_commit/pre/exclude_branch_local_artifacts` and `create_pr/pre/check_merge_readiness` rules |

**New tests (RED first):**
- `test_merge_readiness_context_is_frozen` — dataclass rejects mutation
- `test_enforcement_runner_accepts_merge_readiness_context` — constructor injection works
- `test_exclude_handler_skips_untracked_artifacts` — no `git rm` call when file not tracked
- `test_exclude_handler_removes_tracked_artifacts` — `git rm --cached` called per tracked artifact
- `test_exclude_handler_only_runs_in_terminal_phase` — no-op when current phase ≠ terminal
- `test_exclude_handler_output_format` — output matches exact format from §2.9
- `test_check_merge_readiness_blocks_wrong_phase` — raises `ValidationError` with actionable message
- `test_check_merge_readiness_blocks_tracked_artifacts` — raises `ValidationError` listing tracked files
- `test_check_merge_readiness_happy_path` — no error when phase correct and artifacts untracked
- `test_validate_merge_policy_phase_typo` — `ConfigValidator` raises `ConfigError` for unknown `pr_allowed_phase`
- `test_validate_merge_policy_phase_valid` — no error for matching phase name
- `test_enforcement_yaml_new_actions_registered` — `_validate_registered_actions()` does not raise after C3 handlers registered

**Success Criteria:**
- All new tests GREEN
- `enforcement.yaml` entries validated at startup (no `ConfigError` from `_validate_registered_actions`)
- Both handlers invoke correctly via `EnforcementRunner.run()`
- `ConfigValidator._validate_merge_policy_phase()` integrated into `validate()` call chain
- Full suite passes

---

### Cycle 4 — Tool Enforcement Event Declarations + Integration Test

**Goal:** Add `enforcement_event` class variable to `GitCommitTool` and `CreatePRTool`. Write an
end-to-end integration test that verifies the full enforcement path: `EnforcementRunner.run()` is
called by `BaseTool` dispatch with the correct event name, and produces the expected output.

**Design refs:** §2.6, §2.7

**Files touched:**
| File | Change |
|------|--------|
| `mcp_server/tools/git_tools.py` | `GitCommitTool.enforcement_event: str \| None = "git_commit"` |
| `mcp_server/tools/pr_tools.py` | `CreatePRTool.enforcement_event: str \| None = "create_pr"` |

**New tests (RED first):**
- `test_git_commit_tool_enforcement_event` — `GitCommitTool.enforcement_event == "git_commit"`
- `test_create_pr_tool_enforcement_event` — `CreatePRTool.enforcement_event == "create_pr"`
- `test_git_commit_in_terminal_phase_excludes_artifacts` — integration: commit in `ready` phase triggers `exclude_branch_local_artifacts` handler
- `test_create_pr_wrong_phase_blocked` — integration: `create_pr` in non-terminal phase blocked with actionable error
- `test_create_pr_tracked_artifacts_blocked` — integration: `create_pr` with tracked branch-local artifacts blocked
- `test_create_pr_happy_path` — integration: `create_pr` in `ready` phase with untracked artifacts succeeds

**Success Criteria:**
- `GitCommitTool.enforcement_event` and `CreatePRTool.enforcement_event` set correctly
- Integration tests cover happy path + both enforcement error paths
- `execute()` methods of both tools are UNCHANGED (no enforcement logic added)
- Full suite passes

---

### Cycle 5 — Cleanup (Independent)

**Goal:** Remove `merge=ours` from `.gitattributes`. Delete the four debug scripts. Verify full suite
still passes.

**Design refs:** §2.11, §2.12

**Files touched:**
| File | Change |
|------|--------|
| `.gitattributes` | Remove `.st3/state.json merge=ours` line |
| `check_yaml.py` | Delete |
| `fix_yaml.py` | Delete |
| `revert_yaml.py` | Delete |
| `show_yaml.py` | Delete |

**New tests:** None (pure removal; full suite run is the verification)

**Success Criteria:**
- `.gitattributes` no longer contains `merge=ours`
- All four debug scripts absent from working tree and git index
- Full suite passes with no regressions


---

## Risks & Mitigation

- **Risk:** V6 blast radius — `WorkphasesConfig.model_validator` immediately breaks all in-memory constructions without `terminal: true`
  - **Mitigation:** Fix all affected fixture files in the same commit as the schema change (RED step of C1 writes the test; GREEN step ships schema + all fixture fixes atomically)
- **Risk:** N1 deadlock — `enforcement.yaml` references unknown action types if code ships before handlers, or handlers registered before `enforcement.yaml` entries
  - **Mitigation:** C3 commit is atomic: handlers registered + `enforcement.yaml` updated in the same GREEN commit. `_validate_registered_actions()` catches any ordering error at startup.
- **Risk:** Flag-Day startup crash — `workphases.yaml` or `phase_contracts.yaml` not updated alongside Python code
  - **Mitigation:** C1 updates both YAML files in the same GREEN commit as the Pydantic models. Design §2.11 checklist enforces this.

---

## Milestones

- C1 GREEN: All V6/V7/N_PCR_DOUBLE blast-radius tests pass; new schema tests green
- C2 GREEN: Terminal phase injected in server.py; V8 fix applied; V9 verified (no changes to workflow_fixtures.py)
- C3 GREEN: Handlers functional; enforcement.yaml entries validated at startup
- C4 GREEN: Full enforcement path covered by integration test
- C5 GREEN: Removed files gone; full suite passes

## Related Documentation
- **[docs/development/issue283/design-ready-phase-enforcement.md][related-1]**
- **[docs/development/issue283/research-ready-phase-enforcement.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/development/issue283/design-ready-phase-enforcement.md
[related-2]: docs/development/issue283/research-ready-phase-enforcement.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |