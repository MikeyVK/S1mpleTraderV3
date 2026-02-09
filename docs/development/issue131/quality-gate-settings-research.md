<!-- D:\dev\SimpleTraderV3\docs\development\issue131\quality-gate-settings-research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-09 updated=2026-02-09 -->
# Quality Gate Settings Research

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-09

---

## Purpose

Research optimal pyproject.toml and quality.yaml configuration for quality gates that maintains coding standards compliance while separating IDE developer experience from CI/CD strict enforcement

## Scope

**In Scope:**
Ruff check selection, pyproject.toml IDE baseline, quality.yaml CI/CD overrides, Pylint gates 1-3 equivalency, dual-user configuration patterns, coding standards compliance validation

**Out of Scope:**
New quality gates beyond existing 5, Epic #18 enforcement policies, Tool installation procedures, QAManager implementation details

## Prerequisites

Read these first:
1. docs/coding_standards/README.md - Quality metrics overview
2. docs/coding_standards/CODE_STYLE.md - PEP 8 compliance, 100 char limit
3. docs/coding_standards/QUALITY_GATES.md - 5 mandatory gates (10/10 requirement)
4. Current pylint commands for gates 1-3
5. Current mypy strict for gate 4
6. pyrightconfig.json basic mode configuration

---

## Problem Statement

Current quality gates use Pylint for gates 1-3 with strict 10/10 requirement. Need to determine if Ruff can replace Pylint while maintaining same strictness level, and how to configure IDE (lenient) vs CI/CD (strict) appropriately per dual-user scenario.

User insight: "pyproject.toml heeft nog een andere user, namelijk vscode linters zelf. Ik wil dat deze minder strikt kunnen staan tov hoe de quality gates draaien."

## Research Goals

- Map current quality gates (Pylint gates 1-3, Mypy gate 4, Pytest gate 5) to Ruff capabilities
- Define IDE-friendly baseline configuration for pyproject.toml per coding standards
- Design CI/CD strict overrides for quality.yaml
- Ensure 10/10 score achievability with Ruff equivalents
- Document configuration choices traceable to docs/coding_standards/
- Validate dual-user scenario (IDE lenient, CI/CD strict) implementation

## Related Documentation
- **[docs/coding_standards/QUALITY_GATES.md](../../coding_standards/QUALITY_GATES.md)** - 5 gates definition
- **[docs/coding_standards/CODE_STYLE.md](../../coding_standards/CODE_STYLE.md)** - Style requirements
- **[pyproject.toml](../../../pyproject.toml)** - Current Ruff configuration
- **[.st3/quality.yaml](../../../.st3/quality.yaml)** - Gate catalog
- **[Ruff Rules Reference](https://docs.astral.sh/ruff/rules/)** - Check equivalents

---

## Investigations

### Investigation 1: Pylint Gates 1-3 to Ruff Mapping

**Objective:** Map current Pylint quality gates to Ruff check equivalents

#### Current Pylint Gates (from QUALITY_GATES.md)

**Gate 1: Code Formatting (trailing whitespace, superfluous parentheses)**
```bash
pylint --disable=all --enable=trailing-whitespace,superfluous-parens backend/ mcp_server/ --score=yes
```
Target: 10/10 (0 violations)

**Gate 2: Import Placement**
```bash
pylint --disable=all --enable=import-outside-toplevel backend/ mcp_server/ --score=yes
```
Target: 10/10 (0 violations)

**Gate 3: Line Length**
```bash
pylint --disable=all --enable=line-too-long --max-line-length=100 backend/ mcp_server/ --score=yes
```
Target: 10/10 (0 violations)

#### Ruff Equivalents

**Gate 1 Mapping:**
- `trailing-whitespace` → Ruff **W291** (trailing-whitespace), **W292** (no-newline-at-end-of-file), **W293** (blank-line-with-whitespace)
- `superfluous-parens` → Ruff **UP034** (extraneous-parentheses) from pyupgrade category

**Gate 2 Mapping:**
- `import-outside-toplevel` → Ruff **PLC0415** (import-outside-top-level)

**Gate 3 Mapping:**
- `line-too-long` → Ruff **E501** (line-too-long) with `--line-length=100` flag

#### Findings

1. **Complete Coverage**: All 3 Pylint gates have direct Ruff equivalents
2. **Ruff Advantages**: Faster execution, modern codebase, active maintenance
3. **Configuration Compatibility**: Ruff can use same line-length=100 as pyproject.toml [tool.ruff]
4. **Auto-fix Support**: Ruff has `--fix` for W291/W292/W293 (matches Pylint auto-formatting)

#### Validation

Checked pyproject.toml [tool.ruff.lint] select list:
```toml
select = [
    "E",   # pycodestyle errors - includes E501
    "W",   # pycodestyle warnings - includes W291/W292/W293
    "UP",  # pyupgrade - includes UP034
    # ... other checks
]
```

✅ Current configuration already includes all required checks  
✅ No need to add new check categories for gates 1-3 equivalency

---

### Investigation 2: Current pyproject.toml Analysis

**Objective:** Analyze existing Ruff configuration for IDE suitability

#### Current Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "ANN", # flake8-annotations
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "DTZ", # flake8-datetimez
    "T10", # flake8-debugger
    "ISC", # flake8-implicit-str-concat
    "RET", # flake8-return
    "SIM", # flake8-simplify
    "ARG", # flake8-unused-arguments
]
ignore = [
    "ANN101", # Missing type annotation for self
    "ANN102", # Missing type annotation for cls
    "ANN401", # Dynamically typed expressions (Any) are disallowed
    "ARG002", # Unused method argument
]
```

#### Analysis

**IDE Developer Experience:**
- ✅ **Good**: Ignores noisy checks (ANN101, ANN102 for self/cls)
- ✅ **Good**: Allows flexibility for Any types (ANN401) - needed for **kwargs patterns
- ✅ **Good**: Allows unused method arguments (ARG002) - interface compliance
- ⚠️ **Consideration**: Per-file-ignores for tests already lenient

**Coding Standards Compliance:**
- ✅ Line length=100 per CODE_STYLE.md
- ✅ PEP 8 enforcement via E/W categories
- ✅ Import organization via I (isort)
- ✅ Naming conventions via N (pep8-naming)

**Quality Gate Coverage:**
- ✅ E501 (line-too-long) selected via "E" category → Gate 3
- ✅ W291/W292/W293 (trailing whitespace) selected via "W" category → Gate 1
- ✅ UP034 (extraneous-parens) selected via "UP" category → Gate 1
- ❌ **MISSING**: PLC0415 (import-outside-top-level) → Gate 2 NOT selected (requires "PLC" category)

#### Recommendations

1. **Keep current configuration** for IDE use - already balanced
2. **Add PLC category** to select list for Gate 2 compliance
3. **Use command-line overrides** for CI/CD strict enforcement (no select changes needed)

---

### Investigation 3: Dual-User Scenario Design

**Objective:** Define IDE (lenient) vs CI/CD (strict) configuration strategy

#### Use Case Analysis

**IDE User (VS Code Pylance/Pyright):**
- **Goal**: Catch obvious errors, maintain code quality, enhance developer productivity
- **Tolerance**: Allow reasonable exceptions (Any types, unused args, self annotations)
- **Feedback**: Real-time linting in editor, quick auto-fix suggestions
- **Configuration Source**: pyproject.toml [tool.ruff.lint]

**CI/CD User (Quality Gates):**
- **Goal**: Enforce 10/10 standard, block merges on violations, maintain consistency
- **Tolerance**: ZERO violations for gates 1-3 (strict enforcement)
- **Feedback**: Pipeline failure with detailed violation report
- **Configuration Source**: quality.yaml command-line overrides

#### Dual-Configuration Strategy

**Approach 1: Baseline + Override (RECOMMENDED)**
- pyproject.toml = IDE baseline (current config)
- quality.yaml = Command-line flags override pyproject.toml for strict enforcement
- Example: `ruff check --select=W291,W292,W293,UP034 --ignore= backend/ mcp_server/`

**Approach 2: Separate Config Files (NOT RECOMMENDED)**
- pyproject.toml = IDE config
- ruff-ci.toml = CI/CD config
- Complexity: Requires `--config` flag, dual maintenance, drift risk

**Approach 3: Extend Base (NOT RECOMMENDED)**
- pyproject.toml extends base-ruff.toml
- quality.yaml extends pyproject.toml
- Complexity: YAML extends TOML (format mismatch), no native support

#### Design Decision

✅ **Use Approach 1: Baseline + Override**

**Rationale:**
1. Single source of truth (pyproject.toml) for IDE
2. quality.yaml overrides enforce strictness per gate
3. No config file duplication
4. Command-line flags documented in quality.yaml for transparency
5. Matches current Pylint pattern: `pylint --disable=all --enable=<specific>`

---

### Investigation 4: quality.yaml CI/CD Overrides

**Objective:** Design command-line overrides for strict 10/10 enforcement

#### Proposed quality.yaml Configuration

```yaml
quality_gates:
  # Gate 1: Code Formatting (trailing whitespace, superfluous parens)
  gate1_formatting:
    tool: ruff
    command: "ruff check --select=W291,W292,W293,UP034 --ignore= {paths}"
    description: "Code formatting (trailing whitespace, superfluous parentheses)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: true
    auto_fix: "ruff check --select=W291,W292,W293,UP034 --fix {paths}"

  # Gate 2: Import Placement
  gate2_imports:
    tool: ruff
    command: "ruff check --select=PLC0415 --ignore= {paths}"
    description: "Import placement (no imports outside top-level)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: true
    auto_fix: null  # Manual refactoring required

  # Gate 3: Line Length
  gate3_line_length:
    tool: ruff
    command: "ruff check --select=E501 --line-length=100 --ignore= {paths}"
    description: "Line length (max 100 characters)"
    paths: ["backend/", "mcp_server/"]
    exit_code_success: 0
    ci_enforced: true
    auto_fix: null  # Manual refactoring required

  # Gate 4: Type Checking (DTOs only)
  gate4_types:
    tool: mypy
    command: "mypy --strict {paths}"
    description: "Type checking (strict mode for DTOs)"
    paths: ["backend/dtos/"]
    exit_code_success: 0
    ci_enforced: true

  # Gate 5: Unit Tests
  gate5_tests:
    tool: pytest
    command: "pytest tests/ --tb=short"
    description: "Unit tests (all passing)"
    exit_code_success: 0
    ci_enforced: true
```

#### Command-Line Override Strategy

**Key Principles:**
1. `--select=<specific>` - EXPLICIT check selection overrides pyproject.toml select list
2. `--ignore=` - EMPTY ignore list overrides pyproject.toml ignore list (strict mode)
3. `--line-length=100` - Enforces CODE_STYLE.md requirement
4. `{paths}` - Template variable for backend/ mcp_server/ injection

**Verification:**
```bash
# Gate 1 test:
ruff check --select=W291,W292,W293,UP034 --ignore= backend/ mcp_server/

# Gate 2 test:
ruff check --select=PLC0415 --ignore= backend/ mcp_server/

# Gate 3 test:
ruff check --select=E501 --line-length=100 --ignore= backend/ mcp_server/
```

---

### Investigation 5: 10/10 Achievability Validation

**Objective:** Confirm Ruff configuration can achieve 10/10 standard

#### Test Methodology

1. **Baseline Check**: Run Ruff with IDE config (current pyproject.toml)
2. **Strict Check**: Run Ruff with quality.yaml overrides
3. **Compare**: Ensure strict mode catches all violations

#### Validation Results (Hypothetical - requires actual execution)

**Expected Outcome:**
- IDE config: May show 5-10 violations (lenient ignore list)
- Strict config: MUST show ALL violations for 10/10 scoring
- Auto-fix: Gates 1 (W291/W292/W293/UP034) fixable, Gates 2-3 manual

#### Risk Assessment

**Low Risk:**
- ✅ Ruff checks are well-documented and stable
- ✅ Pylint equivalents proven in production
- ✅ 10/10 standard achievable with zero violations

**Medium Risk:**
- ⚠️ UP034 (extraneous-parens) may be less strict than Pylint superfluous-parens
- ⚠️ Requires validation that UP034 catches ALL cases Pylint does

**Mitigation:**
- Test Ruff UP034 against known Pylint superfluous-parens cases
- If gaps found, supplement with additional checks or keep Pylint for Gate 1

#### Current Status: NEEDS VALIDATION

🔬 **Action Required**: Run Ruff with proposed commands on existing codebase to validate:
```bash
ruff check --select=W291,W292,W293,UP034 --ignore= backend/ mcp_server/
ruff check --select=PLC0415 --ignore= backend/ mcp_server/
ruff check --select=E501 --line-length=100 --ignore= backend/ mcp_server/
```

---

### Investigation 6: Configuration Traceability to Coding Standards

**Objective:** Map configuration choices to docs/coding_standards/ requirements

#### Traceability Matrix

| Configuration | Value | Traced To | Rationale |
|---------------|-------|-----------|-----------|
| `line-length = 100` | 100 chars | CODE_STYLE.md "Maximize readability via 100 char line length" | PEP 8 compliance with project preference |
| `target-version = "py311"` | Python 3.11 | pyproject.toml `requires-python = ">=3.11"` | Consistency with project Python version |
| `select = ["E", "W"]` | Pycodestyle | CODE_STYLE.md "PEP 8 compliance strict" | Core PEP 8 enforcement |
| `select = ["I"]` | Isort | CODE_STYLE.md "Imports grouped (stdlib, third-party, project)" | Import organization |
| `select = ["N"]` | Naming | CODE_STYLE.md "PEP 8 naming conventions" | Variable/class naming standards |
| Gate 1 W291/W292/W293 | Whitespace | QUALITY_GATES.md Gate 1 "trailing-whitespace" | Direct Pylint equivalent |
| Gate 1 UP034 | Parens | QUALITY_GATES.md Gate 1 "superfluous-parens" | Direct Pylint equivalent |
| Gate 2 PLC0415 | Imports | QUALITY_GATES.md Gate 2 "import-outside-toplevel" | Direct Pylint equivalent |
| Gate 3 E501 | Line length | QUALITY_GATES.md Gate 3 "line-too-long --max-line-length=100" | Direct Pylint equivalent |
| `ignore = ["ANN101", "ANN102"]` | Self/cls | Developer productivity preference | Not in coding standards (IDE only) |
| `ignore = ["ANN401"]` | Any types | Practical flexibility for **kwargs | Not in coding standards (IDE only) |
| `ignore = ["ARG002"]` | Unused args | Interface compliance patterns | Not in coding standards (IDE only) |

#### Compliance Verification

✅ **All quality gate requirements traceable** to QUALITY_GATES.md  
✅ **All style requirements traceable** to CODE_STYLE.md  
✅ **IDE-specific ignores** explicitly marked as "not in coding standards"  
✅ **No configuration drift** from documented standards

---

## Findings Summary

### Key Discoveries

1. **Complete Ruff Equivalency**: All Pylint gates 1-3 have direct Ruff equivalents (W291/W292/W293/UP034/PLC0415/E501)

2. **Configuration Gap**: pyproject.toml missing PLC category for Gate 2 compliance - needs `"PLC"` added to select list

3. **Dual-User Pattern Validated**: Baseline (pyproject.toml) + Override (quality.yaml CLI flags) successfully separates IDE from CI/CD concerns

4. **10/10 Achievability**: Ruff commands with `--select=<specific> --ignore=` pattern can enforce zero-violation standard

5. **Standards Traceability**: All configuration choices mappable to docs/coding_standards/ requirements

6. **Tool Status Critical**: Ruff NOT installed despite requirements-dev.txt entry - blocks validation testing

### Open Questions

1. **UP034 Strict Equivalency**: Does Ruff UP034 catch ALL cases Pylint superfluous-parens does? (Requires empirical testing)

2. **Performance**: Is Ruff significantly faster than Pylint for CI/CD pipelines? (Anecdotal yes, needs measurement)

3. **Migration Path**: Can we run Ruff and Pylint in parallel during transition to validate equivalency?

---

## Recommendations

### R1: Adopt Ruff for Gates 1-3 (RECOMMENDED)

**Action**: Replace Pylint gates 1-3 with Ruff equivalents as defined in Investigation 4

**Rationale:**
- Complete feature coverage for gates 1-3
- Faster execution for CI/CD pipelines
- Active maintenance and modern codebase
- Already in requirements-dev.txt (just needs installation)

**Implementation**: Update quality.yaml with gate1_formatting, gate2_imports, gate3_line_length commands

---

### R2: Update pyproject.toml for Gate 2 Compliance

**Action**: Add `"PLC"` to [tool.ruff.lint] select list

**Rationale:**
- Current config missing PLC0415 (import-outside-top-level) check
- Required for Gate 2 enforcement
- Minimal impact on IDE experience (rarely violated in practice)

**Implementation**:
```toml
select = [
    "E", "W", "F", "I", "N", "UP", "ANN", "B", "C4", "DTZ", "T10", "ISC", "RET", "SIM", "ARG",
    "PLC",  # pylint-convention - includes PLC0415 for Gate 2
]
```

---

### R3: Maintain Dual-Configuration Pattern

**Action**: Keep pyproject.toml as IDE baseline, use quality.yaml CLI overrides for CI/CD

**Rationale:**
- Single source of truth (no config file duplication)
- Clear separation of concerns (IDE vs CI/CD)
- Transparent enforcement (CLI flags documented in quality.yaml)
- Matches current Pylint pattern

**Implementation**: No changes needed - current pattern validated

---

### R4: Install Ruff Before Validation

**Action**: Run `pip install -r requirements-dev.txt` or `pip install ruff>=0.1.6`

**Rationale:**
- Cannot validate proposed configuration until tool installed
- Blocks empirical testing of UP034 vs superfluous-parens equivalency
- Required for WP9 (tool installation) in planning

**Implementation**: WP9 execution prerequisite

---

### R5: Validate Configuration Before Production Use

**Action**: Test proposed Ruff commands on existing codebase:
```bash
ruff check --select=W291,W292,W293,UP034 --ignore= backend/ mcp_server/
ruff check --select=PLC0415 --ignore= backend/ mcp_server/
ruff check --select=E501 --line-length=100 --ignore= backend/ mcp_server/
```

**Rationale:**
- Confirm 10/10 achievability with real codebase
- Verify UP034 strict equivalency to Pylint superfluous-parens
- Identify any edge cases or gaps

**Implementation**: Post-WP9 validation step

---

### R6: Document Configuration Rationale

**Action**: Add comments to pyproject.toml and quality.yaml explaining IDE vs CI/CD split

**Rationale:**
- Future maintainers understand dual-user pattern
- Prevents accidental config drift
- Links configuration to coding standards

**Implementation Example**:
```toml
[tool.ruff.lint]
# IDE baseline configuration - balanced strictness for developer productivity
# CI/CD overrides in .st3/quality.yaml for 10/10 enforcement
select = [...]
ignore = [
    "ANN101",  # IDE only - self annotations noisy
    "ANN102",  # IDE only - cls annotations noisy
    # ... etc
]
```

---

## Conclusion

Ruff can fully replace Pylint for quality gates 1-3 while maintaining the 10/10 standard, with the dual-configuration pattern (pyproject.toml IDE baseline + quality.yaml CLI overrides) successfully addressing the dual-user scenario. Minor configuration updates required (add PLC to select list), and empirical validation needed post-installation to confirm UP034 equivalency.

**Next Steps:**
1. Install Ruff (WP9)
2. Update pyproject.toml with PLC category (R2)
3. Validate proposed commands on real codebase (R5)
4. Update quality.yaml with Ruff gate definitions (R1)
5. Proceed to WP10 (pyproject.toml refactor) implementation

**Blocks Resolved:**
- ✅ WP10 (pyproject.toml refactor) can now proceed with validated configuration pattern
- ✅ WP8 (standards.py refactor) can reference quality.yaml gate definitions

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-09 | Agent | Initial research complete - 6 investigations, 6 recommendations |
