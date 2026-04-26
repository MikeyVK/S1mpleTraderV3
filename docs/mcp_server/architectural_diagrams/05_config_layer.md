<!-- docs/mcp_server/architectural_diagrams/05_config_layer.md -->
<!-- template=architecture version=8b924f78 created=2026-03-13T19:06Z updated=2026-03-13 -->
# Config Layer

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-03-13

---

## Purpose

Show the config layer: which configuration files exist, where they live, and which components
load them.

## Scope

**In Scope:** `mcp_server/config/` Python modules, `.st3/` YAML files, load relationships

**Out of Scope:** Pydantic schema detail, template system (`scaffolding/`)

---

## 1. Two Config Domains

Two distinct configuration domains exist side by side. The Python domain contains stable
server-wide settings; the YAML domain contains per-project, per-branch configuration that
changes without server restarts.

```mermaid
graph TD
    subgraph Python Config
        SC["mcp_server/config/<br/>16 modules<br/>(Pydantic BaseSettings)"]
        SC --> GC["git_config.py"]
        SC --> QC["quality_config.py"]
        SC --> WF["workflows.py"]
        SC --> SET["settings.py<br/>(server root)"]
    end
    subgraph YAML Config
        ST3[".st3/"]
        ST3 --> ENF["enforcement.yaml<br/>(enforcement rules)"]
        ST3 --> PC["phase_contracts.yaml<br/>(exit gates per phase)"]
        ST3 --> ART["artifacts.yaml<br/>(scaffold registry)"]
        ST3 --> WFY["workflows.yaml<br/>(phase definitions)"]
    end

    Managers["managers/"] -->|"constructor injection"| SC
    Managers -->|"runtime load"| ST3
```

Changes to `.st3/` YAML files take effect without a server restart. Changes to
`mcp_server/config/` require a restart (or `restart_server` in dev).

---

## 2. Load Relationships

| Consumer | Loads from Python config | Loads from YAML |
|----------|--------------------------|-----------------|
| `PhaseStateEngine` | `WorkflowsConfig` | `phase_contracts.yaml`, `workflows.yaml` |
| `EnforcementRunner` | — | `enforcement.yaml` |
| `ArtifactManager` | `ArtifactRegistryConfig` | `artifacts.yaml` |
| `ProjectManager` | `ProjectStructureConfig` | `workflows.yaml` |
| `GitManager` | `GitConfig` | — |
| `QAManager` | `QualityConfig` | — |

---

## Constraints & Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Two config domains intentionally separated | Python config for deployment settings; YAML for project behaviour | Single YAML for everything (loses type-safety) |
| Constructor injection for Python config | Managers are testable without global state | `from mcp_server.config import settings` everywhere |

---

## Known Architectural Issues

| ID | Component | Issue | Severity |
|----|-----------|-------|----------|
| RC-6 | `phase_contracts.yaml` | Hardcoded `docs/development/issue257/planning.md` and `design.md` — works only for issue #257, breaks for every other branch | High |

---

## Related Documentation

- **[docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md][related-1]**
- **[docs/mcp_server/architectural_diagrams/04_enforcement_layer.md][related-2]**

[related-1]: docs/mcp_server/architectural_diagrams/02_workflow_state_subsystem.md
[related-2]: docs/mcp_server/architectural_diagrams/04_enforcement_layer.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-13 | Agent | Initial draft |
