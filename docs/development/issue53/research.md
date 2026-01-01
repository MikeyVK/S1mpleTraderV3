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

## Recommendations for Planning Phase

Based on research findings, the planning phase should address:

1. **Configuration Schema Design**
   - YAML structure for gates, execution modes, output formats
   - Pydantic models for validation
   - Default values and sensible fallbacks

2. **Migration Strategy**
   - Incremental approach (one gate at a time)
   - Backward compatibility decision
   - Testing strategy for each gate

3. **Extensibility Goals**
   - Custom gate support (coverage, security, formatting)
   - Output format support (text, regex, JSON)
   - File type filtering per gate

4. **Open Questions to Resolve**
   - **Backward Compatibility:** Fail gracefully if quality.yaml missing, or require it?
   - **Custom Gate Validation:** Validate command existence before running?
   - **Output Parsing:** Support custom parsers (Python functions) or limit to regex/JSON?
   - **Gate Ordering:** Run in YAML definition order or allow priority field?

5. **Risk Assessment**
   - Breaking changes (QAManager constructor signature)
   - Performance impact (config loading overhead)
   - Edge cases (timeout handling, JSON parsing failures)
   - CI/CD impact (different timeout requirements)

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

