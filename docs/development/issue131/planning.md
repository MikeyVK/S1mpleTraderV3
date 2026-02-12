<!-- docs/development/issue131/planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-09 updated=2026-02-09 -->
# Quality Gates Config-Driven Execution - Planning

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-02-09  
**Issue:** #131

---

## Purpose

Plan refactoring of QAManager to use quality.yaml as source of truth for gate orchestration, enabling config-driven execution without code changes.

## Scope

**In Scope:**
- active_gates configuration field in quality.yaml
- Generic executor implementation
- Parsing strategy integration (text_regex, json_field, exit_code)
- Test updates for new architecture
- quality.yaml updates (enable Ruff, disable Mypy)

**Out of Scope:**
- New gate definitions (7 gates already exist)
- Epic #18 enforcement policies (separate issue)
- pyproject.toml changes
- standards.py refactoring (separate issue)
- Tool installation procedures

## Prerequisites

Read these first:
1. [Research](research.md) - Architecture analysis complete
2. [quality.yaml](../../../.st3/quality.yaml) - Current 7 gate definitions
3. [QualityConfig](../../../mcp_server/config/quality_config.py) - Pydantic model
4. [QAManager](../../../mcp_server/managers/qa_manager.py) - Current implementation

---

## Summary

Refactor QAManager from hardcoded 3-gate execution (pylint, mypy, pyright) to config-driven dynamic execution using quality.yaml `active_gates` list and generic gate executor pattern. Eliminates ~145 lines of duplicated parsing logic and enables adding/removing gates via configuration only.

**Additional scope:** Refactor standards.py to use quality.yaml (eliminate hardcoded JSON), install quality gate tools, and refactor pyproject.toml based on quality standards research to properly separate IDE baseline from CI/CD strict settings.

---

## Work Packages

### WP1: Configuration Extension

**Deliverables:**
- Add `active_gates: list[str]` field to quality.yaml
- Update QualityConfig Pydantic model with validation
- Ensure active gates exist in gates catalog (cross-validation)

**Acceptance Criteria:**
- quality.yaml has `active_gates: ["pylint", "ruff", "pyright"]`
- QualityConfig.load() validates active gates exist
- Invalid gate ID raises clear error
- Schema validated by Pydantic

**Files Modified:**
- `.st3/quality.yaml`
- `mcp_server/config/quality_config.py`

---

### WP2: Generic Parsing Strategies

**Deliverables:**
- Create parsing strategy executor methods
- Support text_regex, json_field, exit_code strategies
- Use quality.yaml parsing configuration

**Acceptance Criteria:**
- Can parse text output using regex patterns from quality.yaml
- Can parse JSON output using field paths from quality.yaml
- Can interpret exit codes from quality.yaml
- All parsing uses quality.yaml specs (no hardcoded patterns)

**Files Modified:**
- `mcp_server/managers/qa_manager.py` (new methods)

---

### WP3: Generic Gate Executor

**Deliverables:**
- Single generic `_run_gate()` method
- Subprocess invocation with timeout
- Dynamic parsing strategy dispatch
- Success evaluation using quality.yaml criteria

**Acceptance Criteria:**
- Works for any gate in quality.yaml catalog
- Gate number assigned dynamically
- Uses gate.parsing strategy
- Uses gate.success criteria
- Handles timeout and FileNotFoundError
- Returns consistent result structure

**Files Modified:**
- `mcp_server/managers/qa_manager.py` (new method)

---

### WP4: Orchestration Refactor

**Deliverables:**
- Refactor `run_quality_gates()` to read active_gates
- Dynamic gate execution loop
- Scope filtering per gate

**Acceptance Criteria:**
- Iterates over `quality_config.active_gates`
- Calls generic `_run_gate()` for each
- Gate number increments dynamically

---

### WP8: Standards Resource Refactoring

**Deliverables:**
- Refactor standards.py to read from quality.yaml (eliminate hardcoded JSON)
- Return active_gates in response
- Update tests for dynamic behavior

**Acceptance Criteria:**
- `st3://rules/coding_standards` returns dynamic configuration
- Reads active_gates from quality.yaml
- No hardcoded tool lists
- Test validates new implementation

