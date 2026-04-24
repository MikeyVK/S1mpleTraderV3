# QA — Session Handover (Issue #120 / Phase 1)

Date: 2026-01-22  
Branch: `feature/120-scaffolder-error-messages`  
Scope: Read-only review of Phase 1 completeness, with focus on **skipped tests**, **unit/e2e coverage**, and **Phase 1 readiness**.

## Executive Summary
Phase 1 is functionally green (tests pass), but **not QA-complete** under a “no skipped tests / strict pytest hygiene” quality bar.

Key blockers:
- There are **14 skipped tests** in the default `pytest` run.
- A significant subset (11) are core `TemplateScaffolder` unit tests that were skipped due to a test-double incompatibility introduced by template introspection.
- There is also a pytest configuration inconsistency (`pytest.ini` vs `pyproject.toml`) causing **marker strictness not to be enforced** and producing an **UnknownMarkWarning**.

## What Changed (High-level)
Recent work on this branch adds:
- Template schema extraction and validation via Jinja2 AST introspection.
- Integration of introspection into `TemplateScaffolder.validate()`.
- Structured `ValidationError.to_resource_dict()` support for ToolResult resource payloads.

## Evidence: Test Suite Results
All commands were executed locally in the repo root.

### Full suite
Command:
- `python -m pytest -ra`

Result:
- **1281 passed, 14 skipped**

### Unit tests
Command:
- `python -m pytest -ra tests/unit`

Result:
- **1125 passed, 12 skipped**

### Integration / E2E tests
Command:
- `python -m pytest -ra tests/integration`

Result:
- **59 passed, 0 skipped**

## Evidence: Coverage
Note: `pytest-cov` is installed and was used to generate these numbers.

### Unit coverage (backend + mcp_server)
Command:
- `python -m pytest tests/unit -q --cov=mcp_server --cov=backend --cov-report=term`

Result:
- **TOTAL: 80%** (combined)

Notable phase-1 related files (from unit coverage output):
- `mcp_server/scaffolding/template_introspector.py`: **100%**
- `mcp_server/scaffolders/template_scaffolder.py`: **~88%**
- `mcp_server/core/exceptions.py`: **~98%**

### Integration/E2E coverage (mcp_server only)
Command:
- `python -m pytest tests/integration -q --cov=mcp_server --cov-report=term`

Result:
- **TOTAL: 54%**

Interpretation:
- E2E tests exercise the tool/manager flow and many scaffold paths, but large parts of `mcp_server` remain unexecuted in integration runs.

## Evidence: Skipped Tests Inventory
### 11 skips — core `TemplateScaffolder` unit tests
File:
- `tests/unit/scaffolders/test_template_scaffolder.py`

Reason pattern:
- “Mock renderer incompatible with template introspection (Issue #120)”

Skipped tests (high value):
- `TestConstructor.test_accepts_custom_renderer`
- `TestScaffold.test_scaffold_dto_renders_template`
- `TestScaffold.test_scaffold_worker_includes_name_suffix`
- `TestScaffold.test_scaffold_design_doc_uses_markdown_extension`
- `TestScaffold.test_scaffold_service_orchestrator_selects_correct_template`
- `TestScaffold.test_scaffold_service_command_selects_correct_template`
- `TestScaffold.test_scaffold_service_defaults_to_orchestrator`
- `TestScaffold.test_scaffold_generic_uses_template_name_from_context`
- `TestScaffold.test_scaffold_generic_without_template_name_fails` (skipped with a different reason)
- `TestScaffold.test_scaffold_passes_all_context_to_renderer`
- `TestScaffold.test_scaffold_template_not_found_raises_execution_error`

QA assessment:
- These are core contract tests for `scaffold()` behavior (template routing, naming, context pass-through, error typing). Skipping them in the default run is not acceptable for “Phase 1 done”.

### 1 skip — fallback templates not implemented
File:
- `tests/unit/scaffolders/test_template_registry.py`

Skipped test:
- `TestTemplateRegistryLoading.test_uses_fallback_when_primary_none`

Reason:
- `pytest.skip("Fallback template logic not yet implemented")`

QA assessment:
- This is a real feature gap. Either implement fallback behavior or formally exclude it from Phase 1 with updated acceptance criteria. Skipping in default test run indicates unfinished slice.

### 1 skip — legacy manual field validation removed
File:
- `tests/mcp_server/config/test_component_registry.py`

Skipped test:
- `TestArtifactRegistryConfig.test_validate_artifact_fields_missing`

Reason:
- “Manual field validation removed - template introspection is now Single Source of Truth (Issue #120)”

QA assessment:
- This test is now legacy. It should be removed or replaced with a test that validates the new introspection-based validation path. Keeping it as skipped “forever” is not a good end state.

### 1 skip + marker warning — manual integration proxy test
File:
- `tests/mcp_server/core/test_proxy.py`

Details:
- Uses `@pytest.mark.integration` and then does `pytest.skip("Manual integration test - run with real server")`.

QA assessment:
- It’s reasonable to keep manual integration tests out of the default suite, but the marker should be registered, and the default run should not produce `PytestUnknownMarkWarning`.

## Phase 1 “Done?” — QA Verdict
**Not done** if your Definition of Done includes:
- no skipped tests in default run, and/or
- strict marker hygiene (no warnings) and single-source pytest config, and/or
- explicit coverage of `TemplateScaffolder.scaffold()` routing, filename behavior, and error typing.

**Functionally done** if your DoD is limited to:
- green unit + integration suite, and
- core introspection validate path covered.

Given your stated requirement (“tests are being skipped; that cannot be intended”), the appropriate verdict is **NOT DONE**.

## Coverage Gaps (Most Important)
The new tests cover `validate()` via introspection well, but there are gaps for `scaffold()` behavior:
- Worker file naming suffix (`name_suffix`) is not covered outside skipped tests.
- Service template selection by `service_type` is not covered outside skipped tests.
- Generic template selection via `template_name` is not covered outside skipped tests.
- Context pass-through contract is not covered outside skipped tests.
- Template-missing / error-type propagation tests appear inconsistent across test layers (contract intent vs asserted error code/type).

## Recommendations / Next Steps (QA-focused)
1) **Replace skipped scaffolder unit tests with real renderer-based tests**:
   - Use `tmp_path` + a real `JinjaRenderer(template_dir=tmp_path)` and write minimal templates on disk so `env.loader.get_source()` works.
   - This eliminates the need for a mocked renderer and removes 11 skips.

2) **Fix pytest configuration single-source**:
   - Choose either `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`.
   - Ensure integration marker is registered (and enable strict marker checking).

3) **Resolve fallback template behavior**:
   - Either implement fallback in `TemplateScaffolder`, or explicitly remove/park it from Phase 1 and adapt tests accordingly.

4) **Clean up legacy manual-validation test**:
   - Replace the skipped test with a new test that asserts the intended SSOT (template-derived schema) behavior, or remove it if redundant.

## Appendix: Relevant files
- `mcp_server/scaffolders/template_scaffolder.py`
- `mcp_server/scaffolding/template_introspector.py`
- `mcp_server/core/exceptions.py`
- `tests/unit/scaffolders/test_template_scaffolder.py` (skips)
- `tests/unit/scaffolders/test_template_scaffolder_introspection.py` (new validate coverage)
- `tests/integration/mcp_server/test_scaffold_tool_execute_e2e.py`
- `tests/acceptance/test_issue56_acceptance.py`

---
End of QA handover.
