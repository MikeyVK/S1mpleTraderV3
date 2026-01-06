# Issue 91 – Research: failing tests + test structure inventory

Date: 2026-01-06
Branch: `epic/91-test-suite-cleanup`

## Scope / intent
This document is **inventory + research only**.

- Goal 1: capture the **current failing tests** (no fixes yet)
- Goal 2: inventory where unit tests live today vs the intended **mirror layout** of `mcp_server/`
- Goal 3: identify **duplicate test coverage** for the same modules (often caused by non-mirrored placement)

## Project initialization (branch)
Project state was initialized for Issue #91 using the ST3 initialization tool:

- Issue: `91` – "Epic: Restore clean tests + consistent ToolResult error contract"
- Workflow: `refactor`
- Branch: `epic/91-test-suite-cleanup`
- Initial phase: `research`
- Files created/updated: `.st3/projects.json`, `.st3/state.json`

## Test run: current failures
Command executed:
- `python -m pytest -q -ra`

Result summary:
- `10 failed, 1017 passed, 25 warnings` (runtime ~64s)

### Failing tests (as reported)
1) `tests/integration/mcp_server/validation/test_safe_edit_validation_integration.py::TestSafeEditValidationIntegration::test_safe_edit_allows_with_guideline_warnings`
- Observed failure: strict mode rejects a GUIDELINE-level naming issue (`invalid-name`), but the test expects “guidelines warn but allow save”.

2) `tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py::TestScaffoldValidateCycle::test_scaffold_dto_passes_validation`
- Observed failure: scaffolded DTO fails validation due to lint + type issues (trailing newlines, fixme, import-outside-toplevel, unused imports, and `None` default vs `str` type).

3) `tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py::TestScaffoldValidateCycle::test_scaffold_tool_passes_validation`
- Observed failure: scaffolded Tool fails validation due to a syntax error (“unterminated triple-quoted string literal”), causing a cascade of pyright issues.

4) `tests/integration/test_issue39_cross_machine.py::TestIssue39CrossMachine::test_complete_cross_machine_flow`
- Observed failure: test expects `state.json` to contain a mapping keyed by branch name (e.g. `state['fix/42-cross-machine-test']`).
- Actual observed shape: `state.json` appears to be a single-object state with a `branch` field (e.g. `{'branch': 'fix/42-cross-machine-test', ...}`), so membership assertion fails.

5) `tests/mcp_server/managers/test_phase_state_engine_async.py::TestGitCheckoutEncapsulation::test_git_checkout_does_not_call_protected_save_state`
- Observed failure: `ast.parse()` fails with `SyntaxError: invalid non-printable character U+FEFF`.
- Confirmed root cause: `mcp_server/tools/git_tools.py` starts with a UTF-8 BOM (`EF-BB-BF`).

6) `tests/unit/mcp_server/tools/test_git_checkout_state_sync.py::TestGitCheckoutStateSync::test_checkout_syncs_state_and_returns_phase`
7) `tests/unit/mcp_server/tools/test_git_checkout_state_sync.py::TestGitCheckoutStateSync::test_checkout_handles_state_sync_failure_gracefully`
8) `tests/unit/mcp_server/tools/test_git_checkout_state_sync.py::TestGitCheckoutStateSync::test_checkout_handles_unknown_phase`
- Observed failure: tests patch `mcp_server.tools.git_tools.PhaseStateEngine`, but the module does not expose `PhaseStateEngine` as an attribute (likely due to import strategy changes).

9) `tests/unit/mcp_server/tools/test_initialize_project_tool.py::TestInitializeProjectToolMode1::test_branch_name_auto_detected`
- Observed failure: expects `GitManager.get_current_branch()` called once, but it was called twice.
- Also observed: warning log that `git reflog show --all` failed with exit status 128 during the test.

10) `tests/unit/tools/test_git_tools.py::test_get_parent_branch_current_branch`
- Observed failure: expected `PhaseStateEngine.get_state()` to be called with a specific mocked branch; actual call uses `epic/91-test-suite-cleanup`.
- Likely indicates the test’s patch/branch resolution expectation drifted from implementation.

### Quick clustering (hypotheses, not fixes)
- **Validation severity contract drift**: “guideline vs error” behavior doesn’t match tests.
- **Scaffolding templates drift**: template output does not satisfy validator/linter/type-checker expectations.
- **State schema drift**: tests expect one `state.json` schema, code writes another.
- **Import/patching drift**: tests patch module attributes that no longer exist due to refactors.
- **Encoding drift**: BOM in a source file breaks AST parsing.

## Test structure inventory (mirror vs current)
### Intended rule
Unit tests under `tests/unit/mcp_server/` should form a **mirror** of the production code tree under `mcp_server/`.

Example expectation:
- `mcp_server/tools/git_tools.py` → `tests/unit/mcp_server/tools/test_git_tools.py` (and related tool tests in the same mirrored folder)

### Current distribution (Python test files)
Total python test files found under `tests/`: **105**

Bucket counts (by path prefix):
- `tests/unit/mcp_server/`: **44**
- `tests/unit/` (non-mirrored unit tests): **52**
- `tests/mcp_server/`: **1**
- `tests/integration/`: **6**
- other: **2**

Top-level structure under `tests/` today:
- `tests/unit/...` contains both mirrored (`tests/unit/mcp_server/...`) and non-mirrored unit tests (`tests/unit/tools`, `tests/unit/scaffolding`, etc.)
- There is also a separate `tests/mcp_server/...` folder (currently containing at least one manager test)

### Duplicate coverage: same module tested from multiple locations
Heuristic used: first `import` / `from ... import ...` that references `mcp_server.*` inside each test file.

Modules with test coverage spread across multiple folders (examples):

- `mcp_server.tools.git_tools`
  - `tests/unit/mcp_server/tools/test_git_checkout_state_sync.py`
  - `tests/unit/tools/test_git_tools.py`

- `mcp_server.tools.safe_edit_tool`
  - `tests/integration/mcp_server/validation/test_safe_edit_validation_integration.py`
  - `tests/unit/tools/test_safe_edit_tool.py`

- `mcp_server.tools.base`
  - `tests/unit/mcp_server/tools/test_base_tool_error_handling.py`
  - `tests/unit/tools/test_tools_base.py`

- `mcp_server.managers.phase_state_engine`
  - `tests/unit/mcp_server/managers/test_phase_state_engine.py`
  - `tests/unit/mcp_server/managers/test_phase_state_engine_persistence.py`
  - `tests/unit/mcp_server/managers/test_phase_state_engine_workflow.py`
  - `tests/unit/mcp_server/tools/test_force_phase_transition_tool.py`
  - `tests/unit/mcp_server/tools/test_transition_phase_tool.py`
  - `tests/integration/test_issue39_cross_machine.py`
  - `tests/mcp_server/managers/test_phase_state_engine_async.py`

- `mcp_server.config.label_config`
  - `tests/unit/mcp_server/config/test_label_config.py`
  - `tests/unit/mcp_server/config/test_label_startup.py`
  - `tests/unit/mcp_server/config/test_labelconfig_singleton_bug.py`
  - `tests/unit/mcp_server/tools/test_label_tools_integration.py`
  - `tests/unit/tools/test_github_extras.py`
  - `tests/unit/tools/test_label_tools.py`

Interpretation (why this matters):
- When “unit tests” exist both inside and outside the mirrored tree, it becomes harder to enforce a consistent convention, and easy for agents to accidentally create a *second* test file for the same module instead of extending the existing mirrored test.

### UTF-8 BOM / encoding inventory
Files under `tests/` detected with UTF-8 BOM:
- `tests/conftest.py`
- `tests/unit/dtos/strategy/test_risk.py`
- `tests/unit/dtos/strategy/test_signal.py`
- `tests/unit/mcp_server/config/test_workflow_config.py`
- `tests/unit/mcp_server/core/test_policy_engine.py`
- `tests/unit/mcp_server/managers/test_phase_state_engine_workflow.py`
- `tests/unit/mcp_server/managers/test_project_manager.py`
- `tests/unit/mcp_server/tools/test_label_tools_integration.py`

Separate but directly relevant to failures:
- `mcp_server/tools/git_tools.py` has a UTF-8 BOM (confirmed by byte prefix `EF-BB-BF`), which currently breaks `ast.parse()`-based tests.

## Notes / next research steps
(Still “research only”, but outlines what to investigate next.)

- Decide the canonical home for unit tests:
  - Prefer `tests/unit/mcp_server/...` as the mirror of `mcp_server/...`
  - Decide what `tests/unit/tools` and `tests/unit/scaffolding` should become (moved under mirrored folders vs kept but treated as non-mirror)

- For each failing cluster, confirm the intended contract:
  - Validator severity policy (GUIDELINE vs ERROR) relative to SafeEdit “strict/interactive” behavior
  - Scaffolding templates: whether “scaffolded code must validate” is still required, and under which lint/type settings
  - State schema: decide whether `state.json` is single-branch state or multi-branch mapping, then align tests + docs

- Create a “move plan” before moving tests:
  - enumerate all modules with duplicate coverage (list above is a start)
  - for each, pick one canonical test file location and mark the others as “to merge/remove”
