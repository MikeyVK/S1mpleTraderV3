# Issue #53 Research: Quality Gates Configuration Analysis

**Issue:** Migrate quality gate configs to quality.yaml  
**Epic:** #49 - MCP Platform Configurability  
**Status:** Research Phase  
**Date:** 2026-01-01  
**Author:** AI Agent

---

## Research Objective

Analyze current quality gate implementation in `qa_manager.py` to identify all hardcoded configuration items that should be externalized to `config/quality.yaml`.

---

## Current Implementation Analysis

### File: `mcp_server/managers/qa_manager.py` (329 lines)

**Class:** `QAManager`

**Public Methods:**
- `run_quality_gates(files: list[str]) -> dict[str, Any]` - Orchestrates gate execution
- `check_health() -> bool` - Verifies QA tools are installed

**Private Methods:**
- `_run_pylint(files: list[str]) -> dict[str, Any]` (Lines 97-158)
- `_run_mypy(files: list[str]) -> dict[str, Any]` (Lines 176-221)
- `_run_pyright(files: list[str]) -> dict[str, Any]` (Lines 261-295)
- `_parse_pylint_output(output: str) -> list[dict[str, Any]]` (Lines 122-158)
- `_parse_mypy_output(output: str) -> list[dict[str, Any]]` (Lines 223-240)
- `_parse_pyright_output(output: str) -> list[dict[str, Any]]` (Lines 314-329)

---

## Hardcoded Configuration Inventory

### Gate 1: Pylint

**Location:** Lines 97-120

**Hardcoded Items:**

| Item | Value | Line |
|------|-------|------|
| Command | `python -m pylint` | 105-106 |
| Argument: enable | `--enable=all` | 108 |
| Argument: max-line-length | `--max-line-length=100` | 109 |
| Argument: output-format | `--output-format=text` | 110 |
| Timeout | 60 seconds | 117 |

**Output Parsing:**
- Format: Plain text
- Score extraction regex: `r"Your code has been rated at ([\d.]+)/10"` (Line 166)
- Issue extraction: Line-by-line parsing with complex regex (Lines 131-148)

### Gate 2: Mypy

**Location:** Lines 176-195

**Hardcoded Items:**

| Item | Value | Line |
|------|-------|------|
| Command | `python -m mypy` | 183-184 |
| Argument: strict | `--strict` | 186 |
| Argument: no-error-summary | `--no-error-summary` | 187 |
| Timeout | 60 seconds | 193 |

**Output Parsing:**
- Format: Plain text
- Issue extraction regex: `r"^(.+?):(\d+): (error|warning): (.+)$"` (Line 227)

### Gate 3: Pyright

**Location:** Lines 261-278

**Hardcoded Items:**

| Item | Value | Line |
|------|-------|------|
| Command | `pyright` (NOT `python -m pyright`) | 268 |
| Argument: outputjson | `--outputjson` | 269 |
| Timeout | 120 seconds | 274 |

**Output Parsing:**
- Format: JSON
- JSON path: `generalDiagnostics` (Line 323)
- Complex JSON structure parsing (Lines 314-329)

---

## Execution Flow Analysis

### Current Workflow

1. **File Validation** (Lines 36-44)
   - Check all files exist
   - Fail immediately if any missing
   - Add "File Validation" pseudo-gate to results

2. **Pylint Execution** (Lines 46-49)
   - Run `_run_pylint()`
   - If failed: Set `overall_pass = False`
   - **Continue to next gate** (no fail-fast)

3. **Mypy Execution** (Lines 51-54)
   - Run `_run_mypy()`
   - If failed: Set `overall_pass = False`
   - **Continue to next gate** (no fail-fast)

4. **Pyright Execution** (Lines 56-59)
   - Run `_run_pyright()`
   - If failed: Set `overall_pass = False`
   - Return aggregated results

**Key Finding:** Current behavior is **continue-on-error**, NOT fail-fast. All gates run even if earlier gates fail.

---

## Pattern Analysis from Existing Configs

### Pattern 1: workflows.yaml Structure

**Observed:** Issue #50 (workflows.yaml)

```yaml
version: "1.0"
workflows:
  feature:
    name: feature
    description: "..."
    phases: [...]
```

**Key Patterns:**
- Top-level `version` field
- Plural collection key (`workflows`, not `workflow`)
- Each item has: `name`, `description`, configuration
- Rich metadata embedded

### Pattern 2: labels.yaml Structure

**Observed:** Issue #51 (labels.yaml)

```yaml
version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "..."
```

**Key Patterns:**
- List of items with shared structure
- Each item has: `name`, metadata, configuration
- Validation via Pydantic models
- Sensible defaults

### Pattern 3: Pydantic Validation

**Observed:** Both Issue #50 and #51

```python
class ConfigModel(BaseModel):
    field: str = Field(..., description="...")
    model_config = {"frozen": True}
```

**Key Patterns:**
- Frozen models (immutability)
- Rich Field descriptions
- Validation constraints (ge, le, pattern)
- Default factories for complex types

