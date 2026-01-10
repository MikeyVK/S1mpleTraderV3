# Issue #54 Design: Config Foundation Components

**Status:** DRAFT  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Date:** 2026-01-10  
**Issue:** #54 - Config: Scaffold Rules Configuration  
**Phase:** Design  
**Parent:** Epic #49 - MCP Platform Configurability

---

## Executive Summary

**Purpose:** Detailed component designs for config foundation implementation. Each design maps to implementation phases from planning.md with concrete schemas, interfaces, and behavioral specifications.

**Approach:** Four design phases matching planning.md build order:
1. **Phase 1:** Foundation configs + models (no dependencies)
2. **Phase 2:** Structure layer + DirectoryPolicyResolver (depends on Phase 1)
3. **Phase 3:** PolicyEngine refactor (depends on Phases 1+2)
4. **Phase 4:** Tool integration - ScaffoldComponentTool (depends on Phases 1+2)

**Design Philosophy:**
- Contracts first: Define interfaces before implementation
- Type safety: Pydantic models for all configs
- Fail-fast: Validation at config load time
- SSOT: Cross-config validation enforces referential integrity
- SRP: Each component owns ONE responsibility

---

## Related Documents

- [research.md](./research.md) - Research findings and scope decisions
- [planning.md](./planning.md) - Implementation strategy and build order
- [CORE_PRINCIPLES.md](../../architecture/CORE_PRINCIPLES.md) - Architectural principles
- workflows.yaml (Issue #50) - Phase definitions
- validation.yaml (Issue #52) - Template validation rules

---

## Phase 1 Design: Foundation Configs and Models

**Goal:** Create foundation configs and models with NO dependencies on other Issue #54 components.

**Components:** 
- `.st3/components.yaml` + `ComponentRegistryConfig` (WAT domain)
- `.st3/policies.yaml` + `OperationPoliciesConfig` (WANNEER domain)

**Build Order:** Both can be built in parallel (no interdependencies)

### 1.1 components.yaml Schema Design

[Detailed component registry schema - will be added in next edit]

### 1.2 ComponentRegistryConfig Model Design

[Python model design with Pydantic - will be added in next edit]

### 1.3 policies.yaml Schema Design

[Detailed operation policies schema - will be added in next edit]

### 1.4 OperationPoliciesConfig Model Design

[Python model design with Pydantic - will be added in next edit]

### 1.5 Phase 1 Test Strategy

[Test coverage requirements - will be added in next edit]

---

## Phase 2 Design: Structure Layer (DirectoryPolicyResolver)

**Goal:** Create project structure config and directory policy resolution utility.

**Components:**
- `.st3/project_structure.yaml` + `ProjectStructureConfig` (WAAR domain)
- `DirectoryPolicyResolver` utility (path matching, inheritance)

**Dependencies:** ComponentRegistryConfig (for cross-validation)

### 2.1 project_structure.yaml Schema Design

[Detailed directory structure schema - will be added in next edit]

### 2.2 ProjectStructureConfig Model Design

[Python model design with cross-validation - will be added in next edit]

### 2.3 DirectoryPolicyResolver Interface Design

[Utility class design with lookup methods - will be added in next edit]

### 2.4 Inheritance Resolution Algorithm

[Path matching and parent inheritance logic - will be added in next edit]

### 2.5 Phase 2 Test Strategy

[Test coverage requirements - will be added in next edit]

---

## Phase 3 Design: Integration (PolicyEngine Refactor)

**Goal:** Refactor PolicyEngine to use configs instead of hardcoded rules.

**Components:**
- `PolicyEngine` refactor (decision service)
- `PolicyDecision` dataclass (decision result)

**Dependencies:** OperationPoliciesConfig, DirectoryPolicyResolver

### 3.1 PolicyEngine Interface Design

[Class interface with decide() method - will be added in next edit]

### 3.2 PolicyDecision Dataclass Design

[Decision result structure - will be added in next edit]

### 3.3 Decision Algorithm Design

[How PolicyEngine uses configs to make decisions - will be added in next edit]

### 3.4 Audit Trail Design

[Decision logging format - will be added in next edit]

### 3.5 Phase 3 Test Strategy

[Behavior parity tests (not needed, PolicyEngine unused) - will be added in next edit]

---

## Phase 4 Design: Tool Integration (ScaffoldComponentTool)

**Goal:** Refactor ScaffoldComponentTool to use ComponentRegistryConfig.

**Components:**
- `ScaffoldComponentTool` refactor (validation changes only)

**Dependencies:** ComponentRegistryConfig, DirectoryPolicyResolver

### 4.1 ScaffoldComponentTool Changes

[Modified methods and validation logic - will be added in next edit]

### 4.2 Component Type Validation

[How tool validates component_type against config - will be added in next edit]

### 4.3 Path Validation

[How tool uses DirectoryPolicyResolver - will be added in next edit]

### 4.4 Phase 4 Test Strategy

[Integration tests (scaffolding still works) - will be added in next edit]

---

## Cross-Cutting Concerns

### Error Handling Strategy

[ConfigError design, error messages - will be added in next edit]

### Performance Considerations

[Config loading time, lookup performance - will be added in next edit]

### Logging and Observability

[What to log, audit trail format - will be added in next edit]

---

## Implementation Notes

**Priority:** Follow build order strictly (dependencies first)

**Testing:** TDD approach (red → green → refactor)

**Documentation:** Update AGENT_PROMPT.md after each phase

**Migration:** No breaking changes (PolicyEngine loads but doesn't enforce)

---

## Open Questions

[Questions that arose during design phase - to be filled during design work]

---

**Next:** Begin detailed design for Phase 1 components