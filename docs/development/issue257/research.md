<!-- docs\development\issue257\research.md -->
<!-- template=research version=8b7bb3ab created=2026-03-03T14:21Z updated= -->
# Reorder workflow phases: research → design → planning → tdd

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-03

---

## Purpose

Inform the design and planning phases for issue #257; provide input for phase order change and expected_results gate in research exit.

## Scope

**In Scope:**
workflows.yaml phase list order, workphases.yaml exit_requires, phase_state_engine.py exit hooks, project_manager.py schema constants, AGENT_PROMPT.md instructions

**Out of Scope:**
TDD subphase mechanics, validation/documentation phase ordering, MCP tool signatures (no changes needed), existing branch state files

---

## Problem Statement

The current workflow phase order (research → planning → design → tdd) forces full TDD cycle planning before design is complete. This means the agent must commit to specific deliverables, file names, and test structures without knowing the actual design. The planning_deliverables.design sub-key is a code-level symptom: it pre-declares what design should produce during planning — which is semantically backwards.

## Research Goals

- Establish correct epistemic ordering: research (what) → design (how) → planning (detailed breakdown) → tdd (execute)
- Define what research.md must contain as a bridge to design: measurable expected results / KPIs
- Determine exact code changes needed to swap planning and design in the phase state machine
- Identify and remove the now-redundant planning_deliverables.design sub-key
- Ensure no breaking changes to existing branch state, TDD cycle history, or MCP tool signatures

---

## Background

Analysis of the phase state machine (issue #253 prep session, 2026-03-03). The coupling was found to be shallow: workflow ordering is 100% config-driven via workflows.yaml + validate_transition() index logic. The only hardcoded phase-name references in phase_state_engine.py are exit hooks (fired by name, not position) and on_exit_planning_phase() which validates planning_deliverables. project_manager.py contains _phase_entry_keys = {"design", "validation", "documentation"} and _known_phase_keys which treat design as a sub-key of planning_deliverables.

---

## Findings

1. Transition ordering: purely config (workflows.yaml list). Swapping two entries is sufficient for ordering enforcement.
2. Exit hooks: fired by phase name, not position. They survive a swap intact.
3. planning_deliverables.design sub-key: declared in project_manager._known_phase_keys and _phase_entry_keys; validated in on_exit_planning_phase() loop and on_exit_design_phase(). After the reorder, design no longer needs to be a sub-key of planning_deliverables — it has its own phase.
4. research.md exit gate: currently only checks file existence via file_glob. Adding a required '## Expected Results' section (with measurable KPIs) would create a semantic bridge from research to design.
5. design exit gate: currently absent. A file_glob gate on a design document would create a hard gate before planning can start.

## Open Questions

- ❓ Should research.md enforce '## Expected Results' via heading-presence check or via a separate expected_results.yaml file?
- ❓ What is the minimal schema for expected_results that makes KPIs machine-verifiable in the validation phase?
- ❓ Should on_exit_design_phase() gain a new hard gate (file_glob on design doc), or is the existing optional deliverables check sufficient?
- ❓ What happens to existing branches that have planning_deliverables.design already saved? Migration strategy needed?
- ❓ Should the 'refactor' workflow (which has no design phase) remain unchanged, or also gain an expected_results gate on research?


## Related Documentation
- **[docs/development/issue253/research.md][related-1]**
- **[mcp_server/managers/phase_state_engine.py][related-2]**
- **[mcp_server/managers/project_manager.py][related-3]**
- **[.st3/workflows.yaml][related-4]**
- **[.st3/workphases.yaml][related-5]**

<!-- Link definitions -->

[related-1]: docs/development/issue253/research.md
[related-2]: mcp_server/managers/phase_state_engine.py
[related-3]: mcp_server/managers/project_manager.py
[related-4]: .st3/workflows.yaml
[related-5]: .st3/workphases.yaml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |