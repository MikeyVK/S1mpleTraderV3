<!-- docs\development\issue432\design.md -->
<!-- template=design version=5827e841 created=2026-07-18T19:27Z updated= -->
# Graceful Server Initialization

**Status:** APPROVED
**Version:** 1.0  
**Last Updated:** 2026-07-18

---

## 1. Context & Requirements

### 1.1. Problem Statement

Vulnerabilities in the MCP Server's startup sequence cause hard crashes on missing packages, missing config versions, or template mismatches. This prevents the server from returning graceful error messages to the agent, leading to dead tools and unrecoverable initialization failures.

### 1.2. Requirements

**Functional:**
- Server must boot into a `DegradedMCPServer` state when `ConfigError` or `FileNotFoundError` is raised during global bootstrap.
- The `DegradedMCPServer` must register the `health_check` tool.
- The `health_check` tool must cleanly receive the degradation status and reason via constructor dependency injection.
- Template version validation must be deferred to the `ArtifactManager` (specifically the `TemplateScaffolder`) to prevent a single bad template from crashing the global bootstrap.

**Non-Functional:**
- Must adhere to Config-First: Pydantic schemas' `Literal['1.0.0']` constraints are preserved as structural contract.
- Must adhere to Fail-Fast: True infrastructure errors still crash; only domain config errors trigger degraded mode.
- Must adhere to SOLID principles (DIP, ISP) for dependency injection in the `health_check` tool.

### 1.3. Constraints

None

---

## 2. Chosen Design

**Decision:** Implement `DegradedMCPServer` in `cli.py` handling `ConfigError` and `FileNotFoundError`. Reuse `health_check` tool with constructor-injected degradation cause. Retain `Literal` version constraints in Pydantic schemas. Defer template version validation to `TemplateScaffolder`.

**Rationale:** This design strictly obeys ARCHITECTURE_PRINCIPLES.md (Fail-Fast for infra, Degraded for domain), maintains Schema Cohesion, and safely isolates config failures from the MCP transport layer.

### 2.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use `health_check` tool | Avoids introducing a new tool, reuses existing `UNHEALTHY` status. |
| Keep `Literal` schema versions | Schema versions are structural type tags tightly coupled to the Python fields, not floating business logic. Pushing this to the loader violates SRP and Cohesion. |
| Defer template validation to `TemplateScaffolder` | Decouples specific scaffold template failures from global server startup. Uses existing `TemplateScaffolder` mechanisms to raise specific tool domain errors instead of crashing the server. |

### 2.2. Concrete Interface Contracts

#### A. HealthCheckTool and DegradedMCPServer
The degradation cause is statically injected in the constructor by `cli.py`.
The design reuses the existing `HealthStatus.UNHEALTHY` status from `mcp_server/schemas/tool_outputs.py`.

```python
# In mcp_server/schemas/tool_outputs.py
class HealthCheckOutput(BaseToolOutput):
    status: HealthStatus = HealthStatus.HEALTHY
    reason: str | None = None  # Optional error details

# In mcp_server/tools/health_tools.py
class HealthCheckTool(ICoreTool[HealthCheckInput, HealthCheckOutput]):
    def __init__(
        self, 
        override_status: HealthStatus | None = None,
        override_reason: str | None = None
    ) -> None:
        self._override_status = override_status
        self._override_reason = override_reason
```

#### B. Deferred Template Version Validation
The design leverages the existing template introspection capabilities in `TemplateScaffolder` to validate the `TEMPLATE_METADATA` version. To prevent unnecessary deep inspection of invalid or incompatible templates, the exact validation flow is:
1. **Version Check First:** The `TemplateScaffolder.validate()` method reads the `TEMPLATE_METADATA` (via `TemplateAnalyzer.extract_metadata()`) as its first step and compares the `version` with the expected `template_version` from the `ArtifactRegistryConfig` for the respective `artifact_type`.
2. **Exception flow:** Upon a mismatch, the process stops immediately and the scaffolder raises a `ValidationError(f"Template version mismatch: ...")`. No deep variable or inheritance inspection is performed.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-18 | Agent | Initial draft |
| 1.1 | 2026-07-18 | Agent | Interface contracts finalized |