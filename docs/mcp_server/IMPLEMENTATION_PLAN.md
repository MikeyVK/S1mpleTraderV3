# Consolidate Implementation Plan: Jinja2 Templates & Extensibility

This document combines the findings from the **Gap Analysis** with the detailed **Implementation Strategy**, providing a single source of truth for the upcoming work on the `mcp_server` Jinja2 templates.

## 1. Executive Summary

Our goal is to professionalize the `mcp_server` scaffolding capabilities. We will fill coverage gaps identified in the analysis (Tools, Resources, Standard Patterns) and introduce a flexible, generic mechanism to support future needs without code changes.

**Key Deliverables:**
1.  **New Templates**: A suite of templates for MCP components and standard architecture patterns (based on S1mpleTraderV2).
2.  **Extensibility**: A "Generic" template system allowing generation of *any* file type.
3.  **Documentation Sync**: Aligning automation templates with reference documentation.

---

## 2. Scope & Design Decisions

### 2.1. Gap Analysis Findings
-   **Missing MCP Types**: We lack templates for `Tools` and `Resources`, forcing manual boilerplate.
-   **Missing Architecture Patterns**: Common V2 patterns like `Schemas` (Pydantic), `Interfaces` (Protocol), and `Services` (CQRS-style) are not scaffoldable in V3.
-   **Extensibility**: The current system is hardcoded (`dto`, `worker`, `adapter`). Adding a new type requires modifying Python code.

### 2.2. Service Architecture
Based on the CQRS-like patterns in `DataCommandService` and `DataQueryService`, we will implement **3 distinct service templates**:
1.  **Orchestrator Service**: For high-level coordination.
2.  **Command Service**: For write-heavy operations (validation, transaction, execution).
3.  **Query Service**: For read-heavy operations (optimization, caching).

---

## 3. Implementation Steps

### 3.1. Phase 1: Template Implementation (`mcp_server/templates/components/`)

We will create the following Jinja2 files inheriting from `base/base_component.py.jinja2`:

#### A. MCP Components
-   **`tool.py.jinja2`**: Implements `BaseTool`. Fields: `input_schema`, `execute` stub.
-   **`resource.py.jinja2`**: Implements `read()` and URI handling.

#### B. Architecture Components
-   **`schema.py.jinja2`**: Pydantic models (based on `platform_schema.py`).
-   **`interface.py.jinja2`**: `typing.Protocol` definitions (based on `connectors.py`).
-   **`service_orchestrator.py.jinja2`**: General dependency injection and logic.
-   **`service_command.py.jinja2`**: Transactional/Action pattern (based on `data_command_service.py`).
-   **`service_query.py.jinja2`**: Retrieval pattern (based on `data_query_service.py`).

#### C. Extensibility
-   **`generic.py.jinja2`**: A blank slate wrapper that injects a module header and renders arbitrary body content/structure provided via context.

### 3.2. Phase 2: Tooling Refactor

#### `mcp_server/managers/scaffold_manager.py`
-   **Generic Renderer**: Implement `render_generic(template_name, context)` which loads *any* given template file and passes the full context dict.
-   **Specific Renderers**: Add methods for the new specific types (`render_tool`, `render_service`, etc.) to enforce specific validations (e.g., checking if a command service has a persistor).

#### `mcp_server/tools/scaffold_tools.py`
-   **Update CLI**:
    -   Expand `component_type` enum: `['dto', 'worker', 'adapter', 'tool', 'resource', 'schema', 'interface', 'service', 'generic']`.
    -   Add `service_type` argument (enum: `['orchestrator', 'command', 'query']`).
    -   Add `template_name` argument (for generic mode).
    -   Add `context` argument (JSON string or dict for generic mode input).

### 3.3. Phase 3: Documentation

#### [MODIFY] [docs/reference/templates/COMPONENTS_README.md](file:///d:/dev/SimpleTraderV3/docs/reference/templates/COMPONENTS_README.md)
- Update index to include DTO, Worker, Adapter templates.

#### [NEW] [docs/reference/templates/python_dto.md](file:///d:/dev/SimpleTraderV3/docs/reference/templates/python_dto.md)
#### [NEW] [docs/reference/templates/python_worker.md](file:///d:/dev/SimpleTraderV3/docs/reference/templates/python_worker.md)
#### [NEW] [docs/reference/templates/python_adapter.md](file:///d:/dev/SimpleTraderV3/docs/reference/templates/python_adapter.md)

## Verification Plan

### Automated Tests
1.  **Render Verification**: Re-run a script to verify that `scaffold_component` output matches the new reference templates (visual check or diff).
2.  **Linting**: Ensure new markdown files pass lint checks (if any).

### Manual Verification
1.  **Review**: User review of the new reference docs to ensure they match expectations.
 to prevent "Source of Truth" drift.

### 4.1. Automated Verification
We will run the `scaffold_component` tool for each new type to verify:
1.  **Tool**: Generates correct `InputSchema`.
2.  **Resource**: Generates correct URI regex.
3.  **Command Service**: Generates logic structure resembling `DataCommandService`.
4.  **Generic**: Generates a valid file using a custom template path (verifying extensibility).

### 4.2. Quality Gates
-   Generated code must pass `pylint` and `pyright` (via existing CI checks or manual verify).
-   File headers must correctly reflect `@layer` (e.g., `Service`, `Interface`).
