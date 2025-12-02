<!-- filepath: docs/development/backend/dtos/EXECUTION_COMMAND_DESIGN.md -->
# ExecutionCommand Design Document

**Status:** Rename Required  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | ExecutionCommand (currently `ExecutionDirective`) |
| **ID Prefix** | `EXC_` (currently `EXE_`) |
| **Layer** | Execution (Post-Causality) |
| **File Path** | `backend/dtos/execution/execution_command.py` (currently `execution_directive.py`) |
| **Status** | ⚠️ Needs Rename |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExecutionPlanner (4th TradePlanner) |
| **Consumer(s)** | ExecutionWorker (via EventBus) |
| **Trigger** | All 4 TradePlans aggregated by ExecutionPlanner |

**Architectural Role (per EXECUTION_FLOW.md, TRADE_LIFECYCLE.md):**
- ExecutionPlanner aggregates EntryPlan + SizePlan + ExitPlan + ExecutionPlan
- ExecutionCommand is the **final aggregated execution instruction**
- Contains complete CausalityChain for traceability
- ExecutionWorker receives this and creates actual Orders

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `command_id` | `str` | ✅ | Auto-generated | ExecutionWorker, Journal | Pattern: `^EXC_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `causality` | `CausalityChain` | ✅ | ExecutionPlanner | ExecutionWorker, Journal | Complete chain with plan IDs |
| `entry_plan` | `EntryPlan \| None` | ❌ | ExecutionPlanner | ExecutionWorker | Entry specification |
| `size_plan` | `SizePlan \| None` | ❌ | ExecutionPlanner | ExecutionWorker | Sizing specification |
| `exit_plan` | `ExitPlan \| None` | ❌ | ExecutionPlanner | ExecutionWorker | Exit specification |
| `execution_plan` | `ExecutionPlan \| None` | ❌ | ExecutionPlanner | ExecutionWorker | Execution trade-offs |

**Validation:** At least 1 plan required (cannot be empty command).

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | **Post-causality** (complete chain) |
| **Has causality field** | ✅ **YES** - Complete CausalityChain |
| **ID tracked in CausalityChain** | `execution_command_id` (currently `execution_directive_id`) |

**CausalityChain at this point contains:**
- `origin` - From PlatformDataDTO
- `signal_ids[]` - From consumed Signals
- `risk_ids[]` - From consumed Risks
- `strategy_directive_id` - From StrategyPlanner decision
- `entry_plan_id`, `size_plan_id`, `exit_plan_id`, `execution_plan_id` - Plan IDs
- `execution_command_id` - Self-reference

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Final execution instruction - never modified. Audit trail integrity. |

---

## 6. Examples

### NEW_TRADE - Complete Setup (all 4 plans)
```json
{
  "command_id": "EXC_20251201_145000_a1b2c3d4",
  "causality": {
    "origin": {"id": "TCK_20251201_143000_abc123", "type": "TICK"},
    "signal_ids": ["SIG_20251201_143100_def456"],
    "risk_ids": [],
    "strategy_directive_id": "STR_20251201_143110_ghi789",
    "entry_plan_id": "ENT_20251201_144500_jkl012",
    "size_plan_id": "SIZ_20251201_144510_mno345",
    "exit_plan_id": "EXT_20251201_144520_pqr678",
    "execution_plan_id": "EXP_20251201_144530_stu901",
    "execution_command_id": "EXC_20251201_145000_a1b2c3d4"
  },
  "entry_plan": {
    "plan_id": "ENT_20251201_144500_jkl012",
    "symbol": "BTC_USDT",
    "direction": "BUY",
    "order_type": "LIMIT",
    "limit_price": "100000.00"
  },
  "size_plan": {
    "plan_id": "SIZ_20251201_144510_mno345",
    "position_size": "0.5",
    "position_value": "50000.00",
    "risk_amount": "500.00"
  },
  "exit_plan": {
    "plan_id": "EXT_20251201_144520_pqr678",
    "stop_loss_price": "95000.00",
    "take_profit_price": "110000.00"
  },
  "execution_plan": {
    "plan_id": "EXP_20251201_144530_stu901",
    "action": "EXECUTE_TRADE",
    "execution_urgency": "0.80",
    "visibility_preference": "0.50",
    "max_slippage_pct": "0.0050"
  }
}
```

### MODIFY_EXISTING - Trailing Stop (exit only)
```json
{
  "command_id": "EXC_20251201_160000_b2c3d4e5",
  "causality": {
    "origin": {"id": "TCK_20251201_155900_xyz789", "type": "TICK"},
    "strategy_directive_id": "STR_20251201_155950_abc012",
    "exit_plan_id": "EXT_20251201_155955_def345",
    "execution_command_id": "EXC_20251201_160000_b2c3d4e5"
  },
  "entry_plan": null,
  "size_plan": null,
  "exit_plan": {
    "plan_id": "EXT_20251201_155955_def345",
    "stop_loss_price": "98000.00",
    "take_profit_price": null
  },
  "execution_plan": null
}
```

---

## 7. Dependencies

- `backend/dtos/causality.py` → `CausalityChain`
- `backend/dtos/strategy/entry_plan.py` → `EntryPlan`
- `backend/dtos/strategy/size_plan.py` → `SizePlan`
- `backend/dtos/strategy/exit_plan.py` → `ExitPlan`
- `backend/dtos/strategy/execution_plan.py` → `ExecutionPlan`
- `backend/utils/id_generators.py` → `generate_execution_command_id()` (NEW)
- `pydantic.BaseModel`

---

## 8. Breaking Changes Required

| Current | New | Impact |
|---------|-----|--------|
| Class name `ExecutionDirective` | `ExecutionCommand` | Rename class. Major impact across codebase. |
| File `execution_directive.py` | `execution_command.py` | Rename file. Update all imports. |
| Field `directive_id` | `command_id` | Rename field. Update serialization/tests. |
| ID prefix `EXE_` | `EXC_` | New prefix in id_generators.py. |
| Generator `generate_execution_directive_id()` | `generate_execution_command_id()` | Rename/add function. |
| CausalityChain field `execution_directive_id` | `execution_command_id` | Update CausalityChain DTO. |
| Examples use `tick_id` | Use `origin: {id, type}` | Update json_schema_extra examples. |

### Migration Checklist

- [ ] Rename class `ExecutionDirective` → `ExecutionCommand`
- [ ] Rename file `execution_directive.py` → `execution_command.py`
- [ ] Rename field `directive_id` → `command_id`
- [ ] Add `generate_execution_command_id()` to id_generators.py
- [ ] Update CausalityChain: `execution_directive_id` → `execution_command_id`
- [ ] Update all imports throughout codebase
- [ ] Update json_schema_extra examples (tick_id → origin)
- [ ] Update all tests
- [ ] Update ExecutionPlanner implementations

---

## 9. Naming Rationale

**Why rename ExecutionDirective → ExecutionCommand?**

1. **Naming Conflict:** `ExecutionDirective` class name conflicts with `ExecutionDirective` sub-directive in StrategyDirective
2. **Semantic Clarity:**
   - Sub-directives are *hints/constraints* → use `{Role}Directive` pattern
   - Output DTOs are *imperative commands* → use `{Role}Plan` or `{Role}Command` pattern
3. **Pattern Consistency:**
   - `EntryDirective` (hint) vs `EntryPlan` (output)
   - `SizeDirective` (hint) vs `SizePlan` (output)
   - `ExecutionDirective` (hint) vs `ExecutionPlan` (output)
   - `ExecutionCommand` = aggregated output of all 4 TradePlanners

---

## 10. Verification Checklist

### Design Document
- [x] All 8 sections completed
- [x] Reviewed against EXECUTION_FLOW.md
- [x] Reviewed against TRADE_LIFECYCLE.md
- [x] Breaking changes documented
- [x] Naming rationale documented

### Implementation (post-refactor)
- [ ] File renamed: `execution_directive.py` → `execution_command.py`
- [ ] Class renamed: `ExecutionDirective` → `ExecutionCommand`
- [ ] Field renamed: `directive_id` → `command_id`
- [ ] ID generator added
- [ ] CausalityChain updated
- [ ] Examples updated (tick_id → origin)
- [ ] model_config correct (frozen=True)

### Tests (post-refactor)
- [ ] Test file renamed
- [ ] All tests pass

### Integration
- [ ] All imports updated
- [ ] ExecutionPlanner updated
- [ ] ExecutionWorker updated

### Quality Gates
- [ ] `pytest tests/unit/dtos/execution/test_execution_command.py` - ALL PASS
- [ ] `pyright backend/dtos/execution/execution_command.py` - No errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