**Files Modified:**
- `mcp_server/resources/standards.py`
- `tests/unit/mcp_server/resources/test_standards.py`

---

### WP9: Tool Installation & Verification

**Deliverables:**
- Install all tools from requirements-dev.txt in venv
- Verify ruff executable available
- Document tool versions

**Acceptance Criteria:**
- `pip install -r requirements-dev.txt` succeeds
- `ruff --version` returns version number
- `pyright --version` works
- All quality gates tools executable

**Files Modified:**
- None (installation only)
- Document installation in planning

---

### WP10: pyproject.toml Configuration Refactor

**Deliverables:**
- Refactor pyproject.toml based on quality standards research
- Separate IDE-friendly baseline from CI/CD strict settings
- Document rationale for each configuration choice

**Acceptance Criteria:**
- pyproject.toml reflects coding standards from docs/coding_standards/
- Quality.yaml CI/CD overrides clearly documented
- Dual-user scenario (IDE vs CI/CD) explicitly configured
- Configuration decisions traceable to quality standards docs

**Dependencies:**
- **Blocked by:** Separate research into quality gate settings (new research phase)

**Files Modified:**
- `pyproject.toml`
- `.st3/quality.yaml` (CI/CD overrides)
- Applies gate.scope filtering if defined
- Skips gates with no matching files
- Aggregates results correctly

**Files Modified:**
- `mcp_server/managers/qa_manager.py` (refactor existing method)

---

### WP5: Legacy Code Removal

**Deliverables:**
- Remove `_run_pylint()` method
- Remove `_run_mypy()` method
- Remove `_run_pyright()` method
- Remove `_parse_pylint_output()` method
- Remove `_parse_mypy_output()` method
- Remove `_parse_pyright_output()` method
- Remove `_extract_pylint_score()` method

**Acceptance Criteria:**
- ~145 lines of code removed
- No references to removed methods
- All functionality replaced by generic executor

**Files Modified:**
- `mcp_server/managers/qa_manager.py` (deletions)

---

### WP6: Test Updates

**Deliverables:**
- Update existing QAManager tests
- Add tests for active_gates validation
- Add tests for generic executor with different strategies
- Update quality_config tests for new field

**Acceptance Criteria:**
- All existing tests pass or updated
- New tests for active_gates field
- Test generic executor with all 3 parsing strategies
- Test invalid active_gates raises error
- Code coverage maintained

**Files Modified:**
- `tests/unit/mcp_server/managers/test_qa_manager.py`
- `tests/unit/mcp_server/config/test_quality_config.py`

---

### WP7: Quality Gates Configuration Update

**Deliverables:**
- Update quality.yaml active_gates
- Enable Ruff (fast modern linter)
- Disable Mypy (redundant with Pyright)

**Acceptance Criteria:**
- `active_gates: ["pylint", "ruff", "pyright"]`
- Ruff now runs when run_quality_gates called
- Mypy no longer runs
- All 3 active gates execute successfully

**Files Modified:**
- `.st3/quality.yaml`

---

## TDD Cycles

### Cycle 1: Config Model Extension + Tool Installation (WP1, WP9)

**Goal:** Add and validate active_gates configuration, install tools

**Tests:**
- `test_quality_config_with_active_gates()` - Load config with active_gates
- `test_active_gates_validation_fails_for_missing_gate()` - Invalid gate ID error
- `test_active_gates_defaults_to_empty()` - No active_gates field defaults
- (Manual) Verify ruff executable installed and working

**Success Criteria:**
- Tests pass
- QualityConfig has active_gates field
- Cross-validation prevents invalid gate IDs
- All tools from requirements-dev.txt installed

---

### Cycle 2: Generic Parsing Strategies + Standards Refactor (WP2, WP8)

**Goal:** Implement reusable parsing executors, refactor standards.py

**Tests:**
- `test_parse_text_regex_extracts_patterns()` - Regex parsing works
- `test_parse_json_field_extracts_paths()` - JSON field extraction works
- `test_parse_exit_code_interprets_codes()` - Exit code interpretation works
- `test_parsing_uses_quality_yaml_config()` - No hardcoded patterns
- `test_standards_resource_reads_quality_yaml()` - Standards.py dynamic
- `test_standards_resource_reflects_active_gates()` - Active gates in response

