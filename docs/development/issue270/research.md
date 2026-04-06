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

**Finding 2 — planning and design subphase whitelists**

Planning defines subphases: [c1, c2, c3, c4]; design defines subphases: [contracts, flows, schemas]. ScopeEncoder validates subphases strictly against workphases.yaml for phases that appear in commit scopes. Planning and design phases use commit_type_hint: docs and generate no subphase tokens in practice — agents commit with P_PLANNING or P_DESIGN, never P_PLANNING_SP_C1. The whitelists are enforced IF used, but they are never used.

Risk consideration: removing them means ScopeEncoder would reject P_PLANNING_SP_C1 as an invalid subphase (since validation would hit an empty list). This is actually stricter, not looser — removal tightens the contract.

**Finding 3 — policies.yaml commit.allowed_prefixes**

The commit operation in policies.yaml has `allowed_prefixes: [red:, green:, refactor:, docs:]`. `OperationPoliciesConfig` schema (operation_policies_config.py line 33) DOES define the field and line 59 has `has_allowed_prefix()` method. However, the regression test (test_policy_engine_config.py) documents explicitly: 'Bug: policies.yaml had red:, green: but GitManager generates test:, feat:. Fix: PolicyEngine derives prefixes from GitConfig.' The field was not removed from the YAML after the policy was changed. `PolicyEngine.decide()` for commit operations calls `_git_config.get_all_prefixes()` instead.

---

## Findings

All three field groups are confirmed dead:

1. **exit_requires / entry_expects in workphases.yaml** — schema parses them, code path exists, but activation condition is permanently false with current phase_contracts.yaml coverage. Safe to remove from YAML only. WorkphasesConfig schema field remains (issue #271 scope).

2. **planning/design subphase whitelists** — never used in commit scopes. Removing tightens the contract (ScopeEncoder would reject any future P_PLANNING_SP_* attempt). Treat as informational-only or remove. Recommendation: remove; add a comment in workphases.yaml if documentation of past intent is desired.

3. **policies.yaml allowed_prefixes** — schema field parses it, has_allowed_prefix() exists in the model, but PolicyEngine.decide() never calls it for commits. Confirmed dead by regression test. Safe to remove from YAML only. Schema field in operation_policies_config.py may stay (out of scope).

## Open Questions

- ❓ Are there any other callers of WorkphasesConfig.get_exit_requires() or get_entry_expects() outside of PSE._legacy_workphases_gate_summary()?
- ❓ Are there tests that assert specific exit_requires/entry_expects values from the YAML fixture (not from code) that would need updating?


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