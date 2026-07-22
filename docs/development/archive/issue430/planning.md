<!-- docs\development\issue430\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-19T06:55:00Z updated=2026-07-19T07:00:00Z -->
# Rename human_approval parameter to human_approval_message in force transition tools

**Status:** APPROVED  
**Version:** 1.1  
**Last Updated:** 2026-07-19

---

## Purpose

Slice the renaming of human_approval to human_approval_message into safe TDD implementation cycles.

## Scope

**In Scope:**
Input/output models of force_phase_transition and force_cycle_transition tools; PhaseStateEngine signatures; state.json serialization; active documentation (AGENTS.md); unit and integration tests.

**Out of Scope:**
Historical dev archive files under docs/development/archive/

---

## Summary

This document outlines the planning for renaming the human_approval parameter to human_approval_message. The plan slices the work into 4 sequential cycles (manager layer, phase tools layer, cycle tools layer, and documentation alignment), ensuring no regressions and complete renaming with zero lingering references.

All cycles are subject to strict type checking (`mypy`/`pyright` PASS) and validation via `run_quality_gates` before phase commits.

---

## Dependencies

- No external dependencies. All cycles run sequentially.

---

## TDD Cycles


### Cycle 1: C_ENGINE.1

**Goal:** Update core State Engine manager (PhaseStateEngine) parameter to human_approval_message with a temporary deprecated fallback to human_approval. Include a unit test validating that legacy state.json files containing 'human_approval' are loaded successfully.

**Tests:**
- tests/mcp_server/unit/managers/test_phase_state_engine.py
- tests/mcp_server/integration/test_phase_state_engine_concurrent.py
- tests/mcp_server/integration/test_issue39_cross_machine.py

**Success Criteria:**
Direct calls to PhaseStateEngine transition/force_transition methods accept human_approval_message, transitions/cycle histories serialise to human_approval_message, legacy state.json files parse successfully, and all affected unit/integration tests pass with no regressions.



### Cycle 2: C_PHASE_TOOLS.2

**Goal:** Rename parameters in phase tools and inputs/outputs, remove PhaseStateEngine deprecated phase-level fallback parameters, and update all phase transition test suites. Include an explicit field validator that rejects boolean input for human_approval_message.

**Tests:**
- tests/mcp_server/unit/tools/test_transition_phase_tool.py
- tests/mcp_server/unit/tools/test_force_phase_transition_tool.py
- tests/mcp_server/tools/test_a2_schema_constraints.py
- tests/mcp_server/unit/test_server.py

**Success Criteria:**
Phase transition tools expose human_approval_message and enforce valid inputs (rejecting booleans). All phase tool tests pass.

**Dependencies:** C_ENGINE.1


### Cycle 3: C_CYCLE_TOOLS.3

**Goal:** Rename parameters in cycle tools and inputs/outputs, remove PhaseStateEngine deprecated cycle-level fallback parameters, update all cycle transition test suites, and ensure no lingering references to human_approval exist in Python code. Include an explicit field validator that rejects boolean input for human_approval_message.

**Tests:**
- tests/mcp_server/unit/tools/test_cycle_tools.py
- tests/mcp_server/unit/tools/test_cycle_tools_business_logic.py
- tests/mcp_server/unit/tools/test_extra_forbid.py

**Success Criteria:**
Cycle transition tools expose human_approval_message (rejecting booleans). A grep search for human_approval in mcp_server/ and tests/ returns 0 results for active code/tests.

**Dependencies:** C_ENGINE.1


### Cycle 4: C_DOCS.4

**Goal:** Update all active agent guidelines, reference guides, and system prompts to reflect human_approval_message instead of human_approval.

**Tests:**

**Success Criteria:**
All active instruction files and reference documentation are updated. A grep search for human_approval in active docs returns 0 results.

**Dependencies:** C_PHASE_TOOLS.2, C_CYCLE_TOOLS.3

---

## Risks & Mitigation

- **Risk:** LLM agents call the deprecated human_approval name during the migration.
  - **Mitigation:** Temporary deprecated fallback parameters are kept in PhaseStateEngine during Cycles 1 and 2/3 to prevent errors during the transition, and then fully cleaned up.
- **Risk:** Lingering references of human_approval in active code/documentation.
  - **Mitigation:** Verify with a workspace-wide grep search at the end of Cycle 3 and Cycle 4 to ensure zero results in active directories.
- **Risk:** Lax Pydantic type coercion allows boolean `true`/`false` values to be implicitly converted to `"True"`/`"False"` strings and pass length validators.
  - **Mitigation:** Implement explicit Pydantic `@field_validator` checks on tool inputs to reject boolean types.

## Related Documentation
- **[docs/development/issue430/research.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue430/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-19 | Agent | Initial draft |
| 1.1 | 2026-07-19 | Agent | Incorporate QA plan-verifier feedback: legacy state compatibility test, strict boolean validator, and explicit quality gates. |