**Success Criteria:**
- Tests pass
- Three parsing methods exist
- All use quality.yaml configuration
- standards.py no hardcoded JSON

---

### Cycle 3: Generic Gate Executor (WP3)

**Goal:** Single method executes any gate

**Tests:**
- `test_run_gate_executes_subprocess()` - Subprocess called correctly
- `test_run_gate_uses_parsing_strategy()` - Dispatches to correct parser
- `test_run_gate_evaluates_success_criteria()` - Uses quality.yaml success definition
- `test_run_gate_handles_timeout()` - Timeout exception handled
- `test_run_gate_handles_not_found()` - FileNotFoundError handled
- `test_run_gate_assigns_dynamic_gate_number()` - Gate number not hardcoded

**Success Criteria:**
- Tests pass
- Generic executor works for all gates
- No tool-specific logic

---

### Cycle 4: Integration + Cleanup (WP4, WP5, WP6, WP7)

**Goal:** Integrate all components, remove legacy code, update quality.yaml

**Tests:**
- `test_run_quality_gates_reads_active_gates()` - Uses config not hardcoded
- `test_run_quality_gates_executes_all_active()` - All active gates run
- `test_run_quality_gates_with_ruff_enabled()` - Ruff executes when active
- `test_run_quality_gates_skips_mypy_when_inactive()` - Disabled gates don't run
- `test_run_quality_gates_applies_scope_filtering()` - Scope filters work
- `test_legacy_methods_removed()` - Old methods deleted

**Success Criteria:**
- Tests pass
- All active gates execute
- Legacy code removed
- Integration test with real quality.yaml passes
- Ruff enabled, Mypy disabled in quality.yaml

---

### Cycle 5: Configuration Refinement (WP10)

**Goal:** Refactor pyproject.toml based on quality standards research

**Tests:**
- Manual validation against docs/coding_standards/
- Verify IDE experience with lenient settings
- Verify CI/CD strict enforcement via quality.yaml overrides

**Success Criteria:**
- pyproject.toml reflects quality standards
- Dual-user scenario properly configured
- CI/CD overrides documented in quality.yaml
- Configuration choices traceable to standards docs

**Dependencies:**
- **Blocked by:** Quality gate settings research (separate research phase)

---

## Related Documentation

- [research.md](research.md) - Architecture analysis with 6 investigations
- [.st3/quality.yaml](../../../.st3/quality.yaml) - Gate catalog (7 gates defined)
- [quality_config.py](../../../mcp_server/config/quality_config.py) - Config models
- [qa_manager.py](../../../mcp_server/managers/qa_manager.py) - Current implementation
- Issue #49 - Epic: MCP Platform Configurability

---

## Dependencies

**Blocking:**
- None (standalone refactor)

**Blocked By:**
- Research complete ✅
- **WP10 blocked by:** Quality gate settings research (separate research document)

**Enables:**
- Issue #18: Epic - TDD & Coverage Enforcement (quality gate policies)
- Dynamic gate addition without code changes
- Proper IDE vs CI/CD configuration separation

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Tests break during refactor | Medium | High | TDD approach - write tests first |
| Parsing strategies incomplete | Low | Medium | Research identified all 3 strategies used |
| Performance regression | Low | Low | Generic executor same pattern as current |
| Quality.yaml schema breaking change | Low | Medium | No other consumers confirmed |

---

## Milestones

1. **Config Foundation** (WP1, WP9) - active_gates field validated, tools installed
2. **Parsing Layer** (WP2, WP8) - Generic parsers working, standards.py refactored
3. **Executor Layer** (WP3) - Generic gate runs
4. **Integration** (WP4, WP5, WP6, WP7) - run_quality_gates refactored, legacy removed, Ruff enabled
5. **Configuration Refinement** (WP10) - pyproject.toml optimized per quality standards (requires separate research)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-09 | Agent | Complete planning - 7 work packages, 4 TDD cycles, dependencies/risks documented |
| 1.1 | 2026-02-09 | Agent | Extended scope - added WP8 (standards.py refactor), WP9 (tool installation), WP10 (pyproject.toml refactor), added Cycle 5, WP10 blocked by separate quality standards research |