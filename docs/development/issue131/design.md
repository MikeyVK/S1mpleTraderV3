<!-- docs/development/issue131/design.md -->
<!-- template=design version=5827e841 created=2026-02-09T00:00:00Z updated= -->
# quality-gates-config-driven

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-09

---

## Purpose

Design config-driven quality gate execution architecture that eliminates hardcoded gates, reduces code duplication, and properly serves both IDE (developer-friendly) and CI/CD (strict 10/10 enforcement) users

## Scope

**In Scope:**
QAManager refactor, QualityConfig schema, quality.yaml updates, pyproject.toml updates, standards.py refactor, Ruff adoption

**Out of Scope:**
New quality gates beyond existing 5, Epic #18 enforcement policies, Quality gate scoring algorithm changes, Pytest/Mypy replacement

## Prerequisites

Read these first:
1. Research complete (research.md v1.0 - architecture analysis)
2. Research complete (quality-gate-settings-research.md v1.0 - configuration strategy)
3. Planning complete (planning.md v1.1 - 10 work packages)
4. Install Ruff (WP9 prerequisite)
---

## 1. Context & Requirements

### 1.1. Problem Statement

QAManager hardcodes 3 quality gates with ~145 lines parsing duplication and tool-specific methods, while quality.yaml defines 7 gates catalog (57% waste). Need config-driven executor that reads active_gates list, uses generic command execution, and separates IDE (pyproject.toml) from CI/CD (quality.yaml) configuration per dual-user scenario.

### 1.2. Requirements

**Functional:**
- [ ] Read active_gates list from quality.yaml to determine which gates to execute
- [ ] Execute quality gate commands from quality.yaml catalog with path/flag substitution
- [ ] Support Ruff for gates 1-3 (W291/W292/W293/UP034/PLC0415/E501) replacing Pylint
- [ ] Maintain Mypy strict for gate 4 (DTOs only)
- [ ] Maintain Pytest for gate 5
- [ ] Parse command output for 10/10 scoring standard
- [ ] Return standardized QualityGateResult DTOs with violations list
- [ ] Support auto-fix commands for fixable gates (Gate 1 whitespace)
- [ ] Refactor standards.py to read quality.yaml catalog instead of hardcoded JSON

**Non-Functional:**
- [ ] Eliminate ~145 lines parsing code duplication
- [ ] Generic executor replaces tool-specific methods (_run_pylint, _run_pyright, _run_ruff)
- [ ] Active gates configuration single source of truth in quality.yaml
- [ ] pyproject.toml serves IDE with lenient baseline (current select/ignore lists)
- [ ] quality.yaml serves CI/CD with strict CLI overrides (--select=<specific> --ignore=)
- [ ] Maintain backward compatibility with existing QAManager API (run_quality_gates method)
- [ ] Configuration choices traceable to docs/coding_standards/ (QUALITY_GATES.md, CODE_STYLE.md)
- [ ] Zero performance regression vs current Pylint gates (Ruff faster expected)

### 1.3. Constraints

['Maintain 10/10 scoring standard (zero violations)', 'Backward compatible QAManager API', 'Ruff NOT installed (WP9 blocks validation)', 'No changes to pyrightconfig.json (basic mode preserved)', 'Mypy strict only for DTOs (backend/dtos/)', 'All configuration traceable to docs/coding_standards/']
---

## 2. Design Options

### 2.1. Option A: Option 1: Refactor QAManager with Generic Executor



**Pros:**
- ✅ Eliminates duplication
- ✅ Config-driven
- ✅ Maintains API compatibility

**Cons:**
- ❌ Requires QualityConfig.active_gates schema change

### 2.2. Option B: Option 2: New ConfigDrivenQAManager Class



**Pros:**
- ✅ Clean slate
- ✅ No API compatibility concerns

**Cons:**
- ❌ Breaking change
- ❌ Migration burden
- ❌ Duplicate code during transition

### 2.3. Option C: Option 3: Keep Pylint for Gates 1-3



**Pros:**
- ✅ No tool migration risk
- ✅ Proven in production

**Cons:**
- ❌ Slower than Ruff
- ❌ Older codebase
- ❌ Missed modernization opportunity
---

## 3. Chosen Design

**Decision:** Adopt Option 1 (Refactor QAManager) + Replace Pylint with Ruff

**Rationale:** Minimizes codebase churn (refactor vs rewrite), eliminates duplication, modernizes tooling (Ruff faster/maintained), maintains API compatibility, and fully addresses dual-user scenario per research findings.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use Ruff for gates 1-3 replacing Pylint (complete equivalency confirmed) | Research validated W291/W292/W293/UP034/PLC0415/E501 direct mapping, faster execution, active maintenance |
| Add active_gates: list[str] to QualityConfig schema | Enables dynamic gate selection from quality.yaml without code changes |
| Implement generic _execute_gate(gate_config) method replacing tool-specific methods | Eliminates ~145 lines duplication, single responsibility, extensible for new gates |
| Update pyproject.toml with PLC category for Gate 2 compliance | Current config missing PLC0415 check required for import-outside-top-level enforcement |
| Document quality.yaml with Ruff command templates (W291/W292/W293/UP034/PLC0415/E501) | Clear CI/CD override strategy --select=<specific> --ignore= for strict enforcement |
| Refactor standards.py read_quality_gates to parse quality.yaml YAML instead of JSON | Eliminate hardcoded JSON, use quality.yaml as single source of truth |
| Maintain dual-configuration: pyproject.toml IDE baseline, quality.yaml CI/CD overrides | Validated pattern separates developer productivity (lenient) from CI/CD enforcement (strict 10/10) |

### 3.2. Component Architecture

#### 3.2.1. QualityConfig Schema (Pydantic)

**File:** `mcp_server/config/quality_config.py`

**Changes:**
```python
from pydantic import BaseModel, Field

class QualityGateConfig(BaseModel):
    """Configuration for a single quality gate."""
    name: str = Field(..., description="Gate identifier (e.g., 'gate1_formatting')")
    tool: str = Field(..., description="Tool name (ruff, mypy, pytest)")
    command: str = Field(..., description="Command template with {paths} placeholder")
    description: str = Field(..., description="Human-readable gate purpose")
    paths: list[str] = Field(default_factory=lambda: ["backend/", "mcp_server/"])
    exit_code_success: int = Field(default=0, description="Expected exit code for success")
    ci_enforced: bool = Field(default=True, description="Whether gate blocks CI/CD")
    auto_fix: str | None = Field(default=None, description="Auto-fix command template")

class QualityConfig(BaseModel):
    """Configuration for quality gate system."""
    active_gates: list[str] = Field(  # ⬅️ NEW FIELD
        default_factory=list,
        description="List of active gate names from quality_gates catalog"
    )
    quality_gates: dict[str, QualityGateConfig] = Field(
        default_factory=dict,
        description="Catalog of available quality gates"
    )
```

**Rationale:** `active_gates` list enables dynamic gate selection without code changes

---

#### 3.2.2. QAManager Refactored Methods

**File:** `mcp_server/managers/qa_manager.py`

**Removed:** `_run_pylint()`, `_run_pyright()`, `_run_ruff()` (~145 lines duplication)

**Added:** Generic executor

```python
def _execute_gate(self, gate_config: QualityGateConfig) -> QualityGateResult:
    """Execute a quality gate with generic command execution.
    
    Args:
        gate_config: Gate configuration from quality.yaml
        
    Returns:
        QualityGateResult with violations list and 10/10 score status
    """
    # Substitute {paths} placeholder
    command = gate_config.command.format(paths=" ".join(gate_config.paths))
    
    # Execute command
    result = subprocess.run(
        command.split(),
        capture_output=True,
        text=True,
        check=False
    )
    
    # Parse output based on tool (delegated to _parse_output)
    violations = self._parse_output(gate_config.tool, result.stdout, result.stderr)
    
    # Determine success
    success = (result.returncode == gate_config.exit_code_success) and (len(violations) == 0)
    
    return QualityGateResult(
        gate_name=gate_config.name,
        tool=gate_config.tool,
        success=success,
        violations=violations,
        score=10 if len(violations) == 0 else 0  # 10/10 or 0/10
    )

def _parse_output(self, tool: str, stdout: str, stderr: str) -> list[Violation]:
    """Parse tool output into standardized violations list.
    
    Supports: ruff, mypy, pytest
    """
    if tool == "ruff":
        return self._parse_ruff_output(stdout)
    elif tool == "mypy":
        return self._parse_mypy_output(stdout)
    elif tool == "pytest":
        return self._parse_pytest_output(stdout)
    else:
        raise ValueError(f"Unsupported tool: {tool}")

def run_quality_gates(self, files: list[str] | None = None) -> list[QualityGateResult]:
    """Execute active quality gates from quality.yaml.
    
    Backward compatible API - signature unchanged.
    """
    config = self._load_quality_config()  # Reads quality.yaml
    
    results = []
    for gate_name in config.active_gates:  # ⬅️ Use active_gates list
        gate_config = config.quality_gates.get(gate_name)
        if not gate_config:
            raise ValueError(f"Active gate '{gate_name}' not found in quality_gates catalog")
        
        result = self._execute_gate(gate_config)  # ⬅️ Generic executor
        results.append(result)
    
    return results
```

**Rationale:** Generic executor eliminates duplication, single responsibility, extensible

