<!-- docs/mcp_server/architectural_diagrams/03_tool_layer.md -->
<!-- template=architecture version=8b924f78 created=2026-03-13T19:05Z updated=2026-03-13 -->
# Tool Layer

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-03-13

---

## Purpose

Show the tool layer: all 51 MCP tools grouped by file, their base class hierarchy, naming
conventions, and existing inconsistencies.

## Scope

**In Scope:** `tools/` directory, BaseTool hierarchy, MCP tool names, file name conventions

**Out of Scope:** Tool implementation detail, manager-internal logic

---

## 1. Base Class Hierarchy

Every tool inherits from `BaseTool`. The `_BaseTransitionTool` sub-base provides shared
logic for both phase and cycle transition tools. The `EnforcementRunner` wraps `execute()`
as a pre/post-hook at the server level — tools themselves are unaware of enforcement.

```mermaid
graph TD
    BT["BaseTool<br/>(tools/base.py)"]
    BBT["_BaseTransitionTool<br/>(phase_tools.py)"]
    TP["TransitionPhaseTool"]
    FP["ForcePhaseTransitionTool"]
    TC["TransitionCycleTool"]
    FC["ForceCycleTransitionTool"]
    ER["EnforcementRunner<br/>(pre/post hooks)"]

    BT --> BBT
    BBT --> TP
    BBT --> FP
    BBT --> TC
    BBT --> FC
    ER -.->|"wraps execute()"| BT

    style BBT fill:#ffe,color:#000
```

The yellow `_BaseTransitionTool` is defined in `phase_tools.py` but imported by `cycle_tools.py` —
a visibility mismatch (see Known Issues).

---

## 2. Tool Groups by File

All 51 tools grouped by source file. Files marked (⚠) have naming convention violations.

```mermaid
graph LR
    subgraph Git
        GT["git_tools.py<br/>13 tools"]
        GA["git_analysis_tools.py<br/>2 tools"]
        GF["git_fetch_tool.py ⚠<br/>1 tool"]
        GP["git_pull_tool.py ⚠<br/>1 tool"]
    end
    subgraph Workflow
        PT["phase_tools.py<br/>2 tools"]
        CT["cycle_tools.py<br/>2 tools"]
        PJ["project_tools.py<br/>4 tools"]
    end
    subgraph GitHub
        IT["issue_tools.py<br/>5 tools"]
        LT["label_tools.py<br/>5 tools"]
        MT["milestone_tools.py<br/>3 tools"]
        PR["pr_tools.py<br/>3 tools"]
    end
    subgraph Quality
        QT["quality_tools.py<br/>1 tool"]
        TT["test_tools.py<br/>1 tool"]
        VT["validation_tools.py<br/>2 tools"]
        TV["template_validation_tool.py ⚠<br/>1 tool"]
    end
```

Most files follow the `*_tools.py` (plural) convention. The four ⚠ files deviate.

---

## Constraints & Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| EnforcementRunner as pre/post hook at server level | Tools need not know about enforcement; clean separation of concerns | Enforcement logic inside each tool (duplication) |
| All tools via BaseTool | Uniform `execute()` interface; consistent `ToolResult` response shape | Standalone functions (no polymorphism, harder to wrap) |

---

## Known Architectural Issues

| ID | Component | Issue | Severity |
|----|-----------|-------|----------|
| KPI-11 | `_BaseTransitionTool` | Underscore prefix signals module-private, but imported by `cycle_tools.py` from `phase_tools.py` | Medium |
| KPI-11 | `git_fetch_tool.py` | Singular filename vs. `*_tools.py` plural convention for all other files | Low |
| KPI-11 | `git_pull_tool.py` | Same singular/plural deviation | Low |
| KPI-11 | `template_validation_tool.py` | Singular filename deviation | Low |
| KPI-12 | MCP names | `transition_phase` / `force_phase_transition` — word order is crossed vs. `transition_cycle` / `force_cycle_transition` | Medium |

---

## Related Documentation

- **[docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md][related-1]**
- **[docs/mcp_server/architectural_diagrams/04_enforcement_layer.md][related-2]**
- **[docs/mcp_server/architectural_diagrams/08_naming_landscape.md][related-3]**

[related-1]: docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md
[related-2]: docs/mcp_server/architectural_diagrams/04_enforcement_layer.md
[related-3]: docs/mcp_server/architectural_diagrams/08_naming_landscape.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-13 | Agent | Initial draft |
