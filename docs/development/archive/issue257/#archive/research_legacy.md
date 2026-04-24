<!-- docs\development\issue257\research.md -->
<!-- template=research version=8b7bb3ab created=2026-03-03T14:21Z updated= -->
# Reorder workflow phases: research ÔåÆ design ÔåÆ planning ÔåÆ tdd

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

The current workflow phase order (research ÔåÆ planning ÔåÆ design ÔåÆ tdd) forces full TDD cycle planning before design is complete. This means the agent must commit to specific deliverables, file names, and test structures without knowing the actual design. The planning_deliverables.design sub-key is a code-level symptom: it pre-declares what design should produce during planning ÔÇö which is semantically backwards.

## Research Goals

- Establish correct epistemic ordering: research (what) ÔåÆ design (how) ÔåÆ planning (detailed breakdown) ÔåÆ tdd (execute)
- Define what research.md must contain as a bridge to design: measurable expected results / KPIs
- Determine exact code changes needed to swap planning and design in the phase state machine
- Identify and remove the now-redundant planning_deliverables.design sub-key
- Ensure no breaking changes to existing branch state, TDD cycle history, or MCP tool signatures

---

## Background

Analysis of the phase state machine (issue #253 prep session, 2026-03-03). The coupling was found to be shallow: workflow ordering is 100% config-driven via workflows.yaml + validate_transition() index logic. The only hardcoded phase-name references in phase_state_engine.py are exit hooks (fired by name, not position) and on_exit_planning_phase() which validates planning_deliverables. project_manager.py contains _phase_entry_keys = {"design", "validation", "documentation"} and _known_phase_keys which treat design as a sub-key of planning_deliverables.

---

## Findings

1. **Transition ordering** ÔÇö purely config-driven (`workflows.yaml` list). Swapping two entries is sufficient for ordering enforcement. `WorkflowConfig.validate_transition()` uses `phases.index()` ÔÇö no hardcoded phase names.

2. **Exit hooks** ÔÇö fired by phase name, not position. The `if from_phase == "planning":` chain in `transition()` survives a swap intact semantically. However, see finding #6 for the structural problem.

3. **`planning_deliverables.design` sub-key** ÔÇö declared in `project_manager._known_phase_keys` and `_phase_entry_keys`; validated in `on_exit_planning_phase()` loop and `on_exit_design_phase()`. After the reorder, design no longer needs to be a sub-key of planning_deliverables. `on_exit_design_phase()` can be simplified: it currently reads `planning_deliverables.design` which is the backwards dependency we are removing.

4. **research.md exit gate** ÔÇö currently only checks file existence via `file_glob`. Adding a heading-presence check for `## Expected Results` would create a semantic bridge from research to design. Machine-verifiable via regex on the file content.

5. **design exit gate** ÔÇö currently absent. A `file_glob` gate on a design document (e.g., `docs/development/issue{issue_number}/design.md`) would create a hard gate before planning can start.

6. **OCP violation in `transition()`** ÔÇö the `if from_phase == "planning": ... if from_phase == "research": ...` if-chain is closed to extension: adding a new phase requires modifying this method. Correct pattern: registry dict `{phase_name: hook_callable}` populated at class level.

7. **SRP violation: God Class** ÔÇö `PhaseStateEngine` (869 lines) has at least 5 distinct responsibilities: (a) state persistence (atomic write), (b) transition validation + hook dispatch, (c) exit/entry hook implementations (~150 lines, 6 methods), (d) state reconstruction from git (Mode 2), (e) TDD cycle lifecycle management. Per CODE_STYLE anti-patterns: "God classes ÔÇö classes with too many responsibilities".

8. **DIP violation** ÔÇö `DeliverableChecker` is directly instantiated in 4 hook methods (`checker = DeliverableChecker(workspace_root=self.workspace_root)`), coupling the hook logic to a concrete class. Should be injected or provided via factory.

9. **Duplication** ÔÇö `on_exit_validation_phase()`, `on_exit_documentation_phase()`, and `on_exit_design_phase()` are structurally identical: read `planning_deliverables.<phase>.deliverables`, iterate, call `checker.check()`. After removing the `design` sub-key, validation and documentation remain as candidates for a shared `_run_phase_deliverable_gate(phase_key)` helper.

10. **f-string logging** ÔÇö `logger.info(f"...")` used throughout. CODE_STYLE and Python logging best practices require `logger.info("msg %s", var)` for lazy evaluation.

11. **Issue boundary ÔÇö scope of #257 vs. follow-up issues:**

    | Scope | Issue | Epic |
    |---|---|---|
    | PSE OCP registry + `heading_present` gate (unconditional `## Expected Results` on all research-bearing workflows) + phase reorder + design gate + planning_deliverables.design removal + SRP/DIP/DRY/logging fixes | **#257** (this issue) | ÔÇö |
    | `sections.yaml` SSOT + `workflows.yaml phase_contracts` + `WorkflowConfig`/`WorkphasesConfig` models + PSE `content_contract` gate handler ÔÇö full per-workflow content enforcement | **#258** | Epic #49 |
    | `ArtifactManager` sections injection from workflow contract + `research.md.jinja2` (and other phase doc templates) refactored to iterate injected sections list ÔÇö workflow-aware scaffold generation | **#259** | Epic #73 |

    **Rationale:** #257 delivers the OCP registry infrastructure that makes `content_contract` a pluggable gate type ÔÇö without it, #258 cannot land. #259 depends on `sections.yaml` from #258. The boundary is strict: no `sections.yaml`, no `phase_contracts`, no template changes in this issue.

## Open Questions

- Ô£à Should research.md enforce `## Expected Results` via heading-presence check or via a separate `expected_results.yaml` file? ÔåÆ **Heading-presence check in the existing research.md file** (regex on file content). A separate YAML file is over-engineering for now; KPI schema can be formalized in a future issue if machine-verifiability in the validation phase becomes a requirement.
- Ô£à Should `on_exit_design_phase()` gain a new hard gate (file_glob on design doc), or is the existing optional deliverables check sufficient? ÔåÆ **file_glob gate** on `docs/development/issue{issue_number}/design.md`. The optional deliverables check from `planning_deliverables.design` is being removed entirely.
- ÔØô What is the minimal schema for expected_results that makes KPIs machine-verifiable in the validation phase? ÔåÆ Deferred to future issue. For now: heading presence only.
- ÔØô What happens to existing branches that have `planning_deliverables.design` already saved? Are there any such branches? ÔåÆ Needs investigation. Likely none in practice (no current active branches); forward-only: new branches get new schema.
- ÔØô Should the `refactor` workflow (which has no design phase) remain unchanged, or also gain an expected_results gate on research? ÔåÆ **Gets the gate unconditionally.** All workflows with a research phase (feature, bug, refactor, epic) require `## Expected Results`. The absence of a design phase makes this gate *more* important for refactor, not less ÔÇö it is the only structured bridge from research to planning. `hotfix` and `docs` have no research phase ÔÇö the gate is never triggered for them.

---

## Expected Results

> Measurable outcomes that define "done" for this issue. Used as input for design and validation.

### KPI 1 ÔÇö Phase order correct in all workflows
- `feature` workflow phases list: `design` appears before `planning` (index of `design` < index of `planning`)
- `bug` workflow phases list: same constraint
- `refactor` workflow: unchanged (no design phase)
- `hotfix` workflow: unchanged (no design phase)
- **Verification:** `grep -A10 "feature:" .st3/workflows.yaml` shows `design` before `planning`

### KPI 2 ÔÇö workphases.yaml gates correctly configured
- `research.exit_requires`: contains a `heading_present` check for `## Expected Results` in the research file
- `design.exit_requires`: contains a `file_glob` check for `docs/development/issue{issue_number}/design.md`
- `planning.exit_requires`: unchanged ÔÇö still requires `planning_deliverables`
- **Verification:** `WorkphasesConfig.get_exit_requires("research")` returns entry with type `heading_present`

### KPI 3 ÔÇö `planning_deliverables.design` sub-key removed
- `ProjectManager._known_phase_keys` does **not** contain `"design"`
- `ProjectManager._phase_entry_keys` does **not** contain `"design"`
- `on_exit_planning_phase()` loop iterates only `("validation", "documentation")`
- `on_exit_design_phase()` no longer reads `planning_deliverables.design`; uses file_glob gate instead
- **Verification:** passing any `planning_deliverables` dict with a `"design"` key raises `ValueError: Unknown key 'design'`

### KPI 4 ÔÇö OCP: exit hook dispatch uses registry, not if-chain
- `transition()` method contains no `if from_phase == "..."` comparisons
- A `_exit_hooks: dict[str, Callable]` registry (or equivalent) maps phase names to hook callables
- Adding a new phase exit hook requires only adding one entry to the registry (no method modification)
- **Verification:** `grep "if from_phase" mcp_server/managers/phase_state_engine.py` returns 0 matches

### KPI 5 ÔÇö DIP: `DeliverableChecker` not directly instantiated in hook methods
- `DeliverableChecker` instantiated once (constructor injection or lazy property), not 4├ù in hook bodies
- **Verification:** `grep "DeliverableChecker(workspace" mcp_server/managers/phase_state_engine.py` returns Ôëñ1 match

### KPI 6 ÔÇö Duplication eliminated: shared deliverable gate helper
- `on_exit_validation_phase()` and `on_exit_documentation_phase()` delegate to a shared private method
- No copy-paste of the `plan.get(...).get("deliverables", [])` + checker loop
- **Verification:** the two methods each contain Ôëñ3 lines of own logic

### KPI 7 ÔÇö f-string logging eliminated
- No `logger.info(f"...")` or `logger.warning(f"...")` in `phase_state_engine.py`
- **Verification:** `grep "logger\.\w*(f\"" mcp_server/managers/phase_state_engine.py` returns 0 matches

### KPI 8 ÔÇö No regression
- All tests passing: `pytest` exits with code 0
- Minimum 2107 tests collected (no tests deleted)


---


## Related Documentation
- **[docs/development/issue253/research.md][related-1]**
- **[docs/development/issue257/research_sections_config_architecture.md][related-2]**
- **[mcp_server/managers/phase_state_engine.py][related-3]**
- **[mcp_server/managers/project_manager.py][related-4]**
- **[.st3/workflows.yaml][related-5]**
- **[.st3/workphases.yaml][related-6]**
- **[GitHub Issue #258 ÔÇö sections.yaml + phase_contracts + PSE content_contract gate (Epic #49)][related-7]**
- **[GitHub Issue #259 ÔÇö ArtifactManager sections injection + workflow-aware template rendering (Epic #73)][related-8]**

<!-- Link definitions -->

[related-1]: docs/development/issue253/research.md
[related-2]: docs/development/issue257/research_sections_config_architecture.md
[related-3]: mcp_server/managers/phase_state_engine.py
[related-4]: mcp_server/managers/project_manager.py
[related-5]: .st3/workflows.yaml
[related-6]: .st3/workphases.yaml
[related-7]: https://github.com/MikeyVK/S1mpleTraderV3/issues/258
[related-8]: https://github.com/MikeyVK/S1mpleTraderV3/issues/259

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
