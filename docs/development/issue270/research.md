<!-- docs\development\issue270\research.md -->
<!-- template=research version=8b7bb3ab created=2026-04-06T14:59Z updated= -->
# Issue #270 — Remove dead config fields from workphases.yaml and policies.yaml

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-06

---

## Purpose

Pre-implementation verification that all three removals are safe, correct, and complete — no partial fixes.

## Scope

**In Scope:**
workphases.yaml exit_requires/entry_expects fields, workphases.yaml planning/design subphase whitelists, policies.yaml commit.allowed_prefixes field

**Out of Scope:**
Code changes to PSE, PolicyEngine, or WorkphasesConfig schema (those belong to issue #271). ScopeDecoder phase-detection bug (issue #272). Schema field removal from operation_policies_config.py (out of scope unless confirmed dead).

## Prerequisites

Read these first:
1. Issue #257 closed: phase_contracts.yaml is SSOT for exit gates, WorkflowGateRunner owns enforcement
2. _legacy_workphases_gate_summary explicitly marked legacy in PSE (only reached when WGR returns empty + no phase_contracts entry — never true in current config)
3. PolicyEngine regression test (test_policy_engine_config.py) documents that PolicyEngine derives prefixes from GitConfig, not from policies.yaml allowed_prefixes
---

## Problem Statement

Three dead field groups exist in .st3/config/ that are silently ignored at runtime but create maintenance confusion, false documentation, and risk of future misuse. None cause runtime errors. All were identified during QA validation of feature/257-reorder-workflow-phases.

## Research Goals

- Confirm that workphases.yaml exit_requires and entry_expects are truly inert (never enforced at runtime in the current architecture)
- Confirm that planning and design subphase whitelists in workphases.yaml are never validated in practice
- Confirm that policies.yaml commit.allowed_prefixes is never read by PolicyEngine.decide()
- Determine exact removal scope per finding with zero code changes required
- Identify any residual risk or test changes needed

---

## Background

**Finding 1 — workphases.yaml exit_requires / entry_expects**

All phase definitions in workphases.yaml contain exit_requires and/or entry_expects blocks (research, planning, implementation). These were the pre-#257 gate mechanism. Since issue #257, phase_contracts.yaml owns all exit gates via WorkflowGateRunner.

Code path analysis:
- `WorkphasesConfig` schema (workphases.py line 30-31): fields ARE parsed into the model
- `get_exit_requires()` and `get_entry_expects()` methods exist (lines 40-46)
- `_legacy_workphases_gate_summary()` in PSE (line 415) calls both methods
- BUT activation condition (PSE.force_transition lines 228-230): only reached when `not skipped_gates and not passing_gates` after WGR.inspect() — which never happens now that phase_contracts.yaml has entries for all workflows
- PSE constructor (lines 96-97): nullifies both fields when workphases.yaml does NOT exist (test fallback) — confirms they are not relied on at runtime

**Finding 2a — planning and design subphase whitelists (NOT dead)**

Planning defines subphases: `[c1, c2, c3, c4]`; design defines subphases: `[contracts, flows, schemas]`. These are **actively enforced by ScopeEncoder** — when a commit scope includes a subphase token (e.g., `P_PLANNING_SP_C1`), ScopeEncoder validates it against the whitelist for that phase from workphases.yaml. This was a deliberate design decision (A5 from issue #257 design.md).

However, ScopeEncoder's enforcement is not wired through `phase_contracts.yaml`. The whitelists live only in `workphases.yaml`, which is a DRY violation: workflow-phase membership lives partly in `phase_contracts.yaml` (gate enforcement) and partly in `workphases.yaml` (subphase whitelists). That concern is **issue #271 scope**.

**Conclusion for #270:** Leave subphase whitelists intact. Do NOT remove. They are live ScopeEncoder enforcement data.

**Finding 2b — exit_requires / entry_expects in workphases.yaml (stranded legacy)**

All phase definitions contain `exit_requires` and/or `entry_expects` blocks (research, planning, implementation). These were the pre-#257 gate mechanism. The code path that reads them (`PSE._legacy_workphases_gate_summary()`) is explicitly named "legacy" by the original author and is permanently bypassed: the activation condition in `PSE.force_transition` (lines 228-230) only fires when both `skipped_gates` and `passing_gates` are empty after `WGR.inspect()` — which never occurs with current `phase_contracts.yaml` coverage.

PSE constructor also nullifies fallback when `workphases.yaml` does not exist (lines 96-97), confirming no runtime dependency.

**Conclusion for #270:** Safe to remove from YAML only. `WorkphasesConfig` schema fields stay (issue #271 scope).

**Finding 3a — policies.yaml commit.allowed_prefixes (dead)**

The commit operation has `allowed_prefixes: [red:, green:, refactor:, docs:]`. The `OperationPoliciesConfig` schema parses this field (line 33) and a `has_allowed_prefix()` method exists (line 59). But `PolicyEngine.decide()` never calls either — for commit prefix validation it calls `self._git_config.get_all_prefixes()` directly (lines 155-162). The regression test `test_policy_engine_config.py` explicitly documents this as a deliberate fix: "Bug: policies.yaml had red:, green: but GitManager generates test:, feat:. Fix: PolicyEngine derives prefixes from GitConfig."

The field was never removed from policies.yaml after the Convention #6 fix. `validate_commit_message()` in the schema is also dead (never called outside the class).

**Conclusion for #270:** Safe to remove `allowed_prefixes` from YAML. Schema field in `operation_policies_config.py` stays (out of scope).

**Finding 3b — policies.yaml commit.require_tdd_prefix (live, misleadingly named)**

`require_tdd_prefix: true` is used in `PolicyEngine.decide()` (line 155). When True, every commit message must start with a prefix from `_git_config.get_all_prefixes()`. This is a **phase-blind** check: the `phase` parameter passed to `decide()` is ignored in this block. It enforces conventional commit prefixes on ALL commits, not just TDD-phase commits.

The name (`require_tdd_prefix`) implies TDD-exclusivity, but the implementation is a generic "must use a valid conventional commit prefix" guard. The underlying infrastructure (`commit_prefix_map`, `tdd_phases` in `git_config.py`) is itself **marked DEPRECATED** in the schema docstrings: "DEPRECATED: Use workflow phases from workphases.yaml instead."

The rename (`require_tdd_prefix` → `require_commit_prefix`) and the full `commit_prefix_map` deprecation cleanup belong to the GitConfig migration work — future issue, not #270.

**Conclusion for #270:** Leave `require_tdd_prefix` intact. It is live. The naming concern is out of scope.

---

## Findings

**Removal targets for #270 (confirmed dead — YAML only, no code changes):**

1. **`exit_requires` / `entry_expects` in workphases.yaml** — permanently bypassed since phase_contracts.yaml owns all exit gates. Safe to remove from YAML; `WorkphasesConfig` schema fields remain.

2. **`allowed_prefixes` in policies.yaml** — PolicyEngine.decide() never reads this field; it derives prefixes from GitConfig instead. Safe to remove from YAML; schema field in `operation_policies_config.py` remains.

**Leave intact (not dead):**

3. **Subphase whitelists in workphases.yaml** (`planning: [c1,c2,c3,c4]`, `design: [contracts,flows,schemas]`) — actively used by ScopeEncoder. DRY concern (no wire-up to phase_contracts.yaml) is issue #271 scope.

4. **`require_tdd_prefix` in policies.yaml** — live, used in PolicyEngine.decide(). Naming concern + deprecated dependency (`commit_prefix_map`) is future GitConfig migration work.

## Open Questions

- ✅ Subphase whitelists dead? NO — ScopeEncoder reads them actively (design decision A5)
- ✅ `require_tdd_prefix` TDD-only? NO — phase-blind check on all commits; but depends on deprecated `commit_prefix_map`
- ✅ Tests asserting `exit_requires`/`entry_expects` from real YAML? NO — `test_force_phase_transition_tool.py` builds its own inline YAML fixtures; schema field stays → no breakage
- ✅ Tests asserting `allowed_prefixes` from real YAML? YES — `tests/mcp_server/config/test_operation_policies.py` lines 50-51 assert `"red:" in commit.allowed_prefixes` and `"green:" in commit.allowed_prefixes`. These will fail when field is removed from policies.yaml. **Must fix as part of #270.**


## Related Documentation
- **[mcp_server/managers/phase_state_engine.py (lines 96-97, 228-230, 415-436)][related-1]**
- **[mcp_server/config/schemas/workphases.py (lines 30-46)][related-2]**
- **[mcp_server/config/schemas/operation_policies_config.py (lines 33, 59)][related-3]**
- **[tests/mcp_server/unit/managers/test_deliverable_checker.py][related-4]**
- **[tests/mcp_server/config/test_operation_policies.py][related-5]**

<!-- Link definitions -->

[related-1]: mcp_server/managers/phase_state_engine.py (lines 96-97, 228-230, 415-436)
[related-2]: mcp_server/config/schemas/workphases.py (lines 30-46)
[related-3]: mcp_server/config/schemas/operation_policies_config.py (lines 33, 59)
[related-4]: tests/mcp_server/unit/managers/test_deliverable_checker.py
[related-5]: tests/mcp_server/config/test_operation_policies.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |