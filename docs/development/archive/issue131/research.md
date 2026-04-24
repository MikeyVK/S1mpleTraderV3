<!-- docs/development/issue131/research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-09 updated=2026-02-09 -->
# Quality Gates Architecture Analysis

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-09  
**Issue:** #131

---

## Purpose

Research current quality gates architecture to identify disconnect between quality.yaml configuration and QAManager implementation, and recommend path toward config-driven execution.

## Scope

**In Scope:**
- quality.yaml structure analysis
- QAManager implementation review
- pyproject.toml vs quality.yaml relationship
- Dual-user scenario (IDE vs CI/CD)
- Generic executor architecture patterns
- active_gates configuration design

**Out of Scope:**
- New gate tool implementation
- Epic #18 enforcement policies
- pyproject.toml changes
- Tool installation procedures
- standards.py refactoring (separate issue)

## Prerequisites

Read these first:
1. [quality.yaml](../../../.st3/quality.yaml) - Gate catalog with 7 definitions (Epic #49 deliverable)
2. [quality_config.py](../../../mcp_server/config/quality_config.py) - QualityConfig Pydantic model with validation
3. [qa_manager.py](../../../mcp_server/managers/qa_manager.py) - QAManager with run_quality_gates() method
4. [quality_tools.py](../../../mcp_server/tools/quality_tools.py) - RunQualityGatesTool MCP tool interface
5. [pyproject.toml](../../../pyproject.toml) - Tool-specific configurations

---

## Problem Statement

quality.yaml defines 7 available gates with execution strategies, but QAManager hardcodes 3 specific gates (pylint, mypy, pyright) and duplicates parsing logic already defined in quality.yaml. This creates architectural disconnect between configuration and implementation, where 57% of the defined gates (ruff, black, pytest, bandit) are never used despite being fully configured.

## Research Goals

- Analyze current QAManager implementation and identify hardcoded gate selection
- Document quality.yaml catalog capabilities vs actual usage (7 defined vs 3 used)
- Identify code duplication between QAManager parsing and quality.yaml parsing strategies
- Document dual-user scenario: pyproject.toml serves IDE and CI/CD with different strictness levels
- Design active_gates configuration approach for dynamic gate selection
- Evaluate generic gate executor pattern to replace tool-specific methods
- Recommend migration path from hardcoded to config-driven architecture

## Related Documentation
- **[.st3/quality.yaml - Gate catalog with 7 definitions][related-1]**
- **[mcp_server/config/quality_config.py - Config models][related-2]**
- **[mcp_server/managers/qa_manager.py - Current implementation][related-3]**
- **[mcp_server/tools/quality_tools.py - MCP tool wrapper][related-4]**
- **[pyproject.toml - Tool behavior configuration][related-5]**
- **[Issue #49 - Epic: MCP Platform Configurability][related-6]**
- **[Issue #18 - Epic: TDD & Coverage Enforcement][related-7]**

<!-- Link definitions -->

[related-1]: .st3/quality.yaml - Gate catalog with 7 definitions
[related-2]: mcp_server/config/quality_config.py - Config models
[related-3]: mcp_server/managers/qa_manager.py - Current implementation
[related-4]: mcp_server/tools/quality_tools.py - MCP tool wrapper
[related-5]: pyproject.toml - Tool behavior configuration

## Investigation 1: Current Architecture - The Three-Layer System

### Finding: Intentional Separation of Concerns

**Three layers exist with distinct purposes:**

| Layer | File | Responsibility | User |
|-------|------|----------------|------|
| **Tool Configuration** | pyproject.toml | Tool behavior settings (strictness, rules) | IDE + CLI tools |
| **Gate Catalog** | quality.yaml | Execution strategy (command, parsing, success) | QAManager |
| **Orchestration** | QAManager | Execute gates, aggregate results | MCP tools |

### Critical Insight: Dual-User Scenario

User provided key insight: **pyproject.toml serves TWO distinct users:**

1. **IDE/Editor (VS Code, PyCharm):**
   - Real-time linting during development
   - Can be lenient (developer productivity)
   - Immediate feedback in editor

2. **CI/CD Quality Gates:**
   - Strict enforcement before merge
   - Blocks pull requests on violations
   - **Can override** pyproject.toml with stricter settings via command-line flags

**This justifies having BOTH configurations:**
- pyproject.toml: Baseline tool behavior
- quality.yaml: Can override with stricter CI/CD flags

**Example override:**
```yaml
# quality.yaml overrides pyproject.toml for stricter CI/CD
pylint:
  execution:
    command: ["python", "-m", "pylint",
              "--enable=all",  # Stricter than pyproject.toml
              "--disable=duplicate-code,redefined-outer-name",
              "--max-line-length=100"]
```

---
[related-6]: Issue #49 - Epic: MCP Platform Configurability
[related-7]: Issue #18 - Epic: TDD & Coverage Enforcement

---

## Investigation 2: Configuration vs Implementation Disconnect

### Finding: quality.yaml Catalog Underutilized

**Configuration declares 7 gates:**
```yaml
gates:
  pylint: { ... }    # ✅ USED
  pyright: { ... }   # ✅ USED
  mypy: { ... }      # ✅ USED
  ruff: { ... }      # ❌ DEFINED but NEVER used
  black: { ... }     # ❌ DEFINED but NEVER used
  pytest: { ... }    # ❌ DEFINED but NEVER used
  bandit: { ... }    # ❌ DEFINED but NEVER used
```

**Implementation hardcodes 3:**
```python
# qa_manager.py lines 94-96
pylint_gate = self._require_gate(quality_config, "pylint")
mypy_gate = self._require_gate(quality_config, "mypy")
pyright_gate = self._require_gate(quality_config, "pyright")

# ← ruff, black, pytest, bandit are NEVER retrieved
```

**Statistics:**
- Gates defined: 7
- Gates used: 3
- Utilization: **43%**
- Wasted configuration: **57%**

### Architectural Problem

quality.yaml presents as **flexible catalog** but QAManager is **inflexible executor**:

```
┌───────────────────────────┐
│ quality.yaml              │  "I define 7 gates with full config"
│ - Suggests flexibility    │
│ - Complete specifications │
└───────────────────────────┘
           ↓
┌───────────────────────────┐
│ QAManager                 │  "I use exactly 3, always"
│ - Hardcoded selection     │
│ - Ignores 57% of catalog  │
└───────────────────────────┘
```

**Result:** Misleading configuration - adding `ruff` to quality.yaml does nothing.

---

## Investigation 3: Code Duplication - Parsing Logic

### Finding: Tool-Specific Methods Reimplement quality.yaml Parsing

**quality.yaml defines parsing strategies:**
```yaml
pylint:
  parsing:
    strategy: "text_regex"
    patterns:
      - name: "rating"
        regex: "Your code has been rated at ([\\d.]+)/10"
        group: 1
        required: true
```

**BUT qa_manager.py reimplements identical logic:**
```python
def _extract_pylint_score(self, output: str) -> str:
    """Extract score from pylint output."""
    # Pattern: "Your code has been rated at X.XX/10"
    pattern = r"Your code has been rated at ([\d.]+)/10"  # ← DUPLICATE!
    match = re.search(pattern, output)
    if match:
        return f"{match.group(1)}/10"
    return "10/10"
```

**Same pattern in three places:**

| Gate | quality.yaml parsing | QAManager method | Lines Duplicated |
|------|---------------------|------------------|------------------|
| Pylint | `text_regex` strategy | `_run_pylint()` + `_parse_pylint_output()` | ~40 lines |
| Mypy | `exit_code` strategy | `_run_mypy()` + `_parse_mypy_output()` | ~35 lines |
| Pyright | `json_field` strategy | `_run_pyright()` + `_parse_pyright_output()` | ~70 lines |

**Total code duplication:** ~145 lines reimplementing what quality.yaml already specifies.

### Why This Is Problematic

1. **Maintenance burden**: Change parsing → update 2 places
2. **Inconsistency risk**: quality.yaml and code can diverge
3. **Not extensible**: Adding `ruff` requires writing `_run_ruff()` + parsing
4. **Violates DRY**: quality.yaml is "source of truth" but not used as such

---

## Investigation 4: Tool-Specific Methods Analysis

### Finding: High Code Similarity Across Methods

**All three `_run_<tool>()` methods follow identical pattern:**

```python
def _run_<TOOL>(self, gate: QualityGate, files: list[str]) -> dict[str, Any]:
    result = {
        "gate_number": <HARDCODED>,  # ← Different per tool
        "name": gate.name,
        "passed": True,
        "score": "<DEFAULT>",
        "issues": []
    }
    
    try:
        cmd = self._resolve_command(gate.execution.command, files)  # ← Identical
        
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=gate.execution.timeout_seconds,  # ← From quality.yaml
            check=False
        )  # ← Identical subprocess call
        
        # Parse output - ONLY DIFFERENT PART
        output = proc.stdout + proc.stderr
        issues = self._parse_<TOOL>_output(output)  # ← Tool-specific
        
        result["issues"] = issues
        result["passed"] = <SOME_LOGIC>  # ← Varies slightly
        
    except subprocess.TimeoutExpired:  # ← Identical error handling
        result["passed"] = False
        result["issues"] = [{"message": "<TOOL> timed out"}]
    except FileNotFoundError:  # ← Identical error handling
        result["passed"] = False
        result["issues"] = [{"message": "<TOOL> not found"}]
    
    return result
```

**Code similarity:**
- Subprocess invocation: **100% identical**
- Error handling: **100% identical**
- Result structure: **95% identical**
- Only difference: Parsing strategy (10-15% of method)

**Opportunity:** Extract common pattern, use quality.yaml parsing config for the 10% that varies.

---

## Investigation 5: Type Checker Redundancy

### Finding: Mypy and Pyright Both Run (Redundant)

**Current behavior:**
```python
mypy_gate = self._require_gate(quality_config, "mypy")
pyright_gate = self._require_gate(quality_config, "pyright")

# Both type checkers run on same files
mypy_result = self._run_mypy(mypy_gate, mypy_files)
pyright_result = self._run_pyright(pyright_gate, python_files)
```

**Why this is problematic:**

| Tool | Purpose | Strictness | Speed |
|------|---------|------------|-------|
| Mypy | Type checking | Configurable | Moderate |
| Pyright | Type checking | High (default strict) | Fast |

**Overlap:**
- Both detect type errors
- Both validate annotations
- Pyright is typically **stricter** than Mypy
- Running both = **duplicate error reporting**

**Scope filtering inconsistency:**
```yaml
mypy:
  scope:
    include_globs: ["backend/**/*.py", "mcp_server/**/*.py"]
    exclude_globs: ["tests/**/*.py"]
    
pyright:
  # No scope - runs on ALL files including tests
```

**Result:** Test files get Pyright errors but not Mypy errors (confusing).

---

## Investigation 6: Missing Active Gates Configuration

### Finding: No Way to Configure Which Gates Run

**Problem:** quality.yaml has no `active_gates` field.

**Current workaround:** QAManager hardcoded selection:
```python
# Only way to change gates = modify code
pylint_gate = self._require_gate(quality_config, "pylint")
mypy_gate = self._require_gate(quality_config, "mypy")
pyright_gate = self._require_gate(quality_config, "pyright")
```

**What's missing:**
```yaml
# This field does NOT exist
active_gates: ["pylint", "ruff", "pyright"]

gates:
  pylint: { ... }
  ruff: { ... }
  # ...
```

**Impact:**
- Cannot enable `ruff` via configuration
- Cannot disable `mypy` without code change
- Cannot reorder gate execution
- Gate numbers hardcoded (pylint=1, mypy=2, pyright=3)

**User expectation vs reality:**

| User Action | Expected Behavior | Actual Behavior |
|-------------|-------------------|-----------------|
| Add `ruff` to quality.yaml | Ruff runs on next execution | Nothing happens |
| Remove `mypy` from quality.yaml | Mypy stops running | Error: "missing required gate" |
| Reorder gates in YAML | Execution order changes | Order unchanged (hardcoded) |

---

## Recommendations

### Recommendation 1: Add `active_gates` to quality.yaml

**Proposed schema change:**
```yaml
version: "1.0"

# NEW: Ordered list determines which gates run and in what order
active_gates: ["pylint", "ruff", "pyright"]

gates:
  pylint: { ... }    # Available
  ruff: { ... }      # Available (can be activated/deactivated)
  pyright: { ... }   # Available
  mypy: { ... }      # Available but not active (excluded from active_gates)
  # ...
```

**Benefits:**
- ✅ Enables/disables gates via configuration
- ✅ Order determines execution sequence
- ✅ Clear separation: catalog (gates) vs policy (active_gates)
- ✅ Backwards compatible (can default to current ["pylint", "mypy", "pyright"])

---

### Recommendation 2: Implement Generic Gate Executor

**Replace three tool-specific methods with one:**

```python
def _run_gate(
    self, 
    gate: QualityGate, 
    files: list[str], 
    gate_number: int
) -> dict[str, Any]:
    """Generic gate executor using quality.yaml parsing strategy."""
    
    result = {
        "gate_number": gate_number,  # Dynamic, not hardcoded
        "name": gate.name,
        "passed": True,
        "score": "N/A",
        "issues": []
    }
    
    try:
        cmd = self._resolve_command(gate.execution.command, files)
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=gate.execution.timeout_seconds,
            check=False
        )
        
        # USE quality.yaml parsing strategy (dispatch pattern)
        if gate.parsing.strategy == "text_regex":
            issues = self._parse_text_regex(proc, gate.parsing.patterns)
        elif gate.parsing.strategy == "json_field":
            issues = self._parse_json_field(proc, gate.parsing.fields)
        elif gate.parsing.strategy == "exit_code":
            issues = [] if proc.returncode == 0 else [{"message": "Failed"}]
        
        result["issues"] = issues
        result["passed"] = self._evaluate_success(gate.success, issues, proc)
        
    except subprocess.TimeoutExpired:
        result["passed"] = False
        result["issues"] = [{"message": f"{gate.name} timed out"}]
    except FileNotFoundError:
        result["passed"] = False
        result["issues"] = [{"message": f"{gate.name} not found"}]
    
    return result
```

**Benefits:**
- ✅ No code changes to add new gate
- ✅ Uses quality.yaml parsing strategies (DRY)
- ✅ ~145 lines of duplication removed
- ✅ Consistent error handling across all gates

---

### Recommendation 3: Refactored `run_quality_gates()`

**New implementation:**

```python
def run_quality_gates(self, files: list[str]) -> dict[str, Any]:
    """Run quality gates based on active_gates configuration."""
    results = {
        "overall_pass": True,
        "gates": [],
    }
    
    # ... file validation (unchanged) ...
    
    quality_config = QualityConfig.load()
    
    # Read active gates from config (instead of hardcoding)
    active_gate_ids = quality_config.active_gates  # ["pylint", "ruff", "pyright"]
    
    # Execute gates dynamically
    for i, gate_id in enumerate(active_gate_ids, start=1):
        gate = self._require_gate(quality_config, gate_id)
        
        # Apply scope filtering if defined
        filtered_files = gate.scope.filter_files(python_files) if gate.scope else python_files
        
        if not filtered_files:
            # Skip with pass
            results["gates"].append({
                "gate_number": i,
                "name": gate.name,
                "passed": True,
                "score": "Skipped (no matching files)",
                "issues": []
            })
            continue
        
        # Generic executor (replaces _run_pylint, _run_mypy, _run_pyright)
        result = self._run_gate(gate, filtered_files, gate_number=i)
        results["gates"].append(result)
        
        if not result["passed"]:
            results["overall_pass"] = False
    
    return results
```

**Changes:**
- ❌ Remove: `self._run_pylint()`
- ❌ Remove: `self._run_mypy()`
- ❌ Remove: `self._run_pyright()`
- ✅ Add: `self._run_gate()` (generic)
- ✅ Add: `self._parse_text_regex()`
- ✅ Add: `self._parse_json_field()`
- ✅ Add: `self._evaluate_success()`

---

### Recommendation 4: Configuration Migration Plan

**Step 1: Add `active_gates` with backward compatibility**
```yaml
version: "1.0"

# Default to current behavior
active_gates: ["pylint", "mypy", "pyright"]

gates:
  # ... existing definitions unchanged ...
```

**Step 2: Update QualityConfig model**
```python
class QualityConfig(BaseModel):
    version: str
    active_gates: list[str] = Field(
        default=["pylint", "mypy", "pyright"],  # Backward compatible
        description="Ordered list of gates to execute"
    )
    gates: dict[str, QualityGate]
    
    @model_validator(mode="after")
    def validate_active_gates_exist(self) -> "QualityConfig":
        """Ensure all active gates are defined in gates dict."""
        for gate_id in self.active_gates:
            if gate_id not in self.gates:
                raise ValueError(
                    f"Active gate '{gate_id}' not found in gates catalog. "
                    f"Available: {list(self.gates.keys())}"
                )
        return self
```

**Step 3: Refactor QAManager incrementally**
1. Add `_run_gate()` generic method
2. Update `run_quality_gates()` to read `active_gates`
3. Keep old methods temporarily (migration period)
4. Remove old methods after validation

**Step 4: Update quality.yaml**
```yaml
version: "1.0"

# Enable Ruff, remove Mypy redundancy
active_gates: ["pylint", "ruff", "pyright"]

gates:
  # ... all 7 gates remain defined ...
```

---

## Research Artifacts Produced

- ✅ Three-layer architecture documentation (pyproject.toml, quality.yaml, QAManager)
- ✅ Dual-user scenario analysis (IDE vs CI/CD)
- ✅ Configuration vs implementation gap analysis (57% catalog wasted)
- ✅ Code duplication quantification (~145 lines)
- ✅ Tool-specific method similarity analysis (90%+ identical)
- ✅ Type checker redundancy documentation (Mypy vs Pyright)
- ✅ active_gates configuration design
- ✅ Generic gate executor pattern design
- ✅ Migration plan with backward compatibility

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-09 | Agent | Complete research - 6 investigations, dual-user scenario, architecture recommendations, migration plan |