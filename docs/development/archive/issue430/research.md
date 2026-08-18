<!-- docs\development\issue430\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-19T06:48Z updated= -->
# Rename human_approval parameter to human_approval_message in force transition tools

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-19

---

## Purpose

Investigate the blast radius, dependencies, and compatibility strategy for renaming the human approval parameter to human_approval_message.

## Scope

**In Scope:**
Input/output models of force_phase_transition and force_cycle_transition tools; PhaseStateEngine signatures; state.json serialization; active documentation (AGENTS.md); unit and integration tests.

**Out of Scope:**
Historical dev archive files under docs/development/archive/

---

## Problem Statement

LLM agents frequently pass boolean values (true) to the human_approval parameter in force phase/cycle transition tools, despite descriptions requesting a string approval message. This is due to naming ambiguity where 'human_approval' matches boolean heuristic checks in LLM reasoning.

## Research Goals

- Rename human_approval to human_approval_message to remove ambiguity.
- Ensure all tools, managers, serialization logic, documentation, and test suites are updated and functional.
- Define backward compatibility strategy for state.json transition histories.

---

## Background

Issue #39 introduced forced transitions tracking skip_reason and human_approval for audit trails. Issue #146 added force_cycle_transition. LLM agents often fail to pass a string because the field name 'human_approval' strongly implies a boolean value.

---

## Findings

The transitions and cycle_history lists in BranchState are unstructured list[dict[str, Any]] and are never read back or parsed by key in Python. Therefore, writing 'human_approval_message' instead of 'human_approval' in new entries has zero impact on state.json loading compatibility. Active instruction files (AGENTS.md) and 17 test suites must be updated.

---

## Approved Strategy

Option C: Write the new key 'human_approval_message' to new entries in state.json. Old entries with 'human_approval' will be loaded as-is without errors. No data migration script or Pydantic aliases are required because the lists are write-only audit trails that are never deserialized by key in Python.

---

## Expected Results

1. Tools expose 'human_approval_message' in their JSON schemas. 2. Non-empty string validation is enforced. 3. Existing state.json files load successfully. 4. All 17 test suites pass.

## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-19 | Agent | Initial draft |