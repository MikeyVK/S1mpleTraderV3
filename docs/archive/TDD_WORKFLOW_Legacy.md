# Test-Driven Development (TDD) Workflow

## Overview

S1mpleTrader V3 follows **strict TDD discipline** integrated with Git workflow. This is **NOT OPTIONAL** - all new features must follow the RED → GREEN → REFACTOR cycle with feature branches.

## Feature Branch Setup

Every new feature starts with a dedicated branch:

```powershell
# Create feature branch from main
git checkout -b feature/size-plan-dto
```

**Branch naming conventions:**
- `feature/*` - New DTOs, workers, adapters
- `fix/*` - Bug fixes
- `refactor/*` - Code quality improvements
- `docs/*` - Documentation only

## The TDD Cycle

### 1. RED Phase: Write Failing Tests First

Write comprehensive tests **BEFORE** any implementation.

```python
def test_new_feature():
    """Test that new feature works correctly."""
    result = my_new_function(input_data)
    assert result == expected_output  # FAILS - function not implemented
```

**Commit failing tests to document intent:**

```powershell
git add tests/unit/dtos/strategy/test_size_plan.py
git commit -m "test: add failing tests for SizePlan DTO

- Test creation with valid fields
- Test validation rules
- Test edge cases

Status: RED - tests fail (implementation pending)"
```

**Test Coverage Criteria:**

Write tests until you have **complete coverage** of behavior, not arbitrary quantity targets.
Focus on **meaningful tests** that validate actual requirements:

- ✅ **Creation tests** - Valid instantiation with required/optional fields
- ✅ **Validation tests** - Each validation rule (min/max, format, type constraints)
- ✅ **Immutability tests** - frozen=True enforcement (if applicable)
- ✅ **Edge cases** - Boundary values, None handling, special characters
- ✅ **Cross-field validation** - Field dependencies, XOR constraints (if applicable)

**Example:** A minimal DTO with 3 required fields might need only 8-10 tests.
A complex DTO with many optional fields and validation rules might need 20+ tests.

**Quality over quantity:** 14 meaningful tests > 30 redundant tests.

### 2. GREEN Phase: Minimal Implementation

Implement the **minimum code** needed to make tests pass.

```python
def my_new_function(data):
    """Implement minimal working solution."""
    return process(data)  # Test now PASSES
```

**Commit working implementation:**

```powershell
git add backend/dtos/strategy/size_plan.py
git commit -m "feat: implement SizePlan DTO

- Add quantity, risk_amount, position_value fields
- Add validation for positive values
- All tests passing (20/20)

Status: GREEN"
```

### 3. REFACTOR Phase: Improve Code Quality

Enhance code while keeping all tests green:

**REFACTOR Checklist (MANDATORY):**

1. **Run Pylance error check on ALL files** (VS Code Problems panel or `get_errors` tool)
   - ✅ Check **both implementation AND test files**
   - ✅ Fix all errors
   - ✅ Address warnings OR add explicit `# pylint: disable=<rule>` with comment explaining why
   - ❌ Never ignore warnings silently
   
   ```powershell
   # Check implementation files
   get_errors backend/dtos/strategy/size_plan.py
   
   # Check test files (ALSO MANDATORY!)
   get_errors tests/unit/dtos/strategy/test_size_plan.py
   ```

2. **Code quality improvements (implementation AND tests):**
   - Fix trailing whitespace
   - Remove unused imports
   - Replace unnecessary lambdas with method references
   - Add/improve type hints
   - Enhance docstrings
   - Split long lines (<100 chars)
   - Add `json_schema_extra` examples (see [CODE_STYLE.md](CODE_STYLE.md))

3. **Run quality gates** (see [QUALITY_GATES.md](QUALITY_GATES.md))
   ```powershell
   # Whitespace & formatting
   pylint --enable=trailing-whitespace,superfluous-parens
   
   # Import placement
   pylint --enable=import-outside-toplevel
   
   # Line length
   pylint --enable=line-too-long --max-line-length=100
   ```

4. **Verify tests still pass:**
   ```powershell
   pytest tests/unit/<module>/ -v --tb=line
   ```

**Commit REFACTOR improvements:**

