<!-- docs\development\issue414\research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-19T17:40Z updated=2026-08-19T18:25Z -->
# Research: Delegate Validation Resource Schema Generation to IPresenter

**Status:** APPROVED  
**Version:** 1.3  
**Last Updated:** 2026-08-19

---

## Purpose

Investigate the problem space, architectural boundaries, and migration constraints regarding the delegation of `schema://validation` resource generation from the transport layer (`MCPServer`) to the presentation layer.

## Scope

**In Scope:**
- Analysis of current coupling in [`mcp_server/server.py`](file:///c:/temp/pgmcp/mcp_server/server.py) where transport logic constructs `schema://validation` resources.
- Analysis of current presentation boundaries in [`mcp_server/core/interfaces/ipresenter.py`](file:///c:/temp/pgmcp/mcp_server/core/interfaces/ipresenter.py) and [`mcp_server/presenters/text_presenter.py`](file:///c:/temp/pgmcp/mcp_server/presenters/text_presenter.py).
- Analysis of [ARCHITECTURE_PRINCIPLES.md](file:///c:/temp/pgmcp/docs/coding_standards/ARCHITECTURE_PRINCIPLES.md) constraints regarding SRP, ISP, DIP, and composition.
- Exploration of structural options and trade-offs for decoupling transport from presentation.
- Mapping of the blast radius across production files, test suites, and fixtures.
- Definition of the Approved Strategy and Expected Results.

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
3. Identify trade-offs between monolithic presentation and composite presentation models.
4. Establish preservation invariants and candidate seams for subsequent design and planning phases.

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

### 3. Structural Options Explored

| Option | Description | Architectural Assessment |
|---|---|---|
| **Option 1: Monolithic Presenter Extension** | Extend `TextPresenter` to directly generate both text and resource payloads. | Violates SRP; conflates text templating with resource serialization. |
| **Option 2: Transport-Level Protocol Converter** | Move resource generation to transport converters (`mcp_converters.py`). | Leaves presentation formatting logic within the transport adapter layer. |
| **Option 3: Composite Presentation Architecture** | Separate text formatting from resource payload generation, unified by a coordinating presentation facade returning a presentation envelope. | Satisfies SRP, ISP, and DIP; keeps transport layer completely agnostic. |

---

## Invariants & Preservation Goals

1. **Protocol Compatibility:**
   Tool calls failing validation must continue to return `CallToolResult(isError=True)` containing both `TextContent` and the `EmbeddedResource` for `schema://validation`.
2. **Strict Type Safety:**
   All components must adhere to strict typing without global ignores.
3. **Transport Purity:**
   `MCPServer` must depend strictly on `IPresenter` (DIP) and perform zero inspection of domain error types or validation schema extraction.

---

## Blast Radius Analysis

### Production Subsystems
- **Core Interfaces:** [`mcp_server/core/interfaces/ipresenter.py`](file:///c:/temp/pgmcp/mcp_server/core/interfaces/ipresenter.py)
- **Presentation Layer:** [`mcp_server/presenters/`](file:///c:/temp/pgmcp/mcp_server/presenters/)
- **Transport / Server Layer:** [`mcp_server/server.py`](file:///c:/temp/pgmcp/mcp_server/server.py)
- **Composition Root:** [`mcp_server/bootstrap.py`](file:///c:/temp/pgmcp/mcp_server/bootstrap.py)

### Test Suites
- Presenter unit tests: [`tests/mcp_server/unit/test_presenter.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_presenter.py)
- Server argument validation unit tests: [`tests/mcp_server/unit/server/test_validate_tool_arguments.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/server/test_validate_tool_arguments.py)
- Server integration tests: [`tests/mcp_server/integration/test_strict_input_validation_response.py`](file:///c:/temp/pgmcp/tests/mcp_server/integration/test_strict_input_validation_response.py)

---

## Candidate Seams for Later Phases

1. **Seam 1: Presentation Contracts & Components** (Presentation layer decoupling)
2. **Seam 2: Transport Layer Integration** (`MCPServer` DIP and generic presentation consumption)
3. **Seam 3: End-to-End Verification & Quality Gates** (Regression testing)

---

## Approved Strategy

**Selected Strategy:** Preserve Compatibility

**Boundary & Preservation Scope:**
- Preserves 100% backward compatibility for all external MCP clients and JSON-RPC consumers.
- Preserves the exact structure, MIME type (`application/json`), and URI (`schema://validation`) of the validation error resource block.
- Internal refactoring will cleanly separate presentation from transport in accordance with [ARCHITECTURE_PRINCIPLES.md](file:///c:/temp/pgmcp/docs/coding_standards/ARCHITECTURE_PRINCIPLES.md).

**Constraints for Later Phases:**
- The Design phase will define the concrete interfaces, presentation envelope schemas, and component breakdown.
- The Planning and Implementation phases will execute the refactoring via strict TDD cycles.

---

## Expected Results

1. `mcp_server/server.py` is completely free of `schema://validation` construction and error DTO inspection.
2. `MCPServer` depends solely on the `IPresenter` abstraction.
3. The presentation layer coordinates both text rendering and resource generation without violating SRP.
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
