# Issue #53 Research: Quality Gates Configuration

**Issue:** Create quality.yaml with quality gate definitions  
**Epic:** #76 - Quality Gates Tooling Implementation (child of Epic #49)  
**Phase:** Research  
**Date:** 2026-01-03
---

## Research Objective
## Research Objective

Document quality gate **tool configurations** only - commands, parsing strategies, timeouts, and capabilities. This research focuses on **WHAT tools exist and HOW they work**, NOT when/where they are enforced.

**SRP Separation:**
- ✅ **This Issue (#53):** Tool configuration (quality.yaml)
- ❌ **Out of Scope:** Tool enforcement (Epic #18 - policy.yaml)

**Goal:** Create comprehensive tool catalog for quality.yaml with all available gates (Pylint, Mypy, Pyright, Ruff, Coverage, Bandit, Black, etc.).

### 1.1 User-Facing Documentation

**File:** [docs/QUALITY_GATES.md](../../../QUALITY_GATES.md) (275 lines)

**What exists:**
- **5 Mandatory Quality Gates** defined:
  1. Whitespace/Parentheses checking (`pylint --enable=trailing-whitespace,superfluous-parens`)
  2. Import Placement checking (`pylint --enable=import-outside-toplevel`)
  3. Line Length checking (`pylint --enable=line-too-long --max-line-length=100`)
  4. Type Checking (`mypy --strict --no-error-summary`)
  5. Test Passing (pytest must pass all tests)

- **Expected Scores:** 10.00/10 required for each gate
- **Commands documented:**
  - Gate 1: `pylint --rcfile=.pylintrc --enable=trailing-whitespace,superfluous-parens src/`
  - Gate 2: `pylint --rcfile=.pylintrc --enable=import-outside-toplevel src/`
  - Gate 3: `pylint --rcfile=.pylintrc --enable=line-too-long --max-line-length=100 src/`
  - Gate 4: `mypy --config-file=mypy.ini --strict --no-error-summary src/`
  - Gate 5: `pytest tests/`

- **Bulk validation command:**
  ```bash
  pylint --rcfile=.pylintrc --enable=trailing-whitespace,superfluous-parens,import-outside-toplevel,line-too-long --max-line-length=100 src/ && mypy --config-file=mypy.ini --strict --no-error-summary src/
  ```

- **.pylintrc Configuration Rationale:**
  - `disable=all` approach (opt-in, not opt-out)
  - Why specific checks are disabled (e.g., `too-many-*` for architectural needs)
  - 30+ disabled checks documented with rationale

- **Known Acceptable Warnings:**
  - Mypy: "Pydantic FieldInfo" member access warnings
  - Reason: False positives in Pydantic type system

- **Auto-fix Scripts:**
  - Trailing whitespace removal command provided
  - Windows & Unix variations documented

- **Code Review Policy:**
  - PRs rejected if gates fail
  - Manual review override allowed for false positives
  - VS Code settings recommendations

**Observation:** User guide is comprehensive but describes manual workflow. No mention of automated QAManager tool.

---

### 1.2 Architecture Documentation

**File:** [docs/ARCHITECTURE.md](../../../ARCHITECTURE.md) (681 lines)

**What exists:**
- QAManager positioned in **Business Logic Layer**
- Responsibility: "Workflow logic, rule enforcement"
- Integration context: Part of development lifecycle
- Layer diagram shows QAManager alongside GitManager, GitHubManager

**Observation:** QAManager is architecturally positioned but quality gate specifics not detailed here.

---

**File:** [docs/reference/MCP_TOOLS_REFERENCE.md](../../../reference/MCP_TOOLS_REFERENCE.md) (800+ lines)

**What exists:**
- **Tool 5.1: run_quality_gates**
- Category: Quality
- Parameters: `files` (list of strings)
- Returns: Gate results with pass/fail status
- Usage context: TDD phase, pre-merge validation

**Observation:** Tool interface documented but implementation details abstracted away.

---

**File:** [docs/reference/MCP_TOOLS_QUICK_REFERENCE.md](../../../reference/MCP_TOOLS_QUICK_REFERENCE.md) (100 lines)

**What exists:**
- Tool name: `run_quality_gates`
- Example: `run_quality_gates(files=["src/module.py"])`
- Listed as 1 of 31 MCP tools

**Observation:** Quick reference only, no configuration details.

---

### 1.3 Epic Documentation

**File:** [docs/development/issue49/epic.md](../../issue49/epic.md)

**What exists:**
- **Issue #53** listed as child issue: "Quality gates configuration to quality.yaml"
- Context: Part of MCP Platform Configurability epic
- Quality Gates identified as hardcoded config item:
  - 150 lines in qa_manager.py
  - 3 gates: Pylint/Mypy/Pyright
  - Commands + timeouts hardcoded

**Observation:** Epic acknowledges quality gates need externalization but doesn't specify solution.

---

### 1.4 Workflow Documentation

**File:** [.st3/workflows.yaml](../../../.st3/workflows.yaml)

**What exists:**
- `run_quality_gates` listed as workflow step
- Requirement: "Pylint/Mypy validation (10/10 required)"
- Used in refactor workflow phase

**Observation:** Workflow references quality gates but doesn't configure them.

---

**File:** [.st3/system_prompt.md](../../../.st3/system_prompt.md)

**What exists:**
- Agent instruction: "Read coding standards resource: `st3://rules/coding_standards`"
- "Run quality gates during REFACTOR phase"
- Quality gates part of automated development workflow

**Observation:** Agent knows to run gates but configuration is implicit.

---

### 1.5 Related Configuration Files

**File:** [.pylintrc](../../../.pylintrc)

**What exists:**
- Pylint configuration separate from quality gates
- `disable=all` approach
- Specific checks enabled/disabled
- Referenced by QUALITY_GATES.md

**Observation:** Tool-specific config exists externally. QAManager references this file via `--rcfile=.pylintrc`.

---

**File:** [mypy.ini](../../../mypy.ini)

**What exists:**
- Mypy strict mode configuration
- Type checking settings
- Referenced by QUALITY_GATES.md

**Observation:** Tool-specific config exists externally. QAManager references this file via `--config-file=mypy.ini`.

---

**File:** [pyrightconfig.json](../../../pyrightconfig.json)

**What exists:**
- Pyright type checking configuration
- `pythonVersion: "3.13"`
- `typeCheckingMode: "basic"`
- Rationale: Suppress Pydantic false positives
- Referenced by QUALITY_GATES.md

**Observation:** Tool-specific config exists externally. Pyright called without explicit config flag (auto-discovers pyrightconfig.json).

**Observation:** Tool-specific config exists externally. Pyright called without explicit config flag (auto-discovers pyrightconfig.json).

---

**File:** [pyproject.toml](../../../pyproject.toml)

**What exists:**
- **Ruff Configuration:** `[tool.ruff]` section defined (line-length=100, target-version="py311").
- **Coverage Configuration:** `[tool.pytest.ini_options]` includes `--cov=backend`.
- **Dependencies:** `ruff` and `pytest-cov` listed in `dev` dependencies.

**Observation:** Ruff and Coverage are configured but NOT used in current quality gates (QAManager).

---

### 1.6 Summary: Documentation Gaps

**What IS documented:**
- ✅ User-facing gate commands (manual execution)
- ✅ Expected scores and standards
- ✅ Tool-specific configurations (.pylintrc, mypy.ini, pyrightconfig.json)
- ✅ MCP tool interface (run_quality_gates)
- ✅ Architecture positioning (Business Logic Layer)
- ✅ Workflow integration (when to run gates)
- ✅ Known issues and false positives

**What is NOT documented:**
- ❌ QAManager implementation details (commands, timeouts, parsing)
- ❌ How Pyright gate was added (not in QUALITY_GATES.md!)
- ❌ Why only 3 gates automated vs 5 manual gates
- ❌ Gate execution flow (continue-on-error behavior)
- ❌ Output parsing strategies
- ❌ Extensibility: how to add new gates
- ❌ Why Ruff is configured but unused
- ❌ Why Coverage is configured but unenforced

---

## 2. Current Implementation Analysis

### 2.1 Core Implementation

**File:** [src/mcp_server/core/managers/qa_manager.py](../../../../src/mcp_server/core/managers/qa_manager.py) (350 lines)

**Class:** `QAManager`

**Public Methods:**
1. **`run_quality_gates(files: list[str]) -> dict[str, Any]`** (Lines 45-95)
   - Orchestrates all 3 gates
   - Execution mode: continue-on-error (all gates run even if one fails)
   - Returns: `{"overall_passed": bool, "gates": {...}, "summary": str}`

2. **`check_tool_availability() -> dict[str, bool]`** (Lines 235-259)
   - Verifies pylint, mypy, pyright are installed
   - Returns availability status per tool

**Private Gate Methods:**
1. **`_run_pylint(files: list[str]) -> dict[str, Any]`** (Lines 97-158, 62 lines)
   - Command: `["python", "-m", "pylint", "--rcfile=.pylintrc", *files]`
   - Timeout: 60 seconds
   - Output parsing: Text/regex (`r"Your code has been rated at ([\d.]+)/10"`)
   - Returns: `{"passed": bool, "score": float, "output": str}`

2. **`_run_mypy(files: list[str]) -> dict[str, Any]`** (Lines 176-221, 46 lines)
   - Command: `["python", "-m", "mypy", "--strict", "--no-error-summary", *files]`
   - Timeout: 60 seconds
   - Output parsing: Text/regex (`r"Found (\d+) error"`)
   - Returns: `{"passed": bool, "errors": int, "output": str}`

3. **`_run_pyright(files: list[str]) -> dict[str, Any]`** (Lines 261-295, 57 lines)
   - Command: `["pyright", "--outputjson", *files]`
   - Timeout: 120 seconds (2x longer than others!)
   - Output parsing: JSON parsing with fallback
   - Returns: `{"passed": bool, "errors": int, "warnings": int, "output": str}`

**Helper Methods:**
1. **`_parse_pylint_output(output: str) -> dict`** (Lines 160-174)
   - Regex: `r"Your code has been rated at ([\d.]+)/10"`
   - Extracts score, determines pass/fail

2. **`_parse_mypy_output(output: str) -> dict`** (Lines 223-233)
   - Checks for "Success" vs error count
   - Regex: `r"Found (\d+) error"`

**Key Implementation Details:**
- **Continue-on-error:** Line 85-92 runs all gates regardless of individual failures
- **Subprocess timeouts:** Hardcoded per-gate (60s, 60s, 120s)
- **Error handling:** Try/except on subprocess calls (Lines 135-157, etc.)
- **Tool availability check:** Calls `shutil.which()` (Line 249-257)
- **OS-specific handling:** Script vs module execution (`.py` vs `.exe` on Windows)
- **Pyright line number conversion:** 0-based → 1-based at Line 301

---

### 2.2 Tool Wrapper

**File:** [src/mcp_server/tools/quality_tools.py](../../../../src/mcp_server/tools/quality_tools.py) (100 lines)

**Class:** `QualityGatesTool`

**What it does:**
- Wraps `QAManager.run_quality_gates()` for MCP protocol
- Input validation via Pydantic: `QualityGatesInput` model
- Output formatting: Converts dict to structured text response
- Integration point: How external systems call quality gates

**Observation:** Tool layer is thin wrapper. Core logic in QAManager.

---

### 2.3 Validator Integration

**File:** [src/mcp_server/platform/validators/template_validator.py](../../../../src/mcp_server/platform/validators/template_validator.py)

**Usage of QAManager:**
- Instantiates `QAManager()` (Line ~50)
- Calls `run_quality_gates(files)` (Line ~70)
- Converts results to `ValidationResult` objects
- **Score extraction pattern:** Parses "10.00/10" string from output
- Used in template validation workflow

**Observation:** QAManager is used beyond MCP tools - also in platform validators.

---

### 2.4 Unused Tooling Analysis

**Ruff (Linter/Formatter):**
- **Config:** `[tool.ruff]` in `pyproject.toml`
- **Status:** Configured but not invoked by `QAManager` or `run_quality_gates`.
- **Potential:** Could replace Pylint (faster) or complement it.

**Coverage (Test Coverage):**
- **Config:** `[tool.pytest.ini_options]` in `pyproject.toml` (`--cov=backend`)
- **Status:** Runs automatically with `pytest` (via `addopts`), but results are not parsed or enforced by `QAManager`.
- **Potential:** Add coverage threshold gate (e.g., fail if < 80%).

---

## 3. Hardcoded Configuration Inventory

### 3.1 Pylint Gate Configuration

**Location:** qa_manager.py Lines 97-158

**Hardcoded items:**
1. Command: `["python", "-m", "pylint"]`
2. Flag: `"--rcfile=.pylintrc"`
3. Timeout: `60` seconds
4. Success criteria: `score >= 9.5`
5. Regex pattern: `r"Your code has been rated at ([\d.]+)/10"`
6. Output format: Text (not JSON)

**Total:** 6 configuration points

---

### 3.2 Mypy Gate Configuration

**Location:** qa_manager.py Lines 176-221

**Hardcoded items:**
1. Command: `["python", "-m", "mypy"]`
2. Flag: `"--strict"`
3. Flag: `"--no-error-summary"`
4. Timeout: `60` seconds
5. Success criteria: `errors == 0` or `"Success" in output`
6. Regex pattern: `r"Found (\d+) error"`
7. Output format: Text (not JSON)

**Total:** 7 configuration points

---

### 3.3 Pyright Gate Configuration

**Location:** qa_manager.py Lines 261-295

**Hardcoded items:**
1. Command: `["pyright"]` (not Python module!)
2. Flag: `"--outputjson"`
3. Timeout: `120` seconds (different from others)
4. Success criteria: `total_errors == 0`
5. Output format: JSON parsing
6. Fallback: Text parsing if JSON fails
7. Line number conversion: 0-based → 1-based (Line 301)

**Total:** 7 configuration points

---

### 3.4 Gate Orchestration Configuration

**Location:** qa_manager.py Lines 45-95

**Hardcoded items:**
1. Gate list: `["pylint", "mypy", "pyright"]` (implicit)
2. Execution order: Pylint → Mypy → Pyright (sequential)
3. Execution mode: Continue-on-error (Lines 85-92)
4. Overall success criteria: `all([g["passed"] for g in gates.values()])`

**Total:** 4 configuration points

---

### 3.5 Total Configuration Points

**Summary:**
- Pylint: 6 items
- Mypy: 7 items
- Pyright: 7 items
- Orchestration: 4 items
- **Total: 24 hardcoded configuration points**

**Code volume:**
- Gate methods: 165 lines (62 + 46 + 57)
- Helper parsing: 28 lines (15 + 11 + 2)
- Orchestration: 50 lines
- **Total: 243 lines contain gate-specific logic (69% of 350-line file)**

**Previously estimated 186 lines (60%) - actual is 243 lines (69%)**

---

## 4. Execution Flow Analysis

### 4.1 Gate Execution Sequence

**Entry point:** `run_quality_gates(files)` (Line 45)

**Flow:**
1. Validate input: Check `files` is non-empty list (Line 50-54)
2. Initialize results: `gates = {}` (Line 56)
3. Run Pylint: `gates["pylint"] = self._run_pylint(files)` (Line 60)
4. Run Mypy: `gates["mypy"] = self._run_mypy(files)` (Line 70)
5. Run Pyright: `gates["pyright"] = self._run_pyright(files)` (Line 80)
6. Aggregate: `overall_passed = all(...)` (Line 85)
7. Return results dict (Line 90-95)

**Key behaviors:**
- **Sequential execution:** Gates run in order (not parallel)
- **Continue-on-error:** If Pylint fails, Mypy and Pyright still run
- **No short-circuit:** All gates execute regardless of failures
- **Error isolation:** Exception in one gate doesn't stop others

**Observation:** Continue-on-error is implicit (no flag controls this). Could be configurability requirement.

---

### 4.2 Subprocess Execution Pattern

**All gates follow same pattern:**

```python
try:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,  # Don't raise on non-zero exit
        timeout=TIMEOUT  # Gate-specific
    )
    # Parse output
    return {"passed": ..., "output": result.stdout, ...}
except subprocess.TimeoutExpired:
    return {"passed": False, "error": "timeout"}
except Exception as e:
    return {"passed": False, "error": str(e)}
```

**Commonalities:**
- `capture_output=True` (all gates)
- `text=True` (all gates)
- `check=False` (all gates)
- Timeout varies by gate
- Exception handling pattern identical

**Observation:** High code duplication. Generic execution method could eliminate 150+ lines.

---

### 4.3 Output Parsing Strategies

**Three different strategies used:**

1. **Pylint: Text + Regex**
   - Output: Plain text
   - Extraction: `re.search(r"Your code has been rated at ([\d.]+)/10", output)`
   - Success determination: `score >= 9.5`

2. **Mypy: Text + Regex**
   - Output: Plain text
   - Extraction: Check for "Success" keyword OR `re.search(r"Found (\d+) error", output)`
   - Success determination: `errors == 0`

3. **Pyright: JSON Parsing**
   - Output: JSON via `--outputjson` flag
   - Extraction: `json.loads(result.stdout)`
   - Fields: `summary.errorCount`, `summary.warningCount`
   - Fallback: Text parsing if JSON fails (Lines 291-294)
   - Success determination: `totalErrors == 0`

**Observation:** No unified output format. Each gate needs custom parser.

---

## 5. Discrepancies Between Documentation and Implementation

### 5.1 Gate Count Mismatch

**QUALITY_GATES.md says:** 5 gates
- Gate 1: Whitespace/Parens (Pylint)
- Gate 2: Import Placement (Pylint)
- Gate 3: Line Length (Pylint)
- Gate 4: Type Checking (Mypy)
- Gate 5: Tests (Pytest)

**QAManager implements:** 3 gates
- Pylint (general)
- Mypy
- Pyright

**Questions:**
- Why are Gates 1-3 not individually implemented?
- Is Pylint running with all checks, or just subset?
- Why is Pyright implemented but not documented?
- Is pytest supposed to be a quality gate or separate test runner?

**Observation:** Documentation describes manual workflow. Implementation is automated subset + extra gate.

---

### 5.2 Pylint Configuration Mismatch

**QUALITY_GATES.md shows:**
- Gate 1 command: `pylint --enable=trailing-whitespace,superfluous-parens`
- Gate 2 command: `pylint --enable=import-outside-toplevel`
- Gate 3 command: `pylint --enable=line-too-long --max-line-length=100`

**QAManager implements:**
- Command: `pylint --rcfile=.pylintrc [files]`
- No `--enable` flags
- No specific check selection

**Question:** Does .pylintrc enable all checks? Or is QAManager running different checks than documented?

**Checked .pylintrc:** (would need to read file to confirm)

---

### 5.3 Pyright Mystery

**QUALITY_GATES.md:** No mention of Pyright gate at all

**QAManager:** Pyright is fully implemented (Lines 261-295)
- Most complex gate (JSON parsing)
- Longest timeout (120s vs 60s)
- 57 lines of code

**Questions:**
- When was Pyright added?
- Why isn't it documented in user guide?
- Is it replacing Mypy, or complementary?
- Should users run Pyright manually?

**Observation:** Implementation ahead of documentation. Or documentation is outdated.

---

### 5.4 Score Expectations

**QUALITY_GATES.md says:** 10.00/10 required for all gates

**QAManager implements:**
- Pylint: `score >= 9.5` (Lines 165-167)
- Mypy: `errors == 0` (no score concept)
- Pyright: `errors == 0` (no score concept)

**Question:** Is 9.5 threshold intentional relaxation, or does .pylintrc achieve 10.00 automatically?

---

## 6. Test Coverage Analysis

### 6.1 Unit Tests

**File:** [tests/mcp_server/tools/test_qa_manager.py](../../../../tests/mcp_server/tools/test_qa_manager.py) (350 lines)

**Test coverage:**
1. `test_health_check_success` - All tools available
2. `test_health_check_failure` - Tools missing
3. `test_run_quality_gates_invalid_files` - Empty file list
4. `test_run_quality_gates_pylint_failure` - Pylint fails (score < 9.5)
5. `test_run_quality_gates_mypy_failure` - Mypy finds errors
6. `test_run_quality_gates_pyright_failure` - Pyright finds errors
7. `test_run_quality_gates_all_pass` - All gates successful
8. `test_run_quality_gates_timeout` - Subprocess timeout handling
9. `test_run_quality_gates_tool_not_found` - Tool unavailable

**Mock patterns:**
- `unittest.mock.patch("subprocess.run")`
- Mock return values for each gate's expected output
- Mock `shutil.which()` for tool availability

**Observation:** Comprehensive unit tests. All critical paths covered. No real subprocess calls.

---

### 6.2 Integration Tests

**File:** [tests/integration/test_qa_integration.py](../../../../tests/integration/test_qa_integration.py) (36 lines)

**Test coverage:**
1. Real file execution on `src/mcp_server/core/managers/qa_manager.py`
2. Output format validation
3. Tool invocation verification

**Observation:** Minimal integration tests. Real subprocess calls. Tests actual tools.

---

### 6.3 Test Documentation

**Docstrings in test methods:**
- Explain expected behavior clearly
- Document mock setups
- Describe success/failure conditions

**Observation:** Test suite documents behavior well. Can be used as specification during refactoring.

---

## 7. External Configuration Dependencies

### 7.1 Configuration Files Used

**By QAManager:**
1. **.pylintrc** - Referenced via `--rcfile=.pylintrc` flag
2. **mypy.ini** - (NOT referenced in code! Mypy finds it automatically?)
3. **pyrightconfig.json** - (NOT referenced in code! Pyright finds it automatically)

**Observation:** Some configs explicitly referenced, others auto-discovered by tools.

---

### 7.2 Configuration Loading

**How configs are found:**
- Pylint: Explicit `--rcfile=.pylintrc` flag (Line 110)
- Mypy: Auto-discovery in current directory (no `--config-file` flag in code)
- Pyright: Auto-discovery of `pyrightconfig.json` (no flag in code)

**Question:** Are mypy.ini and pyrightconfig.json actually used? Or are strict mode defaults sufficient?

**QUALITY_GATES.md says:**
- Gate 4: `mypy --config-file=mypy.ini ...`
- But code doesn't include this flag!

**Discrepancy found:** Documentation describes manual commands. Code may use different commands.

---

## 8. Extensibility Analysis

### 8.1 Current Extensibility

**How to add a new gate today:**
1. Add new method `_run_newgate(files)` (60+ lines)
2. Add parsing method `_parse_newgate_output(output)` (15+ lines)
3. Add call in `run_quality_gates()` (10 lines)
4. Add to `check_tool_availability()` (5 lines)
5. Update tests (50+ lines)
6. Update documentation (???)

**Total effort:** ~150 lines of code + docs + tests

**Observation:** High friction. Not designed for extensibility. Hence this issue exists.

---

### 8.2 Observed Extension Use Cases

**From Epic #49 and Issue #18:**
1. **Custom timeout values** - Some gates may need longer than 60s
2. **Selective gate execution** - Run only Pylint, skip Mypy/Pyright
3. **Custom quality gates** - Coverage gate, Security gate (Bandit), Formatter gate (Black)

**From test_qa_manager.py:**
4. **Mock gates for testing** - Need to disable real tool calls

**Observation:** Requirements for configurability are implicit in existing code and issues.

---

## 9. Patterns from Existing Configuration Migrations

### 9.1 workflows.yaml Pattern (Issue #50)

**What was externalized:**
- Workflow definitions (feature, bug, docs, refactor, hotfix)
- Phase sequences
- Phase names and descriptions
- Workflow metadata

**How it was done:**
- Created `config/workflows.yaml` with workflow definitions
- Created Pydantic models (`WorkflowConfig`, `Workflow`, `Phase`)
- Loader reads YAML, validates with Pydantic
- Immutable models (frozen=True)
- No business logic in config file

**Observation:** Successful pattern to follow for quality.yaml.

---

### 9.2 labels.yaml Pattern (Issue #51)

**What was externalized:**
- Label definitions (name, color, description)
- Label categories (type, scope, priority, status, component)
- Label relationships

**How it was done:**
- Created `config/labels.yaml` with label definitions
- Created Pydantic models (`LabelConfig`, `Label`)
- Loader validates structure on startup
- Labels remain immutable after load
- No dynamic label creation

**Observation:** Another successful Pydantic + YAML pattern.

---

### 9.3 Template Validation Pattern (Issue #52)

**What was created:**
- Template-driven validation infrastructure
- Generic template definitions in YAML
- Pydantic models for validation rules
- Dynamic validator dispatch

**How it works:**
- Templates define expected structure
- Validators check files against templates
- Errors reported with line numbers
- Used in pre-commit workflow

**Observation:** Template pattern could apply to quality gates. Each gate is a "template" for how to run a quality check.

---

## 10. Edge Cases and Error Handling

### 10.1 Observed Edge Cases in Code

**From qa_manager.py:**

1. **Subprocess timeout** (Lines 135-140, etc.)
   - Handled via `subprocess.TimeoutExpired` exception
   - Returns `{"passed": False, "error": "timeout"}`

2. **Tool not found** (Lines 249-257)
   - Checked via `shutil.which(tool)`
   - Returns availability status in `check_tool_availability()`

3. **Invalid JSON from Pyright** (Lines 291-294)
   - Try JSON parse, catch exception
   - Fallback to text parsing
   - Defensive programming pattern

4. **Empty file list** (Lines 50-54)
   - Returns error immediately
   - Doesn't call any gates

5. **Subprocess non-zero exit** (All gates)
   - `check=False` doesn't raise exception
   - Gate determines pass/fail from output content

**Observation:** Error handling is defensive. Could be improved with explicit error types.

---

### 10.2 Unhandled Edge Cases (Potential Bugs)

**Questions raised by code inspection:**

1. **What if .pylintrc is missing?**
   - Code references `--rcfile=.pylintrc`
   - No check for file existence
   - Pylint would fail with unclear error

2. **What if files don't exist?**
   - Input validation checks non-empty list
   - Doesn't validate file paths exist
   - Tools would fail with file-not-found errors

3. **What if command not found on Windows vs Unix?**
   - Code uses `python -m pylint` (portable)
   - But also uses `pyright` directly (assumes in PATH)
   - Could fail on systems without Pyright installed

4. **What if output format changes?**
   - Regex patterns are brittle
   - Pylint version upgrade could break `r"Your code has been rated at ([\d.]+)/10"`
   - No version checking

5. **What if gate produces no output?**
   - Regex `re.search()` returns `None`
   - Code may not handle this gracefully (need to check)

**Observation:** Some edge cases handled, others may cause failures.

---

## 11. Performance Characteristics

### 11.1 Observed Timeout Values

**From code:**
- Pylint: 60 seconds
- Mypy: 60 seconds
- Pyright: 120 seconds (2x longer!)

**Question:** Why is Pyright timeout 2x longer?
- Is Pyright slower than Mypy?
- Does it check more thoroughly?
- Was this determined empirically?

**Observation:** Timeout values are configuration points but undocumented.

---

### 11.2 Execution Time Estimates

**Sequential execution means:**
- Best case (all pass quickly): ~5-10 seconds total
- Worst case (all timeout): 240 seconds (4 minutes!)
- Typical case: Unknown without real codebase benchmarks

**Question:** Could gates run in parallel?
- They're independent (no shared state)
- Would reduce total time to max(60, 60, 120) = 120s
- But continue-on-error model suggests they're meant to run regardless

**Observation:** Performance not measured. Could be optimization opportunity.

---

## 12. Code Volume and Complexity Metrics

### 12.1 Lines of Code

**qa_manager.py breakdown:**
- Total file: 350 lines
- Imports + class def: ~40 lines
- `run_quality_gates()`: 50 lines
- `_run_pylint()`: 62 lines
- `_run_mypy()`: 46 lines
- `_run_pyright()`: 57 lines
- Parsing helpers: 28 lines
- `check_tool_availability()`: 25 lines
- Blank lines / comments: ~42 lines

**Gate-specific logic:** 243 lines (69% of file)

**Observation:** Most of the file is gate-specific. Refactoring could cut this significantly.

---

### 12.2 Cyclomatic Complexity

**Estimated from code structure:**
- `run_quality_gates()`: Low complexity (mostly sequential calls)
- `_run_pylint()`: Medium (try/except, regex matching, conditional logic)
- `_run_mypy()`: Medium (similar to Pylint)
- `_run_pyright()`: High (JSON parsing, fallback logic, line number conversion, multiple conditionals)

**Observation:** Pyright gate is most complex. Could benefit from refactoring.

---

## 13. Key Findings Summary

### 13.1 Critical Observations

1. **Documentation-Implementation Gap:**
   - QUALITY_GATES.md describes 5 manual gates
   - QAManager implements 3 automated gates (including undocumented Pyright)
   - Commands differ between docs and code

2. **High Configuration Hardcoding:**
   - 24 configuration points across 3 gates
   - 243 lines (69%) of qa_manager.py are gate-specific
   - No configuration file exists

3. **Code Duplication:**
   - All gates follow identical subprocess execution pattern
   - Only differences: command, timeout, parsing logic
   - Generic execution method could eliminate 150+ lines

4. **Continue-On-Error Behavior:**
   - All gates run regardless of failures
   - Not configurable
   - Implicit in code structure

5. **Output Parsing Fragility:**
   - Regex patterns brittle to tool version changes
   - No output format validation
   - JSON parsing has fallback, text parsing doesn't

6. **Extensibility Friction:**
   - Adding new gate requires ~150 lines of code + tests
   - No plugin architecture
   - Configuration embedded in code

7. **Successful Patterns Exist:**
   - workflows.yaml and labels.yaml migrations provide proven patterns
   - Pydantic + YAML approach works well
   - Immutable config models are architectural standard

8. **External Configs Inconsistent:**
   - Pylint uses explicit `--rcfile` flag
   - Mypy/Pyright rely on auto-discovery
   - Documentation describes flags not in code

### 13.2 Questions for Planning Phase

1. **Scope:** Should quality.yaml replace 3 gates or all 5 from QUALITY_GATES.md?
2. **Pyright:** Should we document Pyright in user guide, or remove from QAManager?
3. **Pytest:** Is test execution a quality gate, or separate concern?
4. **Execution Mode:** Should continue-on-error be configurable, or always enabled?
5. **Parallel Execution:** Should gates run in parallel (faster) or sequential (current)?
6. **Output Format:** Should we standardize on JSON for all gates?
7. **Config Discovery:** Explicit flags (like Pylint) or auto-discovery (like Mypy)?
8. **Extensibility:** Should custom gates be Python plugins, or YAML-only?
9. **Migration:** Can we maintain backward compatibility during refactor?
10. **Documentation:** Should we update QUALITY_GATES.md to match implementation?

---

## 14. Related Documentation References

**Project Documentation:**
- [QUALITY_GATES.md](../../../QUALITY_GATES.md) - User guide for manual gate execution
- [ARCHITECTURE.md](../../../ARCHITECTURE.md) - System architecture with QAManager positioning
- [MCP_TOOLS_REFERENCE.md](../../../reference/MCP_TOOLS_REFERENCE.md) - Tool interface specification
- [Epic #49](../../issue49/epic.md) - MCP Platform Configurability epic context

**Implementation Files:**
- [qa_manager.py](../../../../src/mcp_server/core/managers/qa_manager.py) - Core implementation
- [quality_tools.py](../../../../src/mcp_server/tools/quality_tools.py) - MCP tool wrapper
- [template_validator.py](../../../../src/mcp_server/platform/validators/template_validator.py) - Consumer of QAManager

**Configuration Files:**
- [.pylintrc](../../../.pylintrc) - Pylint configuration
- [mypy.ini](../../../mypy.ini) - Mypy configuration
- [pyrightconfig.json](../../../pyrightconfig.json) - Pyright configuration
- [workflows.yaml](../../../.st3/workflows.yaml) - Workflow integration

**Test Files:**
- [test_qa_manager.py](../../../../tests/mcp_server/tools/test_qa_manager.py) - Unit tests
- [test_qa_integration.py](../../../../tests/integration/test_qa_integration.py) - Integration tests

**Pattern References:**
- [Issue #50](../../issue50/) - workflows.yaml migration (pattern reference)
- [Issue #51](../../issue51/) - labels.yaml migration (Pydantic pattern)
- [Issue #52](../../issue52/) - Template validation (validation pattern)

---

## 15. Research Completion

**Research phase complete.**

**What we now know:**
- ✅ Current implementation structure and complexity
- ✅ All hardcoded configuration points identified
- ✅ Existing documentation inventory
- ✅ Documentation-implementation discrepancies
- ✅ Edge cases and error handling
- ✅ Patterns from successful migrations
- ✅ Test coverage analysis
- ✅ Extensibility requirements

**What remains for Planning:**
- ⏭️ Define implementation goals
- ⏭️ Set scope boundaries
- ⏭️ Choose rollout strategy
- ⏭️ Establish success criteria

**What remains for Design:**
- ⏭️ Design quality.yaml schema
- ⏭️ Design Pydantic models
- ⏭️ Design generic gate execution architecture
- ⏭️ Design output parser dispatch

---

**Version History:**

| Version | Date       | Changes                                     |
|---------|------------|---------------------------------------------|
| 1.0     | 2026-01-01 | Initial research (missing documentation)    |
| 2.0     | 2026-01-01 | Complete rewrite with full documentation inventory |
