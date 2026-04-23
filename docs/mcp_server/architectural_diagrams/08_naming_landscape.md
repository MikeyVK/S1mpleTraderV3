<!-- docs/mcp_server/architectural_diagrams/08_naming_landscape.md -->
<!-- template=architecture version=8b924f78 created=2026-03-13T19:07Z updated=2026-03-13 -->
# Naming Landscape

**Status:** CURRENT
**Version:** 1.1
**Last Updated:** 2026-04-23

---

## Purpose

Overview of all file → class → MCP tool name combinations and the naming inconsistencies
identified across the tool layer.

## Scope

**In Scope:** All tool files, class names, MCP tool names, naming patterns

**Out of Scope:** Implementation detail, non-tool modules

---

## 1. Naming Conventions

Three conventions apply across the tool layer. Violations are marked ⚠.

| Convention | Rule | Example ✅ | Violation ⚠ |
|------------|------|------------|-------------|
| File name | `*_tools.py` (plural) | `git_tools.py` | `git_fetch_tool.py` |
| Class name | `PascalCase` + domain noun | `TransitionPhaseTool` | — |
| MCP tool name | `snake_case` verb_noun, consistent word order | `transition_cycle` | `force_phase_transition` ↔ `force_cycle_transition` |
| Base class visibility | `_` prefix = module-private | `_MyInternal` | `_BaseTransitionTool` (imported cross-module) |

---

## 2. File → Class → MCP Name Matrix

Full mapping of all tool files. ⚠ marks known inconsistencies.

| File | Class | MCP Tool Name | Issue |
|------|-------|---------------|-------|
| `git_tools.py` | `CreateBranchTool` | `create_branch` | — |
| `git_tools.py` | `GitStatusTool` | `git_status` | — |
| `git_tools.py` | `GitCommitTool` | `git_add_or_commit` | — |
| `git_tools.py` | `GitRestoreTool` | `git_restore` | — |
| `git_tools.py` | `GitCheckoutTool` | `git_checkout` | — |
| `git_tools.py` | `GitPushTool` | `git_push` | — |
| `git_tools.py` | `GitMergeTool` | `git_merge` | — |
| `git_tools.py` | `GitDeleteBranchTool` | `git_delete_branch` | — |
| `git_tools.py` | `GitStashTool` | `git_stash` | — |
| `git_tools.py` | `GetParentBranchTool` | `get_parent_branch` | — |
| `git_analysis_tools.py` | `GitListBranchesTool` | `git_list_branches` | — |
| `git_analysis_tools.py` | `GitDiffTool` | `git_diff_stat` | Class name differs from MCP name suffix |
| `git_fetch_tool.py` ⚠ | `GitFetchTool` | `git_fetch` | Singular filename |
| `git_pull_tool.py` ⚠ | `GitPullTool` | `git_pull` | Singular filename |
| `phase_tools.py` | `TransitionPhaseTool` | `transition_phase` | — |
| `phase_tools.py` | `ForcePhaseTransitionTool` | `force_phase_transition` ⚠ | Word order crossed |
| `cycle_tools.py` | `TransitionCycleTool` | `transition_cycle` | — |
| `cycle_tools.py` | `ForceCycleTransitionTool` | `force_cycle_transition` ⚠ | Word order crossed |
| `project_tools.py` | `InitializeProjectTool` | `initialize_project` | — |
| `project_tools.py` | `GetProjectPlanTool` | `get_project_plan` | — |
| `project_tools.py` | `SavePlanningDeliverablesTool` | `save_planning_deliverables` | — |
| `project_tools.py` | `UpdatePlanningDeliverablesTool` | `update_planning_deliverables` | — |
| `issue_tools.py` | `CreateIssueTool` | `create_issue` | — |
| `issue_tools.py` | `GetIssueTool` | `get_issue` | — |
| `issue_tools.py` | `ListIssuesTool` | `list_issues` | — |
| `issue_tools.py` | `UpdateIssueTool` | `update_issue` | — |
| `issue_tools.py` | `CloseIssueTool` | `close_issue` | — |
| `label_tools.py` | `ListLabelsTool` | `list_labels` | — |
| `label_tools.py` | `CreateLabelTool` | `create_label` | — |
| `label_tools.py` | `DeleteLabelTool` | `delete_label` | — |
| `label_tools.py` | `RemoveLabelsTool` | `remove_labels` | — |
| `label_tools.py` | `AddLabelsTool` | `add_labels` | — |
| `milestone_tools.py` | `ListMilestonesTool` | `list_milestones` | — |
| `milestone_tools.py` | `CreateMilestoneTool` | `create_milestone` | — |
| `milestone_tools.py` | `CloseMilestoneTool` | `close_milestone` | — |
| `pr_tools.py` | `SubmitPRTool` | `submit_pr` | Replaced deleted public `create_pr` path |
| `pr_tools.py` | `ListPRsTool` | `list_prs` | — |
| `pr_tools.py` | `MergePRTool` | `merge_pr` | — |
| `quality_tools.py` | `RunQualityGatesTool` | `run_quality_gates` | — |
| `test_tools.py` | `RunTestsTool` | `run_tests` | — |
| `validation_tools.py` | `ValidationTool` | `validate_architecture` | Class name is broader than MCP tool name |
| `validation_tools.py` | `ValidateDTOTool` | `validate_dto` | — |
| `template_validation_tool.py` ⚠ | `ValidateTemplateTool` | `validate_template` | Singular filename |
| `scaffold_artifact.py` ⚠ | `ScaffoldArtifactTool` | `scaffold_artifact` | No `_tool` suffix |
| `safe_edit_tool.py` ⚠ | `SafeEditTool` | `safe_edit_file` | No `_tools` plural |
| `code_tools.py` | `CreateFileTool` | `create_file` | — |
| `health_tools.py` | `HealthCheckTool` | `health_check` | — |
| `admin_tools.py` | `RestartServerTool` | `restart_server` | — |
| `discovery_tools.py` | `SearchDocumentationTool` | `search_documentation` | — |
| `discovery_tools.py` | `GetWorkContextTool` | `get_work_context` | — |

