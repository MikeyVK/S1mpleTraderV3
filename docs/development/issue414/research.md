<!-- docs\development\issue414\research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-19T17:40Z updated=2026-08-19T18:30Z -->
# Research: Delegate Validation Resource Schema Generation to IPresenter

**Status:** APPROVED  
**Version:** 1.4  
**Last Updated:** 2026-08-19

---

## Purpose

Investigate the problem space, architectural boundaries, blast radius, and migration strategy for delegating `schema://validation` resource generation from the transport layer (`MCPServer`) to the presentation layer.

## Scope

**In Scope:**
- Analysis of coupling in [`mcp_server/server.py`](file:///c:/temp/pgmcp/mcp_server/server.py) where transport logic constructs `schema://validation` resources.
- Analysis of current presentation boundaries in [`mcp_server/core/interfaces/ipresenter.py`](file:///c:/temp/pgmcp/mcp_server/core/interfaces/ipresenter.py) and [`mcp_server/presenters/text_presenter.py`](file:///c:/temp/pgmcp/mcp_server/presenters/text_presenter.py).
- Analysis of [ARCHITECTURE_PRINCIPLES.md](file:///c:/temp/pgmcp/docs/coding_standards/ARCHITECTURE_PRINCIPLES.md) constraints regarding SRP (Rule 1.1), ISP (Rule 1.4), DIP (Rule 1.5), and composition.
- Exhaustive blast radius audit across production subsystems, test suites, configuration, and documentation.
- Definition of the Approved Strategy (per boundary) and Expected Results.

**Out of Scope:**
- Specifying concrete class designs, method bodies, or interface implementations (reserved for Design phase).
- Modifying individual MCP tool logic or validation decorators.
- Altering the MCP wire protocol format or JSON-RPC schema contracts.

---

## Problem Statement

In the current implementation of [`mcp_server/server.py`](file:///c:/temp/pgmcp/mcp_server/server.py#L160-L176), the transport layer (`MCPServer`) directly inspects the execution result DTO for `error_type == "ValidationError"`, extracts `result_dto.input_schema`, and appends an embedded resource dictionary (`{"type": "resource", "resource": {"uri": "schema://validation", ...}}`) to `ToolResult.content`.

This produces architectural tensions:
1. **Presentation Boundary Violation:** The transport layer is responsible for assembling presentation resources instead of consuming a presented view from the presentation layer.
2. **SRP & Responsibility Overlap:** `MCPServer` mixes transport orchestration (request routing, caching, response serialization) with domain-specific presentation logic.
3. **DIP Violation:** `MCPServer.__init__` is coupled to the concrete class `TextPresenter` rather than the abstraction `IPresenter`.

---

## Research Goals

1. Investigate the current flow of validation errors from tool execution through caching and presentation to protocol serialization.
2. Analyze the architectural constraints (SRP, ISP, DIP) governing the separation between Markdown text rendering and embedded resource generation.
3. Verify the complete blast radius across all production files, tests, configs, and active documentation.
4. Establish the Approved Strategy per boundary and expected results for subsequent design and planning phases.

---

## Findings & Evidence

### 1. The Presentation Nature of `schema://validation`

Investigation of the MCP client behavior (e.g. in VS Code and agent environments) shows:
- An `EmbeddedResource` with `uri="schema://validation"` is an interactive UI/presentation element displayed directly to the client/user to inspect the valid parameter schema.
- Generating this view is fundamentally a presentation responsibility, not a transport responsibility.

### 2. Architectural Tensions Identified

- **Nomenclature and Single Responsibility:**
  `TextPresenter` is historically named and focused on generating Markdown strings from templates. Making a text presenter directly responsible for extracting and formatting JSON resource payloads violates SRP (Rule 1.1 in `ARCHITECTURE_PRINCIPLES.md`).
- **Text References vs. Resource Payloads:**
  - Visible text in chat (e.g., Markdown notes, tips, and URI footnote references) is purely textual presentation.
  - Embedded resource payloads (JSON schemas with MIME types and URI identifiers) represent structured presentation data.
- **Transport Independence:**
  The transport layer (`server.py`) should remain completely agnostic of specific error types (`ValidationError`), schema extraction, or presentation resource construction.

---

## Comprehensive Blast Radius Audit

An exhaustive audit of the codebase identified the following affected surfaces:

### 1. Production Subsystems
- [`mcp_server/core/interfaces/ipresenter.py`](file:///c:/temp/pgmcp/mcp_server/core/interfaces/ipresenter.py): Core interface for the presentation layer.
- [`mcp_server/core/interfaces/__init__.py`](file:///c:/temp/pgmcp/mcp_server/core/interfaces/__init__.py): Re-export facade for core interfaces.
- [`mcp_server/presenters/text_presenter.py`](file:///c:/temp/pgmcp/mcp_server/presenters/text_presenter.py): Text presentation implementation and `validate_presentation_alignment`.
- [`mcp_server/presenters/__init__.py`](file:///c:/temp/pgmcp/mcp_server/presenters/__init__.py): Presenter package exports.
- [`mcp_server/server.py`](file:///c:/temp/pgmcp/mcp_server/server.py): `MCPServer.__init__` type annotation and `MCPServer.handle_call_tool` presentation orchestration.
- [`mcp_server/bootstrap.py`](file:///c:/temp/pgmcp/mcp_server/bootstrap.py): Composition root instantiating and injecting the presenter into `MCPServer`.
- [`mcp_server/core/operation_notes.py`](file:///c:/temp/pgmcp/mcp_server/core/operation_notes.py): Interacts with `presenter.present_notes(tool_name, entries)` (verified for contract compatibility).

### 2. Test Suites
- [`tests/mcp_server/unit/test_presenter.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_presenter.py): Direct unit tests for presenter methods, templates, notes, and alignment checks.
- [`tests/mcp_server/unit/server/test_validate_tool_arguments.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/server/test_validate_tool_arguments.py): Unit tests verifying that `schema://validation` `EmbeddedResource` is present on validation failure.
- [`tests/mcp_server/integration/test_strict_input_validation_response.py`](file:///c:/temp/pgmcp/tests/mcp_server/integration/test_strict_input_validation_response.py): Integration tests verifying end-to-end MCP `CallToolResult` schema resources.
- [`tests/mcp_server/integration/test_pipeline_e2e.py`](file:///c:/temp/pgmcp/tests/mcp_server/integration/test_pipeline_e2e.py): Integration pipeline tests configuring `server.presenter`.
- [`tests/mcp_server/unit/server/test_bootstrap.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/server/test_bootstrap.py): Verifies presenter instantiation and injection in `bootstrap.py`.
- [`tests/mcp_server/unit/core/test_note_context_unit.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/core/test_note_context_unit.py): Verifies `NoteContext` delegation to `presenter.present_notes`.
- [`tests/mcp_server/unit/managers/test_enforcement_runner_unit.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/managers/test_enforcement_runner_unit.py): Mocks `note_context.presenter`.
- [`tests/mcp_server/unit/test_server.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_server.py): Server orchestration unit tests with mocked presenter.

### 3. Configuration & Schemas
- `.pgmcp/config/presentation.yaml`: SSOT for presentation templates, emojis, and failure messages (no schema changes required).
- `mcp_server/config/schemas/presentation_config.py`: Pydantic config models for presentation settings.

### 4. Active Documentation
- [`docs/manuals/architecture.md`](file:///c:/temp/pgmcp/docs/manuals/architecture.md): Reference to `ipresenter.py` and presenter subsystem structure.

---

## Approved Strategy (per Boundary)

### Boundary 1: Internal Python Interfaces (`IPresenter`, `MCPServer`, Presenters)
- **Selected Strategy:** **Clean Break**
- **Rationale:** This is internal repository code without external package consumers. A clean break allows immediate replacement of outdated signatures without maintaining legacy shims, transitional wrappers, or technical debt.
- **Rules:** Replace internal signatures and interfaces in one cohesive refactor.

### Boundary 2: External MCP Protocol (`CallToolResult` Wire Contract)
- **Selected Strategy:** **Preserve Wire Contract**
- **Rationale:** External MCP clients (VS Code, Copilot, agent runtimes) expect `CallToolResult(isError=True)` containing both `TextContent` (error message) and `EmbeddedResource` (`schema://validation`).
- **Rules:** The wire-level JSON-RPC representation must remain 100% identical and fully compatible.

---

## Expected Results

1. `mcp_server/server.py` is completely free of `schema://validation` construction, hardcoded resource dicts, and error DTO inspection.
2. `MCPServer` depends strictly on the `IPresenter` abstraction.
3. The presentation layer coordinates both text rendering and resource generation without violating SRP or ISP.
4. All unit and integration test suites pass with 100% type safety and zero linter warnings.

---

## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/coding_standards/DOCUMENTATION_STANDARD.md][related-2]**
- **[docs/development/archive/issue406/design_gaps.md][related-3]**
- **[docs/development/archive/issue411/research.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/coding_standards/DOCUMENTATION_STANDARD.md
[related-3]: docs/development/archive/issue406/design_gaps.md
[related-4]: docs/development/archive/issue411/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-19 | Agent | Initial research document analyzing presentation delegation and interface design |
| 1.1 | 2026-08-19 | Agent | Refined presentation architecture with PresentedOutput DTO |
| 1.2 | 2026-08-19 | Agent | Applied ARCHITECTURE_PRINCIPLES.md composite design |
| 1.3 | 2026-08-19 | Agent | Enforced documentation standard boundaries by removing premature design specifications |
| 1.4 | 2026-08-19 | Agent | Explicitly defined Approved Strategy per boundary (Clean Break internally / Preserve Wire Contract externally) and completed exhaustive blast radius audit |