```powershell
git add backend/dtos/strategy/size_plan.py tests/unit/dtos/strategy/test_size_plan.py
git commit -m "refactor: improve SizePlan DTO code quality

Implementation improvements:
- Add comprehensive docstrings
- Fix line length violations
- Add type hints for all fields
- Clean up whitespace
- Add json_schema_extra examples

Test improvements:
- Remove unused imports
- Replace unnecessary lambdas with method references
- Fix Pylance warnings (added explicit pylint disables with justification)

Quality gates: All 10/10
Pylance: 0 errors, 0 warnings (implementation + tests)
Status: GREEN (tests still 20/20)"
```

**Common Pylance issues and fixes:**

```python
# ❌ BAD: Unnecessary lambda in tests
bus.subscribe("EVENT", lambda p: received.append(p), scope)

# ✅ GOOD: Direct method reference
bus.subscribe("EVENT", received.append, scope)

# ❌ BAD: Unused import
from unittest.mock import Mock  # Not used anywhere

# ✅ GOOD: Remove unused imports
# (just delete the line)

# Catching broad exceptions for handler isolation
except Exception as e:  # pylint: disable=broad-exception-caught
    # Justification: We don't know what exceptions handlers throw

# Using f-strings in logging (modern Python convention)
logger.error(  # pylint: disable=logging-fstring-interpolation
    f"Error: {detail}",  # Modern Python, no performance issue on error path
    exc_info=e
)
```

### 4. ⚠️ MANDATORY: Status Updates (NEVER SKIP!)

**This step is frequently forgotten by AI agents. It MUST be done before merge.**

Run complete quality checklist (see [QUALITY_GATES.md](QUALITY_GATES.md)).

If all gates pass, **IMMEDIATELY** update status documents:

```powershell
# 1. Get current test count
$testCount = (pytest tests/ --collect-only -q 2>$null | Select-String "^\d+ tests").Matches.Value
Write-Host "Total tests: $testCount"

# 2. Update IMPLEMENTATION_STATUS.md
# - Update test counts in Summary table
# - Update module-specific tables
# - Add entry to "Recent Updates (YYYY-MM-DD)" section
# - Update "Last Updated" date at top

# 3. Update TODO.md (if applicable)
# - Mark completed items with [x] and **RESOLVED**
# - Add commit hash for traceability
# - Update Summary table percentages

# 4. Commit the updates
git add docs/TODO.md docs/implementation/IMPLEMENTATION_STATUS.md
git commit -m "docs: update status for <FeatureName> completion

- Test count: X → Y (+Z tests)
- Updated module tables
- Added to Recent Updates"
```

**WHY THIS MATTERS:**
- Status docs are the project's memory across AI sessions
- Without updates, completed work appears "not done" to future agents
- This prevents duplicate work and maintains accurate project state

### 5. Merge to Main

Once all quality gates pass, merge back to main:

```powershell
# Switch back to main
git checkout main

# Merge feature (squash or regular based on preference)
git merge feature/size-plan-dto

# Push to GitHub
git push origin main

# Delete feature branch
git branch -d feature/size-plan-dto
```

## Commit Message Conventions

Use **Conventional Commits** format with clear prefixes:

- `test:` - Tests only (Red phase)
- `feat:` - New feature implementation (Green phase)
- `refactor:` - Code quality improvements (Refactor phase)
- `docs:` - Documentation updates
- `fix:` - Bug fixes
- `chore:` - Build/tooling changes

**Message structure:**
```
<type>: <short summary>

<optional body with details>
- Bullet point 1
- Bullet point 2

<optional footer with status>
Status: RED|GREEN
Quality gates: 10/10
```

## Branching Strategy

- **`main`** - Always stable
  - All tests passing
  - All quality gates met (10/10)
  - No trailing whitespace
  - Imports at top-level only

- **`feature/*`** - Development branches
  - Commit early, commit often
  - RED → GREEN → REFACTOR commits
  - Only merge to main when ALL quality gates pass

## Anti-Patterns to Avoid

❌ **Direct commits to main** (use feature branches)

❌ **Combined test + implementation commits** (separate RED and GREEN)

❌ **Skipping test phase** (write tests first, always)

❌ **Breaking tests during refactor** (tests must stay green)

❌ **Merging with failing quality gates** (10/10 required)

## Historical Note

Recent commits (1d4258a, d3418dd, 7b62902) violated this workflow:
- No feature branches used (direct on main)
- Tests + implementation in single commit
- No separate RED phase commits

**From now on:** STRICT adherence to TDD + Git workflow. No exceptions.

## Related Documentation

- [QUALITY_GATES.md](QUALITY_GATES.md) - Quality checklist
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Branching and commit conventions
- [CODE_STYLE.md](CODE_STYLE.md) - Code formatting standards
