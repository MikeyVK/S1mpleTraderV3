<!-- docs\development\issue247\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-21T20:21Z updated= -->
# Test Structure Separation: backend/ vs mcp_server/

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-21

---

## Purpose

Foundation for the actual restructuring migration in the planning/TDD phases. All decisions must be based on verified import analysis, not directory names.

## Scope

**In Scope:**
All files under tests/, conftest.py hierarchy, pyproject.toml testpaths, __init__.py structure, mcp_server/tools/test_tools.py rename

**Out of Scope:**
Actual file moves (planning/TDD phase), test execution behavior changes (issue #103), CI/CD pipeline changes, content changes to test files

## Prerequisites

Read these first:
1. Issue #247 created with initial inventory
2. 2318 tests passing on main (verified Feb 2026)
3. Import-based scan completed on all 196 test files
---

## Problem Statement

The tests/ directory mixes pre-MCP backend tests and MCP server tests without structural separation. Import-based analysis of all 196 test files reveals: 27 backend-only, ~160 mcp_server-only, 3 MIXED (import both), ~35 NONE (template rendering, no production imports → MCP). No path exists to run only backend tests or only MCP tests cleanly.

## Research Goals

- Produce a verified, import-based ownership matrix for all 196 test files
- Identify mis-classified files in the current directory structure
- Define the conftest.py split strategy (global autouse currently runs MCP singleton reset on backend tests)
- Specify pyproject.toml testpaths and norecursedirs changes
- Identify the 3 MIXED files and determine correct placement
- List cleanup actions: empty dirs, supporting file moves

---

## Background

The test structure predates the MCP server implementation. Backend tests existed in tests/unit/core/, tests/unit/dtos/, etc. MCP server development added tests alongside without ownership enforcement. Result: interleaved single tree where backend and MCP tests exist at every level of the hierarchy.

---

## Findings

Import scan results (196 files total):

BACKEND (27 files):
- tests/parity/test_normalizer.py
- tests/test_tier1_templates.py  ← SURPRISE: in tests/ root but imports backend
- tests/unit/backend/core/test_phase_detection.py
- tests/unit/backend/core/test_scope_encoder.py
- tests/unit/core/interfaces/test_eventbus.py
- tests/unit/core/interfaces/test_worker.py
- tests/unit/core/test_enums.py
- tests/unit/core/test_eventbus.py
- tests/unit/core/test_flow_initiator.py
- tests/unit/core/test_strategy_cache.py
- tests/unit/dtos/ (16 files: execution, shared, state, strategy, causality)
- tests/unit/services/test_template_engine.py  ← SURPRISE: in services/ but imports backend
- tests/unit/utils/test_id_generators.py  ← SURPRISE: in utils/ but imports backend

MCP_SERVER (~160 files):
- tests/unit/core/test_exceptions.py  ← MIS-CLASSIFIED: imports mcp_server.core.exceptions
- tests/unit/core/test_validation_error_enhancement.py  ← MIS-CLASSIFIED: imports mcp_server
- All of tests/unit/mcp_server/ (55 files)
- All of tests/mcp_server/ (35 legacy taskXX files)
- All of tests/unit/tools/ (25 files)
- All of tests/unit/config/ (13 files)
- All of tests/unit/scaffolders/ (6 files)
- All of tests/unit/managers/ (5 files)
- All of tests/unit/scaffolding/ (3 files)
- tests/unit/services/test_search_service.py
- tests/unit/templates/ (1 file)
- tests/unit/validation/ (2 files)
- tests/integration/ (23 files)
- tests/acceptance/ (1 file)
- tests/regression/ (1 file)
- tests/ root tier0/tier1/tier2/template cycle files (~20 files)

NONE→MCP (~35 files, no direct production imports, test template rendering via pathlib+jinja2):
- All tests/mcp_server/scaffolding/test_tier3_* (16 files)
- All tests/mcp_server/scaffolding/test_taskXX_* (7 files)
- tests/test_tier0_*, test_tier2_*, test_design_*, test_artifacts_yaml_*
- tests/unit/config/test_labels_yaml_conventions.py
- tests/unit/templates/test_generic_doc_template.py
- tests/unit/test_pytest_config.py (meta-test)

MIXED (3 files — import both backend AND mcp_server):
- tests/integration/mcp_server/validation/test_safe_edit_validation_integration.py
- tests/integration/test_concrete_templates.py
- tests/integration/test_workflow_cycle_e2e.py

CONFTEST PROBLEM:
- tests/conftest.py resets MCP config singletons (IssueConfig, ScopeConfig, etc.) via autouse=True
- This means every backend test also triggers MCP singleton reset — unnecessary coupling
- After split: global conftest.py should not contain MCP-specific fixtures
- tests/backend/conftest.py: backend-only fixtures, no MCP imports
- tests/mcp_server/conftest.py: MCP singleton reset (autouse=True stays here)

EMPTY DIRS:
- tests/unit/assembly/ (only __init__.py, no tests)
- tests/unit/dtos/build_specs/ (only __init__.py, no tests)

SUPPORTING FILES CLASSIFICATION:
- tests/fixtures/artifact_test_harness.py → MCP (used by integration tests)
- tests/fixtures/workflow_fixtures.py → MCP
- tests/parity/normalization.py → backend (used by test_normalizer.py)
- tests/baselines/ → MCP (used by regression tests)

## Additional Findings (2026-02-21 session)

### 1. tests/test_tier1_templates.py — NOT a backend test
Initial classification as "backend" was wrong. The two `backend.*` references are string literals used as Jinja2 render input and assertion data — the test verifies that the template passes through whatever project import string you give it. The test itself is purely MCP scaffolding validation. Fix: replace `"from backend.core import Worker"` with a neutral string like `"from myproject.core import Worker"`. No semantic change, coupling removed.

### 2. MIXED files — coupling should be removed, not accommodated
The 3 MIXED integration files accumulated backend imports over time. Each case is different:

**test_concrete_templates.py** (3 clusters of `backend.*`):
- Line 207: string literal `"from backend.core import Something"` → replace with neutral string
- Lines 257–267: asserts that the scaffolded worker template generates specific `backend.core.interfaces.*` import paths → change to pattern-based assertions (e.g., assert `"IWorkerLifecycle"` appears, not the full import path). This is the correct approach: the test validates behaviour (worker implements the protocol), not the hardcoded namespace.

**test_safe_edit_validation_integration.py** (lines 211, 245):
- Both occurrences are inside multiline string fixtures written to a temp file to trigger SafeEditTool validation. Fix: replace `BaseWorker` fixture with a generic ABC subclass that triggers the same validation path.

**test_workflow_cycle_e2e.py** (line 13):
- Real Python import: `from backend.core.phase_detection import ScopeDecoder`
- Root cause: `scope_encoder.py` and `phase_detection.py` are mis-placed in `backend/core/`. Both files have zero `backend.*` imports — only stdlib + yaml. They implement MCP workflow tooling (commit-scope encoding, phase detection from state.json). They belong in `mcp_server/core/`.
- Fix: move both files to `mcp_server/core/`, update 6 import sites (see below), tests become pure MCP.

### 3. scope_encoder.py and phase_detection.py mis-placed in backend/
Blast radius — all current import sites:
```
mcp_server/managers/git_manager.py:8          from backend.core.scope_encoder import ScopeEncoder
mcp_server/managers/project_manager.py:26     from backend.core.phase_detection import ScopeDecoder
mcp_server/tools/discovery_tools.py:10        from backend.core.phase_detection import PhaseDetectionResult, ScopeDecoder
tests/unit/backend/core/test_scope_encoder.py:18   from backend.core.scope_encoder import ScopeEncoder
tests/unit/backend/core/test_phase_detection.py:23 from backend.core.phase_detection import PhaseDetectionResult, ScopeDecoder
tests/integration/test_workflow_cycle_e2e.py:13    from backend.core.phase_detection import ScopeDecoder
```
Total: 3 production files, 2 test files, 1 integration test = 6 sites.

### 4. tests/unit/test_pytest_config.py
No `backend.*` or `mcp_server.*` imports — reads `pyproject.toml` only. Tests the MCP workflow guard (`-m not integration` in addopts prevents live GitHub API calls). Classification: MCP infrastructure. Target: `tests/mcp_server/unit/test_pytest_config.py`.

### 5. Test files for relocated modules
After moving `scope_encoder.py` and `phase_detection.py`:
- `tests/unit/backend/core/test_scope_encoder.py` → `tests/mcp_server/unit/core/test_scope_encoder.py`
- `tests/unit/backend/core/test_phase_detection.py` → `tests/mcp_server/unit/core/test_phase_detection.py`

---

## Open Questions

*All open questions resolved — see Additional Findings above.*


## Related Documentation
- **[pytest documentation: testpaths configuration][related-1]**
- **[pyproject.toml [tool.pytest.ini_options]][related-2]**

<!-- Link definitions -->

[related-1]: pytest documentation: testpaths configuration
[related-2]: pyproject.toml [tool.pytest.ini_options]

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |