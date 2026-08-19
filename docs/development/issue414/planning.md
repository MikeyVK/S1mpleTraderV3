<!-- docs\development\issue414\planning.md -->
<!-- template=planning version=130ac5ea created=2026-08-19T18:56Z updated=2026-08-19T19:05Z -->
# Planning: Delegate Validation Resource Schema Generation to IPresenter

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-19

---

## Purpose

Plan the sequential TDD implementation cycles, deliverables, and exit criteria for Issue #414.

## Scope

**In Scope:**
- TDD implementation of DTO schemas (`PresentationResource`, `PresentedOutput`).
- Segregated protocols (`ITextPresenter`, `IResourcePresenter`, `IPresenter`).
- Presenter implementations (`ValidationResourcePresenter`, `TextPresenter` adaptation, `ResponsePresenter`).
- Decoupling of `MCPServer` transport layer and `ApplicationBootstrap` composition root.
- Comprehensive unit and integration test coverage with 100% type safety.

**Out of Scope:**
- Modifications to other MCP tools, validation decorators, or client-side JSON-RPC protocol handling.

---

## Summary

Decomposition of the composite presentation architecture into 4 sequential TDD cycles, ensuring strict SRP, ISP, and DIP compliance while preserving external wire protocol compatibility.

---

## TDD Cycles

### Cycle 1: Presentation Schemas & Interfaces

**Goal:** Define immutable `PresentationResource` and `PresentedOutput` DTO schemas and update `IPresenter`, `ITextPresenter`, and `IResourcePresenter` interface protocols.

**Deliverables:**
- `D1.1`: Create immutable `PresentationResource` and `PresentedOutput` models in [`mcp_server/schemas/presentation_output.py`](file:///c:/temp/pgmcp/mcp_server/schemas/presentation_output.py).
- `D1.2`: Define `ITextPresenter`, `IResourcePresenter`, and `IPresenter` protocols in [`mcp_server/core/interfaces/ipresenter.py`](file:///c:/temp/pgmcp/mcp_server/core/interfaces/ipresenter.py).
- `D1.3`: Create unit tests in [`tests/mcp_server/unit/schemas/test_presentation_output.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/schemas/test_presentation_output.py) and [`tests/mcp_server/unit/core/interfaces/test_presenter_interfaces.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/core/interfaces/test_presenter_interfaces.py).

**Tests:**
- `tests/mcp_server/unit/schemas/test_presentation_output.py`
- `tests/mcp_server/unit/core/interfaces/test_presenter_interfaces.py`

**Exit Criteria:**
- `PresentationResource` and `PresentedOutput` models are frozen and verified.
- `ITextPresenter`, `IResourcePresenter`, and `IPresenter` protocols are defined with `@runtime_checkable`.
- Unit tests pass with 0 typing errors under Pyright and mypy.

---

### Cycle 2: Presenter Subcomponents & Composition

**Goal:** Implement `ValidationResourcePresenter`, adapt `TextPresenter` to `ITextPresenter`, and implement `ResponsePresenter` composite.

**Deliverables:**
- `D2.1`: Implement `ValidationResourcePresenter` extracting `schema://validation` in [`mcp_server/presenters/validation_resource_presenter.py`](file:///c:/temp/pgmcp/mcp_server/presenters/validation_resource_presenter.py).
- `D2.2`: Refactor `TextPresenter` to implement `ITextPresenter` in [`mcp_server/presenters/text_presenter.py`](file:///c:/temp/pgmcp/mcp_server/presenters/text_presenter.py).
- `D2.3`: Implement `ResponsePresenter` coordinating text and resource delegates in [`mcp_server/presenters/response_presenter.py`](file:///c:/temp/pgmcp/mcp_server/presenters/response_presenter.py).
- `D2.4`: Update presenter package exports in [`mcp_server/presenters/__init__.py`](file:///c:/temp/pgmcp/mcp_server/presenters/__init__.py) and add unit tests in [`tests/mcp_server/unit/test_presenter.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_presenter.py).

**Tests:**
- `tests/mcp_server/unit/test_presenter.py`

**Exit Criteria:**
- `ValidationResourcePresenter` extracts `schema://validation` from `ValidationErrorOutput`.
- `TextPresenter` implements `ITextPresenter`.
- `ResponsePresenter` delegates to both and returns `PresentedOutput`.
- All presenter unit tests pass.

**Dependencies:** Cycle 1

---

### Cycle 3: Transport Layer Decoupling & Bootstrap Wiring

**Goal:** Decouple `MCPServer` to `IPresenter`, map `PresentedOutput` to `ToolResult`, and wire `ResponsePresenter` in `bootstrap.py`.

**Deliverables:**
- `D3.1`: Decouple `MCPServer` to accept `IPresenter | None` via constructor injection and generically map `PresentedOutput` in [`mcp_server/server.py`](file:///c:/temp/pgmcp/mcp_server/server.py).
- `D3.2`: Wire composite `ResponsePresenter` in [`mcp_server/bootstrap.py`](file:///c:/temp/pgmcp/mcp_server/bootstrap.py).
- `D3.3`: Update server and bootstrap unit tests in [`tests/mcp_server/unit/server/test_validate_tool_arguments.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/server/test_validate_tool_arguments.py), [`tests/mcp_server/unit/test_server.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_server.py), and [`tests/mcp_server/unit/server/test_bootstrap.py`](file:///c:/temp/pgmcp/tests/mcp_server/unit/server/test_bootstrap.py).

**Tests:**
- `tests/mcp_server/unit/server/test_validate_tool_arguments.py`
- `tests/mcp_server/unit/test_server.py`
- `tests/mcp_server/unit/server/test_bootstrap.py`

**Exit Criteria:**
- `MCPServer` contains zero `schema://validation` or `ValidationError` inspection.
- `bootstrap.py` wires `ResponsePresenter`.
- Server and bootstrap unit tests pass.

**Dependencies:** Cycle 2

---

### Cycle 4: End-to-End Verification & Quality Gates

**Goal:** Run full end-to-end integration tests and execute complete quality gates.

**Deliverables:**
- `D4.1`: Verify end-to-end MCP wire compatibility in [`tests/mcp_server/integration/test_strict_input_validation_response.py`](file:///c:/temp/pgmcp/tests/mcp_server/integration/test_strict_input_validation_response.py) and [`tests/mcp_server/integration/test_pipeline_e2e.py`](file:///c:/temp/pgmcp/tests/mcp_server/integration/test_pipeline_e2e.py).
- `D4.2`: Run branch quality gates ensuring 10.00/10 linting and 100% type safety.

**Tests:**
- `tests/mcp_server/integration/test_strict_input_validation_response.py`
- `tests/mcp_server/integration/test_pipeline_e2e.py`

**Exit Criteria:**
- End-to-end integration tests pass verifying wire contract compatibility.
- Branch quality gates pass with 10.00/10 linting and 0 typing errors.

**Dependencies:** Cycle 3

---

## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/coding_standards/DOCUMENTATION_STANDARD.md][related-2]**
- **[docs/development/issue414/research.md][related-3]**
- **[docs/development/issue414/design.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/coding_standards/DOCUMENTATION_STANDARD.md
[related-3]: docs/development/issue414/research.md
[related-4]: docs/development/issue414/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-19 | Agent | Initial planning document specifying 4 TDD cycles and deliverable mapping |