---

## 3. Word Order Inconsistency (MCP names)

The phase and cycle tools use a crossed word order pattern:

| Intended pattern | Actual MCP name | Verdict |
|-----------------|-----------------|---------|
| `transition_phase` | `transition_phase` | ✅ |
| `force_transition_phase` | `force_phase_transition` ⚠ | Crossed |
| `transition_cycle` | `transition_cycle` | ✅ |
| `force_transition_cycle` | `force_cycle_transition` ⚠ | Crossed |

Both are internally consistent (phase and cycle mirror each other), but the `force_*`
variants swap verb and domain noun compared to the non-force variants. A rename to
`force_transition_phase` / `force_transition_cycle` would align all four.

---

## Constraints & Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Document naming conventions explicitly | Conventions are followed for ~85% of tools; making them explicit enables automated drift detection | Implicit conventions (already caused the current deviations) |

---

## Known Architectural Issues

| ID | Component | Issue | Severity |
|----|-----------|-------|----------|
| KPI-11 | `git_fetch_tool.py`, `git_pull_tool.py`, `template_validation_tool.py` | Singular filenames deviate from `*_tools.py` convention | Low |
| KPI-11 | `scaffold_artifact.py`, `safe_edit_tool.py` | No `_tools` suffix pattern at all | Low |
| KPI-12 | `force_phase_transition`, `force_cycle_transition` | Word order crossed vs. `transition_phase` / `transition_cycle` | Medium |
| KPI-11 | `_BaseTransitionTool` | Underscore prefix implies module-private; imported cross-module | Medium |

---

## Related Documentation

- **[docs/mcp_server/architectural_diagrams/03_tool_layer.md][related-1]**
- **[docs/development/issue257/GAP_ANALYSE_ISSUE257.md][related-2]**

[related-1]: docs/mcp_server/architectural_diagrams/03_tool_layer.md
[related-2]: docs/development/issue257/GAP_ANALYSE_ISSUE257.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-13 | Agent | Initial draft |