---

#### 3.2.3. quality.yaml Updated Schema

**File:** `.st3/quality.yaml`

**Changes:**

```yaml
# Active quality gates for CI/CD enforcement
active_gates:
  - gate1_formatting
  - gate2_imports
  - gate3_line_length
  - gate4_types
  - gate5_tests

# Quality gates catalog
quality_gates:
  # Gate 1: Code Formatting (Ruff replaces Pylint)
  gate1_formatting:
    tool: ruff
    command: "ruff check --select=W291,W292,W293,UP034 --ignore= {paths}"
    description: "Code formatting (trailing whitespace, superfluous parentheses)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: true
    auto_fix: "ruff check --select=W291,W292,W293,UP034 --fix {paths}"

  # Gate 2: Import Placement (Ruff replaces Pylint)
  gate2_imports:
    tool: ruff
    command: "ruff check --select=PLC0415 --ignore= {paths}"
    description: "Import placement (no imports outside top-level)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: true
    auto_fix: null

  # Gate 3: Line Length (Ruff replaces Pylint)
  gate3_line_length:
    tool: ruff
    command: "ruff check --select=E501 --line-length=100 --ignore= {paths}"
    description: "Line length (max 100 characters)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: true
    auto_fix: null

  # Gate 4: Type Checking (Mypy strict for DTOs only)
  gate4_types:
    tool: mypy
    command: "mypy --strict {paths}"
    description: "Type checking (strict mode for DTOs)"
    paths: ["backend/dtos/"]
    exit_code_success: 0
    ci_enforced: true

  # Gate 5: Unit Tests (Pytest)
  gate5_tests:
    tool: pytest
    command: "pytest tests/ --tb=short"
    description: "Unit tests (all passing)"
    exit_code_success: 0
    ci_enforced: true

  # INACTIVE GATES (catalog for future use)
  pyright_basic:
    tool: pyright
    command: "pyright {paths}"
    description: "Pyright basic mode (informational only)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: false

  bandit_security:
    tool: bandit
    command: "bandit -r {paths}"
    description: "Security vulnerability scanning"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: false
```

**Rationale:** 
- `active_gates` list defines which gates run (5 gates active, 2 inactive)
- Ruff commands use `--select=<specific> --ignore=` for strict CI/CD enforcement
- Command templates with `{paths}` placeholder for flexibility
- `auto_fix` field enables automated remediation for Gate 1

---

#### 3.2.4. pyproject.toml IDE Configuration

**File:** `pyproject.toml`

**Changes:**

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
# IDE baseline configuration - balanced strictness for developer productivity
# CI/CD overrides in .st3/quality.yaml for 10/10 enforcement
select = [
    "E",   # pycodestyle errors - includes E501 (line-too-long)
    "W",   # pycodestyle warnings - includes W291/W292/W293 (whitespace)
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade - includes UP034 (extraneous-parens)
    "ANN", # flake8-annotations
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "DTZ", # flake8-datetimez
    "T10", # flake8-debugger
    "ISC", # flake8-implicit-str-concat
    "RET", # flake8-return
    "SIM", # flake8-simplify
    "ARG", # flake8-unused-arguments
    "PLC", # pylint-convention - includes PLC0415 (import-outside-top-level) ⬅️ NEW
]
ignore = [
    "ANN101", # IDE only - self annotations noisy
    "ANN102", # IDE only - cls annotations noisy
    "ANN401", # IDE only - allow Any for **kwargs patterns
    "ARG002", # IDE only - allow unused method args for interface compliance
]
```

**Rationale:**
- Added `"PLC"` for Gate 2 compliance (PLC0415 import-outside-top-level)
- Comments clarify IDE vs CI/CD dual-user pattern
- Ignore list preserved for developer productivity

---

#### 3.2.5. standards.py Refactored

**File:** `mcp_server/resources/standards.py`

**Current (Hardcoded JSON):**
```python
def read_quality_gates() -> str:
    """Return quality gates configuration as JSON (HARDCODED)."""
    return json.dumps({
        "gates": [
            {"name": "pylint", "command": "pylint..."},
            # ... hardcoded
        ]
    })
```

**Refactored (YAML Parsing):**
```python
import yaml
from pathlib import Path

def read_quality_gates() -> str:
    """Return quality gates configuration from quality.yaml."""
    quality_yaml_path = Path(__file__).parent.parent.parent / ".st3" / "quality.yaml"
    
    if not quality_yaml_path.exists():
        raise FileNotFoundError(f"quality.yaml not found at {quality_yaml_path}")
    
    with quality_yaml_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Convert to JSON for MCP tool compatibility
    return json.dumps(config, indent=2)