---

## Output Parsing Strategy Analysis

### Strategy 1: Plain Text with Regex (Pylint, Mypy)

**Characteristics:**
- Line-by-line processing
- Regex pattern matching
- Extract: file, line, column, severity, message

**Example (Mypy):**
```
mcp_server/file.py:42: error: Missing return statement
```

**Regex:** `^(.+?):(\d+): (error|warning): (.+)$`

### Strategy 2: JSON Parsing (Pyright)

**Characteristics:**
- Single JSON object output
- Nested structure traversal
- Field extraction: `message`, `file`, `range`, `severity`, `rule`

**Example:**
```json
{
  "generalDiagnostics": [
    {
      "file": "mcp_server/file.py",
      "message": "Type mismatch",
      "severity": "error",
      "range": {"start": {"line": 41, "character": 10}}
    }
  ]
}
```

**Note:** Pyright line numbers are 0-based (converted to 1-based in code, Line 301)

---

## Configuration Dependencies

### External Dependencies

1. **Pylint Configuration:** `.pylintrc` (not managed by qa_manager.py)
2. **Mypy Configuration:** `mypy.ini` (not managed by qa_manager.py)
3. **Pyright Configuration:** `pyrightconfig.json` (not managed by qa_manager.py)

**Finding:** QA gates rely on BOTH:
- Command-line arguments (hardcoded in qa_manager.py)
- Tool-specific config files (external)

**Question for Planning:** Should quality.yaml manage tool-specific configs, or only gate orchestration?

---

## Edge Cases and Error Handling

### Timeout Behavior

**Code:** Lines 117, 193, 274

```python
proc = subprocess.run(..., timeout=60, check=False)
```

**Exception Handling:**
- `TimeoutExpired` → Result: `passed=False`, `score="Timeout"`
- `FileNotFoundError` → Result: `passed=False`, `score="Not Found"`

**Finding:** Timeouts are per-gate, not global

### Tool Availability Check

**Method:** `check_health()` (Lines 70-90)

**Checks:**
1. Pylint: `python -m pylint --version`
2. Mypy: `python -m mypy --version`
3. Pyright: `pyright --version`

**Behavior:** Returns `True` if all tools available, `False` otherwise

**Finding:** Health check does NOT fail startup, just returns boolean

---

## Code Volume Analysis

### Lines to Externalize

| Component | Lines | Description |
|-----------|-------|-------------|
| `_run_pylint()` | 62 | Gate execution + parsing |
| `_run_mypy()` | 46 | Gate execution + parsing |
| `_run_pyright()` | 57 | Gate execution + parsing |
| Hardcoded commands | ~15 | Command strings, arguments |
| Hardcoded timeouts | ~3 | Timeout values |
| Hardcoded patterns | ~3 | Regex patterns |
| **Total** | **186** | Lines with hardcoded config |

**Observation:** Almost 60% of qa_manager.py (186/329 lines) contains gate-specific logic that could be generalized.

---

## Extensibility Requirements (Observed)

### Use Case 1: Custom Timeouts

**Scenario:** Large codebases need longer timeouts  
**Current:** Requires code modification  
**Evidence:** Pyright timeout (120s) > Pylint/Mypy (60s)

### Use Case 2: Selective Gate Execution

**Scenario:** Disable slow gates during prototyping  
**Current:** No mechanism to disable gates  
**Evidence:** All gates always run

### Use Case 3: Custom Gates

**Scenario:** Add coverage gate, security gate (Bandit), formatter gate (Black)  
**Current:** Requires adding new `_run_*()` methods  
**Evidence:** Pattern duplication across 3 gate methods

---

## Key Research Findings

1. **Configuration Spread:** 15+ configuration points across 3 gates
2. **Execution Model:** Continue-on-error (NOT fail-fast as might be assumed)
3. **Output Diversity:** Three distinct parsing strategies (text/regex, regex, JSON)
4. **Code Duplication:** 60% of qa_manager.py is gate-specific boilerplate
5. **Pattern Precedent:** workflows.yaml and labels.yaml establish clear config patterns
6. **Tool Independence:** Gate commands are independent of tool configs (.pylintrc, mypy.ini)
7. **Health Checking:** Existing mechanism to verify tool availability
8. **No Priority System:** Gates run in fixed order (Pylint → Mypy → Pyright)

---

## Questions for Planning Phase

1. Should quality.yaml manage tool-specific configs (.pylintrc), or only orchestration?
2. Should execution mode (continue-on-error) be configurable?
3. Should gate execution order be configurable?
4. Should we support custom output parsers, or limit to regex/JSON?
5. Should file type filtering be per-gate or global?
6. Should health checks fail startup or just warn?

---

## Related Documentation

- **Issue #50:** workflows.yaml (config pattern reference)
- **Issue #51:** labels.yaml (Pydantic pattern reference)
- **Issue #49:** Epic overview (MCP Platform Configurability)
- **Code:** `mcp_server/managers/qa_manager.py` (current implementation)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial research - current state analysis only |

