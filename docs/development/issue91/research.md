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

## Cluster research: related issues + intended contracts

This section ties each observed failure cluster to prior design/planning work.
Goal: understand whether tests drifted from implementation, or implementation drifted from the documented contract.

### Cluster A: Validation severity (GUIDELINE vs STRICT) vs SafeEdit strict-mode behavior
**Primary failing test:**
- `tests/integration/mcp_server/validation/test_safe_edit_validation_integration.py::test_safe_edit_allows_with_guideline_warnings`

**Relevant design/planning:**
- Issue #52 defines a 3-layer validator with **guidelines as warnings only** (never blocks).
  - See `docs/development/issue52/research.md` (“Guidelines (LOOSE - warnings only, never blocks)”).
  - Issue #52 test strategy explicitly includes `test_safe_edit_allows_with_guideline_warnings()` as an integration test where “Warnings allow save”.
- Issue #38 SafeEditTool planning clarifies strict-mode control flow:
  - `mode == "strict" and not passed` → reject edit.
  - `interactive` may save with warnings.

**Hypothesis (drift source):**
- The failing case is a Pylint naming violation (`invalid-name`). That likely arrives via a **lint pipeline**, not via the template validator “guidelines” layer.
- If linting issues are treated as “passed=False” even for purely stylistic warnings, then strict mode will reject — which contradicts Issue #52’s “guidelines don’t block” expectation.

**Research question to answer before fixing anything:**
- Which rule set is authoritative for “GUIDELINE” severity?
  - Template guidelines only?
  - Or also lint rules, but with a severity mapping?

### Cluster B: Scaffold → Validate E2E drift
**Primary failing tests:**
- `tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py::test_scaffold_dto_passes_validation`
- `tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py::test_scaffold_tool_passes_validation`

**Relevant design/planning:**
- Issue #52 explicitly includes “Scaffold → Validate Cycle” end-to-end tests where **generated code validates**.
- Issue #52 quality gates explicitly state “No TODO/FIXME comments in committed code”.

**Observed drift:**
- DTO scaffold output currently fails due to `FIXME/TODO`, unused imports, formatting, and type mismatch (`None` default vs `str`).
- Tool scaffold output currently fails due to syntax error (“unterminated triple-quoted string literal”).

**Hypothesis (drift source):**
- Template content changed post-Issue #52 acceptance (or validator/linter ruleset got stricter) without updating the expected E2E contract.