```

**Rationale:** Eliminate hardcoded JSON, use quality.yaml as single source of truth

---

### 3.3. Data Flow

```
┌─────────────────┐
│ IDE User        │
│ (VS Code)       │
└────────┬────────┘
         │ Reads
         ▼
┌─────────────────────┐
│ pyproject.toml      │  ◄─── IDE baseline (lenient)
│ [tool.ruff.lint]    │       select = [E, W, UP, PLC, ...]
│ select/ignore lists │       ignore = [ANN101, ANN102, ANN401, ARG002]
└─────────────────────┘


┌─────────────────┐
│ CI/CD Pipeline  │
│ (GitHub Actions)│
└────────┬────────┘
         │ Calls
         ▼
┌─────────────────────┐
│ QAManager           │
│ run_quality_gates() │
└────────┬────────────┘
         │ Reads
         ▼
┌─────────────────────────────────────────────┐
│ quality.yaml                                │  ◄─── CI/CD strict (10/10)
│ active_gates: [gate1, gate2, gate3, ...]   │
│ quality_gates:                              │
│   gate1_formatting:                         │
│     command: "ruff --select=W291,... --ignore="  │  ◄─── Overrides pyproject.toml
│   gate2_imports:                            │
│     command: "ruff --select=PLC0415 --ignore="   │
└───────────────┬─────────────────────────────┘
                │ Template
                ▼
        ┌───────────────┐
        │ _execute_gate()│  ◄─── Generic executor
        └───────┬────────┘
                │ Delegates
                ▼
        ┌───────────────┐
        │ _parse_output()│  ◄─── Tool-specific parsing
        └───────┬────────┘
                │ Returns
                ▼
        ┌───────────────────────┐
        │ QualityGateResult DTO  │
        │ - gate_name            │
        │ - tool                 │
        │ - success (10/10?)     │
        │ - violations[]         │
        └────────────────────────┘
```

**Key Points:**
1. **Separation**: IDE reads pyproject.toml, CI/CD uses quality.yaml overrides
2. **Single Source**: quality.yaml defines all gates, active_gates list controls execution
3. **Generic Executor**: _execute_gate handles all tools uniformly
4. **Standardized Output**: QualityGateResult DTO for all gates

---

### 3.4. Implementation Sequence (TDD Cycles from Planning)

**Cycle 1: QualityConfig Schema** (WP1-WP2)
1. RED: Write tests for active_gates field in QualityConfig
2. GREEN: Add active_gates: list[str] field to Pydantic model
3. REFACTOR: Validate schema against quality.yaml structure

**Cycle 2: Generic Executor** (WP3-WP4)
1. RED: Write tests for _execute_gate with mock gate_config
2. GREEN: Implement _execute_gate with subprocess execution
3. REFACTOR: Extract _parse_output delegation

**Cycle 3: Ruff Integration** (WP5-WP6)
1. RED: Write tests for Ruff gate 1-3 commands
2. GREEN: Add gate1/gate2/gate3 to quality.yaml, implement _parse_ruff_output
3. REFACTOR: Validate 10/10 scoring with real codebase

**Cycle 4: Configuration Updates** (WP7-WP10)
1. WP8 (standards.py): Refactor read_quality_gates to parse YAML
2. WP9 (tool install): Install Ruff via pip
3. WP10 (pyproject.toml): Add PLC category, document dual-user pattern

**Cycle 5: Validation & Documentation** (Integration)
1. Run all gates with new configuration
2. Validate 10/10 achievability
3. Update QUALITY_GATES.md with Ruff commands

---


## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Does Ruff UP034 catch ALL cases Pylint superfluous-parens does? (Requires empirical validation post-WP9) |  |  |
| What is actual Ruff performance improvement vs Pylint in CI/CD? (Measure after implementation) |  |  |
| Should we run Ruff and Pylint in parallel during migration for safety? (Risk mitigation trade-off) |  |  |
## Related Documentation
- **[docs/development/issue131/research.md - Architecture analysis][related-1]**
- **[docs/development/issue131/quality-gate-settings-research.md - Configuration strategy][related-2]**
- **[docs/development/issue131/planning.md - Work breakdown][related-3]**
- **[docs/coding_standards/QUALITY_GATES.md - 5 gates definition][related-4]**
- **[docs/coding_standards/CODE_STYLE.md - Style requirements][related-5]**

<!-- Link definitions -->

[related-1]: docs/development/issue131/research.md - Architecture analysis
[related-2]: docs/development/issue131/quality-gate-settings-research.md - Configuration strategy
[related-3]: docs/development/issue131/planning.md - Work breakdown
[related-4]: docs/coding_standards/QUALITY_GATES.md - 5 gates definition
[related-5]: docs/coding_standards/CODE_STYLE.md - Style requirements

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |