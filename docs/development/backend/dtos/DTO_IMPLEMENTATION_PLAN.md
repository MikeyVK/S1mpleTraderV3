<!-- filepath: docs/development/backend/dtos/DTO_IMPLEMENTATION_PLAN.md -->
# DTO Implementation Plan - S1mpleTraderV3

**Status:** Active  
**Version:** 1.0  
**Created:** 2025-12-01  
**Last Updated:** 2025-12-01

---

## Executive Summary

This document provides the complete implementation roadmap for DTO refactoring and new DTO implementation in S1mpleTraderV3. It follows a TDD-first approach and is structured in priority phases.

**Total Effort Estimate:** ~20-25 hours

---

## Part A: Refactor Existing DTOs

### Phase 1: Critical Architectural Fixes (Priority: CRITICAL)

**Issues:** #1, #2 - Pre-causality DTOs incorrectly have causality fields

**Estimated Effort:** 4 hours

#### 1.1 Signal DTO Refactor

**File:** `backend/dtos/strategy/signal.py`  
**Design Doc:** [SIGNAL_DESIGN.md](SIGNAL_DESIGN.md)

| Change | Current | New |
|--------|---------|-----|
| Remove field | `causality: CausalityChain` | (deleted) |
| Rename field | `asset: str` | `symbol: str` |
| Update pattern | `^[A-Z0-9_]+/[A-Z0-9_]+$` | `^[A-Z][A-Z0-9_]{2,}$` |
| Change type | `confidence: float` | `confidence: Decimal` |

**TDD Steps:**

```bash
# Step 1: Update tests FIRST
# Edit: tests/unit/dtos/strategy/test_signal.py
# - Remove all causality-related test cases
# - Rename 'asset' → 'symbol' in all tests
# - Update pattern expectations
# - Change confidence to Decimal

# Step 2: Run tests (should FAIL - RED)
pytest tests/unit/dtos/strategy/test_signal.py -v

# Step 3: Implement changes
# Edit: backend/dtos/strategy/signal.py
# - Remove causality field and import
# - Rename asset → symbol
# - Update validation pattern
# - Change confidence: float → Decimal

# Step 4: Run tests (should PASS - GREEN)
pytest tests/unit/dtos/strategy/test_signal.py -v

# Step 5: Quality checks
pyright backend/dtos/strategy/signal.py
ruff check backend/dtos/strategy/signal.py
```

**Impact Analysis:**
- `tests/unit/dtos/strategy/test_signal.py` - Update all tests
- SignalDetector plugin implementations - Update constructor calls
- Any code that references `signal.asset` - Update to `signal.symbol`

---

#### 1.2 Risk DTO Refactor

**File:** `backend/dtos/strategy/risk.py`  
**Design Doc:** [RISK_DESIGN.md](RISK_DESIGN.md)

| Change | Current | New |
|--------|---------|-----|
| Remove field | `causality: CausalityChain` | (deleted) |
| Rename field | `affected_asset: str \| None` | `affected_symbol: str \| None` |
| Update pattern | `^[A-Z0-9_]+/[A-Z0-9_]+$` | `^[A-Z][A-Z0-9]{2,}$` |
| Change type | `severity: float` | `severity: Decimal` |

**TDD Steps:** Same pattern as Signal

**Impact Analysis:**
- `tests/unit/dtos/strategy/test_risk.py` - Update all tests
- RiskMonitor plugin implementations - Update constructor calls
- Any code that references `risk.affected_asset` - Update to `risk.affected_symbol`

---

### Phase 2: Terminology Alignment (Priority: HIGH)

**Issues:** #6, #7 - Naming conflicts and terminology issues

**Estimated Effort:** 5 hours

#### 2.1 ExecutionDirective → ExecutionCommand Rename

**Current File:** `backend/dtos/execution/execution_directive.py`  
**New File:** `backend/dtos/execution/execution_command.py`  
**Design Doc:** [EXECUTION_COMMAND_DESIGN.md](EXECUTION_COMMAND_DESIGN.md)

| Change | Current | New |
|--------|---------|-----|
| Class name | `ExecutionDirective` | `ExecutionCommand` |
| File name | `execution_directive.py` | `execution_command.py` |
| Field name | `directive_id` | `command_id` |
| ID prefix | `EXE_` | `EXC_` |
| Generator | `generate_execution_directive_id()` | `generate_execution_command_id()` |
| CausalityChain field | `execution_directive_id` | `execution_command_id` |

**TDD Steps:**

```bash
# Step 1: Add new ID generator
# Edit: backend/utils/id_generators.py
# Add: generate_execution_command_id() function

# Step 2: Update CausalityChain
# Edit: backend/dtos/causality.py
# Rename: execution_directive_id → execution_command_id

# Step 3: Create new test file (copy and modify)
# Create: tests/unit/dtos/execution/test_execution_command.py

# Step 4: Create new DTO file
# Create: backend/dtos/execution/execution_command.py

# Step 5: Update all imports across codebase
# PowerShell: Find all references
Select-String -Path "backend\**\*.py" -Pattern "from backend.dtos.execution.execution_directive" -Recurse
# Update to: from backend.dtos.execution.execution_command

# Step 6: Remove old files (after all tests pass)
# Delete: backend/dtos/execution/execution_directive.py
# Delete: tests/unit/dtos/execution/test_execution_directive.py
```

**Impact Analysis - Files to Update:**
- `backend/dtos/execution/__init__.py`
- `backend/dtos/causality.py`
- `backend/utils/id_generators.py`
- All ExecutionPlanner implementations
- All ExecutionWorker implementations
- All test files referencing ExecutionDirective

---

#### 2.2 StrategyDirective Field Rename

**File:** `backend/dtos/strategy/strategy_directive.py`  
**Design Doc:** [STRATEGY_DIRECTIVE_DESIGN.md](STRATEGY_DIRECTIVE_DESIGN.md)

| Change | Current | New |
|--------|---------|-----|
| Field name | `target_trade_ids` | `target_plan_ids` |

**TDD Steps:**

```bash
# Step 1: Update tests
# Edit: tests/unit/dtos/strategy/test_strategy_directive.py
# Rename: target_trade_ids → target_plan_ids

# Step 2: Run tests (RED)
# Step 3: Update DTO
# Step 4: Run tests (GREEN)
```

---

### Phase 3: Code Smell Cleanup (Priority: MEDIUM)

**Issues:** #8, #9 - ExecutionGroup issues

**Estimated Effort:** 3 hours

#### 3.1 ExecutionGroup Cleanup

**File:** `backend/dtos/execution/execution_group.py`  
**Design Doc:** [EXECUTION_GROUP_DESIGN.md](EXECUTION_GROUP_DESIGN.md)

| Change | Current | New |
|--------|---------|-----|
| Remove enum value | `ExecutionStrategyType.DCA` | (deleted) |
| Analyze/type | `metadata: Dict[str, Any]` | Remove or type specifically |

**TDD Steps:**

```powershell
# Step 1: Check for DCA usage
Select-String -Path "backend\**\*.py","tests\**\*.py" -Pattern "ExecutionStrategyType.DCA" -Recurse

# Step 2: If no usage, update tests to not reference DCA
# Step 3: Remove DCA from enum
# Step 4: Analyze metadata usage
Select-String -Path "backend\**\*.py","tests\**\*.py" -Pattern "\.metadata" -Recurse | Select-String -Pattern "execution" -CaseSensitive:$false

# Step 5: Based on analysis, either:
#   - Remove metadata field entirely
#   - Or replace with typed fields (chunk_size, interval_seconds, etc.)
```

---

### Phase 4: Infrastructure & Low Priority (Priority: LOW)

**Issues:** #11, #12, #13

**Estimated Effort:** 4 hours

#### 4.1 ExecutionCommand Examples Update

**File:** `backend/dtos/execution/execution_command.py`

Update `json_schema_extra` examples:
- Change `tick_id` references to `origin: {id, type}` format

#### 4.2 Enum Centralization

**File:** `backend/core/enums.py`

Move/consolidate enums:
- `DirectiveScope` from strategy_directive.py
- `ExecutionMode` if scattered
- `ExecutionAction` from execution_plan.py
- `OrderType`, `OrderStatus` (new - for Order DTO)
- `GroupStatus`, `ExecutionStrategyType` from execution_group.py

**Note:** This is optional cleanup - existing inline enums work fine.

#### 4.3 TickCache → StrategyCache Rename

**File:** `backend/core/strategy_cache.py` (if exists)

Per EXECUTION_FLOW.md, the correct name is `StrategyCache`.

---

## Part B: Implement New DTOs

### Phase 5: State Layer DTOs (Priority: MEDIUM)

**Estimated Effort:** 6 hours

#### 5.1 Order DTO

**File:** `backend/dtos/state/order.py`  
**Design Doc:** [ORDER_DESIGN.md](ORDER_DESIGN.md)

**Prerequisites:**
- [ ] Add `generate_order_id()` to id_generators.py
- [ ] Add `OrderType`, `OrderStatus` enums to enums.py

**TDD Steps:**

```bash
# Step 1: Add prerequisites
# Edit: backend/utils/id_generators.py
def generate_order_id() -> str:
    return _generate_id("ORD")

# Edit: backend/core/enums.py
class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

# Step 2: Write tests FIRST
# Create: tests/unit/dtos/state/test_order.py

# Step 3: Run tests (RED)
pytest tests/unit/dtos/state/test_order.py -v

# Step 4: Implement Order DTO
# Create: backend/dtos/state/order.py

# Step 5: Run tests (GREEN)
pytest tests/unit/dtos/state/test_order.py -v
```

---

#### 5.2 Fill DTO

**File:** `backend/dtos/state/fill.py`  
**Design Doc:** [FILL_DESIGN.md](FILL_DESIGN.md)

**Prerequisites:**
- [ ] Order DTO must be implemented first
- [ ] Add `generate_fill_id()` to id_generators.py

**TDD Steps:** Same pattern as Order

---

### Phase 6: CausalityChain Review (Priority: LOW - DEFER)

**Estimated Effort:** 2 hours

**Issue:** #14 - Review if intermediate plan IDs are needed

**Current state:** CausalityChain contains:
- `entry_plan_id`
- `size_plan_id`
- `exit_plan_id`
- `execution_plan_id`

**Question:** Are these needed for Journal reconstruction?

**Arguments PRO keeping:**
- Fine-grained traceability ("which planner produced what")
- Debugging aid

**Arguments CON keeping:**
- Journal only needs: Signal → Decision → Order
- Intermediate plans are implementation details

**Decision:** Defer until Journal implementation. Document rationale regardless of decision.

---

## Implementation Schedule

### Week 1: Critical Fixes

| Day | Task | Effort | Files |
|-----|------|--------|-------|
| Day 1 | Signal DTO refactor | 2h | signal.py, test_signal.py |
| Day 1 | Risk DTO refactor | 2h | risk.py, test_risk.py |
| Day 2 | ExecutionCommand rename (prep) | 2h | id_generators.py, causality.py |
| Day 2 | ExecutionCommand rename (impl) | 2h | execution_command.py, tests |
| Day 3 | Import updates & verification | 2h | All affected files |

### Week 2: Medium Priority

| Day | Task | Effort | Files |
|-----|------|--------|-------|
| Day 1 | StrategyDirective field rename | 1h | strategy_directive.py |
| Day 1 | ExecutionGroup DCA removal | 1h | execution_group.py |
| Day 1 | ExecutionGroup metadata analysis | 1h | Analysis only |
| Day 2 | Order DTO prerequisites | 1h | enums.py, id_generators.py |
| Day 2 | Order DTO implementation | 3h | order.py, test_order.py |
| Day 3 | Fill DTO implementation | 2h | fill.py, test_fill.py |

### Week 3: Cleanup & Documentation

| Day | Task | Effort | Files |
|-----|------|--------|-------|
| Day 1 | Example updates | 1h | Various json_schema_extra |
| Day 1 | Enum centralization (optional) | 2h | enums.py |
| Day 2 | CausalityChain review | 2h | causality.py, docs |
| Day 2 | Final verification | 2h | All |

---

## Verification Protocol

### Per-DTO Verification

After each DTO change, run:

```bash
# 1. Unit tests
pytest tests/unit/dtos/{layer}/test_{dto}.py -v

# 2. Type checking
pyright backend/dtos/{layer}/{dto}.py

# 3. Linting
ruff check backend/dtos/{layer}/{dto}.py

# 4. Full test suite (catch integration issues)
pytest tests/ -v --tb=short
```

### Full Suite Verification

After each phase completion:

```bash
# All tests
pytest tests/ -v

# All type checks
pyright backend/

# All linting
ruff check backend/

# Import verification
python -c "from backend.dtos import *; print('All imports OK')"
```

---

## Risk Mitigation

### Breaking Change Risks

| Risk | Mitigation |
|------|------------|
| Signal/Risk causality removal breaks plugins | Search all plugin code for causality usage BEFORE removal |
| ExecutionCommand rename misses imports | Use grep/find to identify ALL references |
| Symbol pattern change breaks existing data | Format changes from `BTC/EUR` to `BTC_EUR` (underscore) - validate no stored data uses slash format |