**Research question:**
- Is the current intended contract still “all scaffolded code passes full validation/lint/type-check”, or should validation be template-aware and allow some patterns for generated code? (Issue #52 reads like it should pass.)

### Cluster C: State schema drift (state.json shape)
**Primary failing test:**
- `tests/integration/test_issue39_cross_machine.py::test_complete_cross_machine_flow`

**Relevant issue chain:**
- Issue #39 (dual-mode initialization + recovery) explicitly references:
  - Issue #42 (phase model)
  - Issue #45 (state.json structure)
  - Issue #48 (Git as SSOT)

**Observed drift:**
- The test expects `state.json` to be a mapping keyed by branch name.
- Current runtime evidence suggests `state.json` is a single-object “current branch state” document with a `branch` field.

**Research question:**
- Where is the canonical state schema documented now?
  - If Issue #45 exists as a design doc, it is not obviously present under `docs/development/issue45/` (needs locating).

### Cluster D: Git tools tests drifting from refactors (patching/exports)
**Primary failing tests:**
- `tests/unit/mcp_server/tools/test_git_checkout_state_sync.py::*` (patch expects `mcp_server.tools.git_tools.PhaseStateEngine`)
- `tests/unit/tools/test_git_tools.py::test_get_parent_branch_current_branch`

**Relevant refactor context:**
- Issue #64 documents significant refactors of git tools (renames, adding `base_branch`, updating tool registration and tests).

**Observed drift:**
- Tests patch attributes that no longer exist on the module (likely moved imports or changed import style).
- Another test’s patching/branch resolution expectation appears to be leaking the real current branch name.

**Research question:**
- Which version of `git_tools.py` interface is intended:
  - module-level imports exposed for patching, or
  - local imports inside execute() (common pattern used to avoid heavyweight imports)?

### Cluster E: Parent-branch auto-detection via reflog
**Primary failing test:**
- `tests/unit/mcp_server/tools/test_initialize_project_tool.py::test_branch_name_auto_detected`

**Relevant design/planning:**
- Issue #79 explicitly calls out git reflog limitations (non-persistent across machines, unreliable for old branches) and recommends threading `parent_branch` explicitly.

**Observed drift:**
- In the test environment, `git reflog show --all` fails (exit status 128), and `GitManager.get_current_branch()` is called twice.

**Research question:**
- Should tests treat reflog detection as best-effort and mock it out by default, or should the implementation avoid reflog calls when not needed?

### Cluster F: Encoding drift (UTF-8 BOM)
**Primary failing test:**
- `tests/mcp_server/managers/test_phase_state_engine_async.py::test_git_checkout_does_not_call_protected_save_state`

**Observed drift:**
- `mcp_server/tools/git_tools.py` begins with UTF-8 BOM bytes (`EF-BB-BF`), which breaks `ast.parse()` when reading source as plain UTF-8.

**Research question:**
- Should BOM be prevented repo-wide (recommended for Python), or should tests read source with `utf-8-sig` when doing AST parsing?

## Mirror goal: consolidate all mcp_server unit tests under tests/unit/mcp_server/

### Target principle
- Any **unit test whose subject is in `mcp_server/`** must live under `tests/unit/mcp_server/` in a mirrored path.
- `tests/integration/mcp_server/` remains for integration/E2E.

### Current “non-mirrored but mcp_server-related” unit tests (inventory)
These files are currently in non-mirrored locations but primarily import `mcp_server.*`:

From `tests/unit/tools/`:
- `tests/unit/tools/test_code_tools.py` (→ `mcp_server.core.exceptions`)
- `tests/unit/tools/test_dev_tools.py` (→ `mcp_server.tools.code_tools`)
- `tests/unit/tools/test_discovery_tools.py` (→ `mcp_server.tools.discovery_tools`)
- `tests/unit/tools/test_git_tools.py` (→ `mcp_server.tools.git_tools`)
- `tests/unit/tools/test_github_extras.py` (→ `mcp_server.config.label_config`)
- `tests/unit/tools/test_issue_tools.py` (→ `mcp_server.tools.issue_tools`)
- `tests/unit/tools/test_label_tools.py` (→ `mcp_server.config.label_config`)
- `tests/unit/tools/test_milestone_tools.py` (→ `mcp_server.tools.milestone_tools`)
- `tests/unit/tools/test_pr_tools.py` (→ `mcp_server.tools.pr_tools`)
- `tests/unit/tools/test_quality_tools.py` (→ `mcp_server.tools.quality_tools`)
- `tests/unit/tools/test_safe_edit_tool.py` (→ `mcp_server.tools.safe_edit_tool`)
- `tests/unit/tools/test_scaffold_tools.py` (→ `mcp_server.core.exceptions`)
- `tests/unit/tools/test_template_validation_tool.py` (→ `mcp_server.tools.template_validation_tool`)
- `tests/unit/tools/test_test_tools.py` (→ `mcp_server.core.exceptions`)
- `tests/unit/tools/test_tools_base.py` (→ `mcp_server.tools.base`)
- `tests/unit/tools/test_validation_tools.py` (→ `mcp_server.tools.validation_tools`)

From `tests/unit/scaffolding/`:
- `tests/unit/scaffolding/test_components.py` (→ `mcp_server.core.exceptions`)

From `tests/mcp_server/`:
- `tests/mcp_server/managers/test_phase_state_engine_async.py` (→ `mcp_server.managers.phase_state_engine`)

### Consolidation outcome (no fixes yet)
- Expected end-state: the above unit tests move under:
  - `tests/unit/mcp_server/tools/` (for tool tests)
  - `tests/unit/mcp_server/scaffolding/` (for scaffolding tests)
  - `tests/unit/mcp_server/managers/` (for manager tests)

This consolidation should reduce duplicated test files and make it harder for agents to create new tests in the wrong place.
