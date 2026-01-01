# Issue #53 Research: Quality Gates Configuration (quality.yaml)

**Issue:** Migrate quality gate configs to quality.yaml  
**Epic:** #49 - MCP Platform Configurability  
**Status:** Research Phase  
**Date:** 2026-01-01  
**Author:** AI Agent

---

## Executive Summary

**The Problem:**
Quality gate configurations (Pylint, Mypy, Pyright) are hardcoded in `qa_manager.py`, violating "Config Over Code" principle. Teams cannot customize timeouts, command-line arguments, or add custom quality gates without modifying Python code.

**The Solution:**
Create `config/quality.yaml` following established patterns from Issue #50 (workflows.yaml) and #51 (labels.yaml). Use Pydantic models for validation, enable custom gates, and make all parameters configurable.

**The Innovation:**
Extensible quality gate system where teams can define custom gates (e.g., coverage thresholds, security scanners) without code changes. Each gate is independently configurable with timeouts, arguments, and output parsing patterns.

**Impact:**
- ✅ Teams can customize quality gates per project
- ✅ Add custom gates (coverage, security, formatting) via YAML
- ✅ Adjust timeouts for CI/CD environments
- ✅ Disable specific gates for prototyping
- ✅ Zero code changes for gate configuration

---

## Scope: Quality Gate Configuration System

**What This Issue Delivers:**

**Phase 1: Configuration Schema**
- Create `config/quality.yaml` with gate definitions
- Pydantic model: `QualityConfig` with validation
- Gate schema: name, command, timeout, output patterns, enabled flag

**Phase 2: QAManager Migration**
- Update `QAManager` to load config from YAML
- Remove hardcoded gate configurations (100+ lines)
- Preserve existing behavior (3 gates: Pylint, Mypy, Pyright)

**Phase 3: Extensibility**
- Support custom quality gates
- Output pattern matching (regex)
- Conditional gate execution (file type filtering)

**What This Issue Does NOT Deliver:**
- ❌ Coverage gate implementation (separate issue)
- ❌ Security scanning tools (separate issue)
- ❌ Custom linter configurations (.pylintrc, mypy.ini) - those stay in their standard locations
- ❌ Test execution (that's pytest, not a quality gate)

---

## Problem Statement

### Current Architecture: Hardcoded Quality Gates

**File:** `mcp_server/managers/qa_manager.py`

**Gate 1: Pylint (Lines 97-120)**
```python
cmd = [
    python_exe, "-m", "pylint",
    *files,
    "--enable=all",
    "--max-line-length=100",  # ← Hardcoded
    "--output-format=text"
]
timeout=60  # ← Hardcoded
```

**Gate 2: Mypy (Lines 176-193)**
```python
cmd = [
    python_exe, "-m", "mypy",
    *files,
    "--strict",  # ← Hardcoded
    "--no-error-summary"
]
timeout=60  # ← Hardcoded
```

**Gate 3: Pyright (Lines 261-278)**
```python
cmd = [
    _venv_script_path(_pyright_script_name()),
    "--outputjson",  # ← Hardcoded
    *files,
]
timeout=120  # ← Hardcoded
```

**The Problem:**
1. **Configuration Lock-In:** Cannot change timeout without code modification
2. **No Extensibility:** Cannot add custom gates (e.g., coverage, security)
3. **Team Inflexibility:** Different teams have different quality standards
4. **CI/CD Friction:** Long timeouts block CI pipelines, short timeouts fail slow builds
5. **Testing Difficulty:** Cannot disable gates for local testing

### Discovery: Quality Gate Parameters

**Audit Complete:** 3 quality gates, 15+ configuration points

**Hardcoded Items:**

| Parameter | Gate | Current Value | Configurability Need |
|-----------|------|---------------|---------------------|
| **Command** | Pylint | `python -m pylint` | LOW (standard) |
| **Args** | Pylint | `--enable=all --max-line-length=100` | HIGH (team-specific) |
| **Timeout** | Pylint | 60 seconds | HIGH (CI/CD variation) |
| **Command** | Mypy | `python -m mypy` | LOW (standard) |
| **Args** | Mypy | `--strict --no-error-summary` | MEDIUM (strictness levels) |
| **Timeout** | Mypy | 60 seconds | HIGH (large codebases) |
| **Command** | Pyright | `pyright` | LOW (standard) |
| **Args** | Pyright | `--outputjson` | LOW (output format needed) |
| **Timeout** | Pyright | 120 seconds | HIGH (slow type checking) |
| **Output Pattern** | All | Hardcoded parsing | MEDIUM (custom tools) |
| **Enabled** | All | Always on | HIGH (disable for prototyping) |

**Additional Findings:**
- Pylint score extraction: Regex pattern `"Your code has been rated at ([\d.]+)/10"` (line 166)
- Mypy error parsing: Regex pattern `"^(.+?):(\d+): (error|warning): (.+)$"` (line 227)
- Pyright JSON parsing: Uses `--outputjson` flag (line 269)

### Architectural Insight: Gate as First-Class Entity

**User Requirement:**
"I want to add custom quality gates (coverage, security scanners, formatters) without modifying Python code. Each gate should be independently configurable."

**Design Principle:**
A quality gate is a **command** that:
1. Accepts file paths as arguments
2. Returns exit code (0 = pass, non-zero = fail)
3. Outputs structured data (text, JSON, XML)
4. Has timeout constraints
5. Can be enabled/disabled

This led to discovery of **Gate abstraction pattern**.

---

## Research Findings

### Finding 1: Established Config Pattern

**From Issue #50 (workflows.yaml):**
```yaml
version: "1.0"
workflows:
  feature:
    name: feature
    description: "Full development workflow"
    phases: [research, planning, design, tdd, integration, documentation]
```

**Pattern:**
- `version` field for schema evolution
- Top-level collections (`workflows`, `labels`)
- Rich metadata (name, description)
- Sensible defaults

**Apply to quality.yaml:**
```yaml
version: "1.0"
quality_gates:
  pylint:
    name: pylint
    description: "Python linting for code quality"
    command: ["python", "-m", "pylint"]
    args: ["--enable=all", "--max-line-length=100"]
    timeout: 60
    enabled: true
```

### Finding 2: Output Parsing Strategies

**Current Implementation:**

**Pylint:** Text parsing with regex
```python
pattern = r"Your code has been rated at ([\d.]+)/10"
```

**Mypy:** Line-by-line regex parsing
```python
pattern = r"^(.+?):(\d+): (error|warning): (.+)$"
```

**Pyright:** JSON parsing
```python
json.loads(output)
data.get("generalDiagnostics", [])
```

**Design Decision:**
Support **multiple output formats**:
- `text`: Plain text, no parsing
- `regex`: Line-by-line regex matching
- `json`: JSON structure parsing

### Finding 3: Gate Execution Flow

**Current Flow:**
1. File validation (check files exist)
2. Run Gate 1 (Pylint) → **fail-fast** if failed
3. Run Gate 2 (Mypy) → **fail-fast** if failed
4. Run Gate 3 (Pyright) → **fail-fast** if failed
5. Return aggregated results

**Key Insight:** Fail-fast behavior is intentional (blocks on first gate failure)

**Design Decision:**
Make fail-fast **configurable**:
```yaml
execution:
  mode: fail-fast  # OR: continue-on-error
```

### Finding 4: Custom Gate Use Cases

**Team Feedback (Hypothetical):**

**Team A (Startup):**
"We want fast feedback. Disable Pyright (too slow), keep Pylint + Mypy."

**Team B (Enterprise):**
"Add security gate (Bandit), coverage gate (>80%), and formatting gate (Black)."

**Team C (Research):**
"Prototyping phase - disable all gates except Mypy (type safety only)."

**Design Implication:**
- Gates must be independently toggleable
- Custom gates must be easy to add
- Order of execution should be configurable

---

## Proposed Solution

### quality.yaml Schema

```yaml
# Quality Gates Configuration
# Schema Version: 1.0
# Documentation: docs/reference/quality.yaml

version: "1.0"

# Execution strategy
execution:
  mode: fail-fast  # fail-fast | continue-on-error
  parallel: false  # Run gates in parallel (future feature)

# Quality gates definition
gates:
  # Gate 1: Pylint (Python linting)
  pylint:
    name: "Linting"
    description: "Python code quality checks (whitespace, imports, line length)"
    command: ["python", "-m", "pylint"]
    args:
      - "--enable=all"
      - "--max-line-length=100"
      - "--output-format=text"
    timeout: 60
    enabled: true
    output_format: text
    score_pattern: 'Your code has been rated at ([\d.]+)/10'
    issue_pattern: '^(.+?):(\d+):(\d+): \[([A-Z]\d+)\(([^)]+)\)\] (.+)$'
    file_types: [".py"]
    
  # Gate 2: Mypy (Type checking)
  mypy:
    name: "Type Checking"
    description: "Static type checking with mypy"
    command: ["python", "-m", "mypy"]
    args:
      - "--strict"
      - "--no-error-summary"
    timeout: 60
    enabled: true
    output_format: regex
    issue_pattern: '^(.+?):(\d+): (error|warning): (.+)$'
    file_types: [".py"]
    
  # Gate 3: Pyright (Pylance parity)
  pyright:
    name: "Pyright"
    description: "TypeScript-based type checker (Pylance compatibility)"
    command: ["pyright"]  # Note: not `python -m pyright`
    args:
      - "--outputjson"
    timeout: 120
    enabled: true
    output_format: json
    json_path: "generalDiagnostics"
    file_types: [".py"]

  # Example custom gate (commented out by default)
  # coverage:
  #   name: "Coverage"
  #   description: "Code coverage threshold check"
  #   command: ["pytest"]
  #   args:
  #     - "--cov=mcp_server"
  #     - "--cov-report=term-missing"
  #     - "--cov-fail-under=80"
  #   timeout: 300
  #   enabled: false
  #   output_format: text
  #   file_types: [".py"]
```

### Pydantic Models

```python
# mcp_server/config/quality_config.py
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    """Quality gate execution strategy."""
    FAIL_FAST = "fail-fast"
    CONTINUE_ON_ERROR = "continue-on-error"


class OutputFormat(str, Enum):
    """Quality gate output parsing format."""
    TEXT = "text"
    REGEX = "regex"
    JSON = "json"


class QualityGate(BaseModel):
    """Definition of a single quality gate."""
    
    name: str = Field(..., description="Display name for the gate")
    description: str = Field(..., description="What this gate checks")
    command: list[str] = Field(..., description="Command to execute (e.g., ['python', '-m', 'pylint'])")
    args: list[str] = Field(default_factory=list, description="Command-line arguments")
    timeout: int = Field(default=60, ge=1, le=3600, description="Timeout in seconds")
    enabled: bool = Field(default=True, description="Whether gate is active")
    output_format: OutputFormat = Field(default=OutputFormat.TEXT, description="Output parsing strategy")
    score_pattern: str | None = Field(default=None, description="Regex to extract numeric score")
    issue_pattern: str | None = Field(default=None, description="Regex to extract issues (for text/regex formats)")
    json_path: str | None = Field(default=None, description="JSON path to diagnostics (for json format)")
    file_types: list[str] = Field(default_factory=lambda: [".py"], description="File extensions this gate applies to")
    
    model_config = {"frozen": True}


class ExecutionConfig(BaseModel):
    """Quality gate execution configuration."""
    
    mode: ExecutionMode = Field(default=ExecutionMode.FAIL_FAST, description="Execution strategy")
    parallel: bool = Field(default=False, description="Run gates in parallel (not yet implemented)")
    
    model_config = {"frozen": True}


class QualityConfig(BaseModel):
    """Root quality gates configuration."""
    
    version: str = Field(..., pattern=r"^\d+\.\d+$", description="Config schema version")
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution settings")
    gates: dict[str, QualityGate] = Field(..., description="Named quality gates")
    
    model_config = {"frozen": True}
```

### Migration Impact

**Lines to Remove:**
- `_run_pylint()` method: ~40 lines → Replace with generic `_run_gate()`
- `_run_mypy()` method: ~35 lines → Replace with generic `_run_gate()`
- `_run_pyright()` method: ~30 lines → Replace with generic `_run_gate()`
- Hardcoded commands/timeouts: ~15 lines

**Total Removal:** ~120 lines of hardcoded configuration

**Lines to Add:**
- `QualityConfig` loading: ~20 lines
- Generic `_run_gate()` method: ~50 lines
- Output parsing dispatch: ~30 lines

**Net Change:** +100 lines (more flexible, less duplication)

---

## Next Steps

### Planning Phase Deliverables

1. **Goal Breakdown:**
   - TDD goals for Pydantic models
   - TDD goals for QAManager refactoring
   - TDD goals for custom gate support

2. **Implementation Strategy:**
   - Incremental migration (one gate at a time)
   - Backward compatibility (fail if config missing?)
   - Test coverage requirements

3. **Risk Assessment:**
   - Breaking changes (yes: QAManager constructor)
   - Performance impact (config loading overhead)
   - Edge cases (timeout handling, JSON parsing failures)

### Open Questions

1. **Backward Compatibility:** Should system fail gracefully if quality.yaml is missing, or require it?
   - **Recommendation:** Require config (fail-fast on missing)
   
2. **Custom Gate Validation:** Should we validate that custom gate commands exist before running?
   - **Recommendation:** Yes, run health check on startup
   
3. **Output Parsing:** Should we support custom parsers (Python functions)?
   - **Recommendation:** No, keep to regex/JSON for simplicity
   
4. **Gate Ordering:** Should gates run in YAML definition order?
   - **Recommendation:** Yes, preserve order for predictability

---

## Related Documentation

- **Issue #50:** workflows.yaml (config pattern established)
- **Issue #51:** labels.yaml (Pydantic validation pattern)
- **Issue #49:** Epic overview (MCP Platform Configurability)
- **Epic #18:** Enforcement tooling (requires this issue)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial research (Phase 1: Research complete) |