### Rollback Plan

Each phase is independent. If issues arise:
1. Revert the specific phase commits
2. Fix issues in isolation
3. Re-attempt with fixes

### Testing Strategy

1. **Unit tests first** - Validate DTO in isolation
2. **Integration tests** - Validate with actual workers
3. **Manual smoke test** - Run a basic strategy flow

---

## Appendix: DTO Status Matrix

| DTO | File | Impl | Tests | SRP | Issues | Phase |
|-----|------|------|-------|-----|--------|-------|
| Origin | ✅ | ✅ Complete | ✅ | ✅ | - | - |
| PlatformDataDTO | ✅ | ✅ Complete | ✅ | ✅ | - | - |
| CausalityChain | ✅ | ✅ Complete | ✅ | ⚠️ | #14 (defer) | P6 |
| DispositionEnvelope | ✅ | ✅ Complete | ✅ | ✅ | - | - |
| **Signal** | ✅ | ⚠️ Issues | ⚠️ | ❌ | #1,#3,#5,#10 | **P1** |
| **Risk** | ✅ | ⚠️ Issues | ⚠️ | ❌ | #2,#4,#5,#10 | **P1** |
| **StrategyDirective** | ✅ | ⚠️ Issues | ⚠️ | ⚠️ | #7 | **P2** |
| EntryPlan | ✅ | ✅ Lean | ✅ | ✅ | - | - |
| SizePlan | ✅ | ✅ Lean | ✅ | ✅ | - | - |
| ExitPlan | ✅ | ✅ Lean | ✅ | ✅ | - | - |
| ExecutionPlan | ✅ | ✅ Good | ✅ | ✅ | - | - |
| **ExecutionCommand** | ✅ | ⚠️ Rename | ⚠️ | ✅ | #6,#11 | **P2** |
| **ExecutionGroup** | ✅ | ⚠️ Issues | ⚠️ | ❌ | #8,#9 | **P3** |
| TradePlan | ✅ | ✅ Minimal | ✅ | ✅ | - | - |
| **Order** | ❌ | Not impl | - | - | - | **P5** |
| **Fill** | ❌ | Not impl | - | - | - | **P5** |

---

## Document References

### Design Documents (created)
- [SIGNAL_DESIGN.md](SIGNAL_DESIGN.md)
- [RISK_DESIGN.md](RISK_DESIGN.md)
- [STRATEGY_DIRECTIVE_DESIGN.md](STRATEGY_DIRECTIVE_DESIGN.md)
- [EXECUTION_COMMAND_DESIGN.md](EXECUTION_COMMAND_DESIGN.md)
- [EXECUTION_GROUP_DESIGN.md](EXECUTION_GROUP_DESIGN.md)
- [PLATFORM_DATA_DTO_DESIGN.md](PLATFORM_DATA_DTO_DESIGN.md)
- [ENTRY_PLAN_DESIGN.md](ENTRY_PLAN_DESIGN.md)
- [SIZE_PLAN_DESIGN.md](SIZE_PLAN_DESIGN.md)
- [EXIT_PLAN_DESIGN.md](EXIT_PLAN_DESIGN.md)
- [EXECUTION_PLAN_DESIGN.md](EXECUTION_PLAN_DESIGN.md)
- [DISPOSITION_ENVELOPE_DESIGN.md](DISPOSITION_ENVELOPE_DESIGN.md)
- [ORDER_DESIGN.md](ORDER_DESIGN.md)
- [FILL_DESIGN.md](FILL_DESIGN.md)
- [ORIGIN_DTO_DESIGN.md](ORIGIN_DTO_DESIGN.md) (existing)
- [CAUSALITY_CHAIN_DESIGN.md](CAUSALITY_CHAIN_DESIGN.md) (existing)
- [TRADE_PLAN_DESIGN.md](TRADE_PLAN_DESIGN.md) (existing)

### Authoritative Architecture Docs
- `docs/architecture/WORKER_TAXONOMY.md` (v2.0)
- `docs/architecture/PIPELINE_FLOW.md` (v3.0)
- `docs/architecture/EXECUTION_FLOW.md` (v2.0)
- `docs/architecture/TRADE_LIFECYCLE.md` (v2.0)

### Coding Standards
- `docs/coding_standards/CODE_STYLE.md`
- `docs/coding_standards/TDD_WORKFLOW.md`

---

*Document Version: 1.0*  
*Created: 2025-12-01*
