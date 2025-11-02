# Git Workflow

## Overview

S1mpleTrader V3 uses a **feature branch workflow** with strict quality gates. All development happens on dedicated branches, and only production-ready code merges to `main`.

## Branch Strategy

### Main Branch

**`main`** - Production-ready code only

**Requirements:**
- All tests passing (100%)
- All quality gates met (10/10)
- No trailing whitespace
- Imports at top-level only
- Type checking clean (for DTOs)

**Never commit directly to main** during feature development!

### Feature Branches

**`feature/*`** - Development branches for new features

**Naming conventions:**
- `feature/size-plan-dto` - New DTOs
- `feature/signal-detector` - New workers
- `feature/event-adapter` - New adapters
- `feature/multi-strategy-cache` - Architectural changes

**Other branch types:**
- `fix/*` - Bug fixes (e.g., `fix/causality-chain-bug`)
- `refactor/*` - Code quality improvements
- `docs/*` - Documentation only (e.g., `docs/restructure-agent-md`)

## Feature Development Flow

### 1. Create Feature Branch

Start every new feature with a dedicated branch:

```powershell
# Ensure main is up-to-date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/size-plan-dto
```

### 2. TDD Cycle with Commits

Follow RED → GREEN → REFACTOR with separate commits:

**RED Phase:**
```powershell
git add tests/unit/dtos/strategy/test_size_plan.py
git commit -m "test: add failing tests for SizePlan DTO

- Test creation with valid fields
- Test validation rules
- Test edge cases

Status: RED - tests fail (implementation pending)"
```

**GREEN Phase:**
```powershell
git add backend/dtos/strategy/size_plan.py
git commit -m "feat: implement SizePlan DTO

- Add quantity, risk_amount, position_value fields
- Add validation for positive values
- All tests passing (20/20)

Status: GREEN"
```

**REFACTOR Phase:**
```powershell
git add backend/dtos/strategy/size_plan.py tests/unit/dtos/strategy/test_size_plan.py
git commit -m "refactor: improve SizePlan DTO code quality

- Add comprehensive docstrings
- Fix line length violations
- Add type hints for all fields
- Clean up whitespace
- Add json_schema_extra examples

Quality gates: All 10/10
Status: GREEN (tests still 20/20)"
```

### 3. Quality Gates Verification

Update metrics after all gates pass:

```powershell
git add docs/implementation/IMPLEMENTATION_STATUS.md
git commit -m "docs: update Quality Metrics Dashboard for SizePlan

- Added SizePlan row: 10/10 all gates
- Test coverage: 20/20 passing"
```

### 4. Merge to Main

Once feature is complete and all quality gates pass:

```powershell
# Switch to main
git checkout main

# Merge feature branch (use --no-ff to preserve history)
git merge --no-ff feature/size-plan-dto

# Push to GitHub
git push origin main

# Delete feature branch (cleanup)
git branch -d feature/size-plan-dto
```

**Alternative: Squash merge** for cleaner history:
```powershell
git checkout main
git merge --squash feature/size-plan-dto
git commit -m "feat: implement SizePlan DTO (#123)

Complete implementation with tests and quality gates"
git push origin main
git branch -d feature/size-plan-dto
```

## Commit Message Conventions

Use **Conventional Commits** format for clear history:

### Format

```
<type>: <short summary>

<optional body with bullet points>
- Detail 1
- Detail 2

<optional footer with metadata>
Status: RED|GREEN
Quality gates: 10/10
```

### Types

- `test:` - Tests only (RED phase)
- `feat:` - New feature implementation (GREEN phase)
- `refactor:` - Code quality improvements (REFACTOR phase)
- `docs:` - Documentation updates
- `fix:` - Bug fixes
- `chore:` - Build/tooling changes

### Examples

**RED Phase:**
```
test: add failing tests for ExecutionDirective DTO

- Test causality chain tracking
- Test routing plan integration
- Test validation rules

Status: RED - implementation pending
```

**GREEN Phase:**
```
feat: implement ExecutionDirective DTO

- Add causality, routing_plan, entry_plan fields
- Implement validation for required fields
- All tests passing (25/25)

Status: GREEN
```

**REFACTOR Phase:**
```
refactor: improve ExecutionDirective quality

- Add json_schema_extra examples
- Fix trailing whitespace (15 violations)
- Add comprehensive docstrings
- Split long lines (<100 chars)

Quality gates: 10/10
Status: GREEN (tests still 25/25)
```

**Documentation:**
```
docs: update IMPLEMENTATION_STATUS with ExecutionDirective

- Added row: 10/10 all gates, 25/25 tests
- Updated completion percentage: 8/14 DTOs (57%)
```

## Commit Best Practices

### Commit Early, Commit Often

On feature branches, commit frequently:
- After each RED phase (failing tests)
- After each GREEN phase (passing implementation)
- After each REFACTOR phase (quality improvements)
- After quality gates verification

**Don't:**
- Wait until feature is "perfect" to commit
- Combine RED + GREEN in single commit
- Commit broken code to main

### Atomic Commits

Each commit should represent **one logical change**:

**Good:**
```powershell
# Commit 1: Failing tests
git commit -m "test: add SizePlan validation tests"

# Commit 2: Implementation
git commit -m "feat: implement SizePlan validators"

# Commit 3: Quality
git commit -m "refactor: fix whitespace in SizePlan"
```

**Bad:**
```powershell
# Combining multiple changes
git commit -m "Add SizePlan DTO with tests and also fix ExecutionPlan bug"
```

### Descriptive Messages

**Good:**
```
feat: implement Signal DTO

- Add signal_id, symbol, direction fields
- Implement causality tracking
- Add UTC timestamp validation
- All tests passing (22/22)

Status: GREEN
```

**Bad:**
```
fix stuff
WIP
updated files
```

## Branch Cleanup

Delete feature branches after merging:

```powershell
# Local cleanup
git branch -d feature/size-plan-dto

# Remote cleanup (if pushed)
git push origin --delete feature/size-plan-dto
```

**Don't accumulate stale branches!**

## Historical Anti-Patterns

Recent commits (1d4258a, d3418dd, 7b62902) violated this workflow:

**Issues:**
- ❌ Direct commits to main (no feature branch)
- ❌ Tests + implementation in single commit (should be RED → GREEN)
- ❌ No separate test commits for RED phase

**Correction:** From now on, STRICT adherence to feature branch workflow.

## Integration with GitHub

### Pull Requests (Optional)

For team collaboration, use pull requests:

```powershell
# Push feature branch to GitHub
git push -u origin feature/size-plan-dto

# Create PR via GitHub web UI
# - Title: "feat: implement SizePlan DTO"
# - Description: List changes, reference issues
# - Request reviews if needed

# After approval, merge via GitHub UI
# Then delete branch locally and remotely
```

### Tags for Releases

Mark significant milestones:

```powershell
# After completing Phase 1.2 (all protocols)
git tag -a v0.1.2 -m "Phase 1.2: Core protocols complete

- IStrategyCache implemented
- IEventBus implemented
- IWorkerLifecycle implemented
- All tests passing (300+)"

git push origin v0.1.2
```

## Related Documentation

- [TDD_WORKFLOW.md](TDD_WORKFLOW.md) - Test-driven development cycle
- [QUALITY_GATES.md](QUALITY_GATES.md) - Quality checklist
- [CODE_STYLE.md](CODE_STYLE.md) - Code formatting standards
