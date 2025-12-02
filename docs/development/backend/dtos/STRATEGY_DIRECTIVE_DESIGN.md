<!-- filepath: docs/development/backend/dtos/STRATEGY_DIRECTIVE_DESIGN.md -->
# StrategyDirective Design Document

**Status:** Refactor Required  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | StrategyDirective |
| **ID Prefix** | `STR_` |
| **Layer** | Strategy (Post-Causality Start) |
| **File Path** | `backend/dtos/strategy/strategy_directive.py` |
| **Status** | ⚠️ Needs Refactor |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | StrategyPlanner (plugin worker) |
| **Consumer(s)** | TradePlanners (Entry, Size, Exit, Execution) via EventBus |
| **Trigger** | StrategyPlanner decision based on Signals + Risks |

**Architectural Role (per PIPELINE_FLOW.md, WORKER_TAXONOMY.md):**
- StrategyPlanner is the **bridge** between Analysis Layer (Signal/Risk) and Planning Layer
- StrategyDirective is the **FIRST post-causality DTO** in the pipeline
- Creates CausalityChain with origin + signal_ids + risk_ids
- Contains 4 sub-directives with constraints/hints for each TradePlanner

---

## 3. Fields

### Main StrategyDirective Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `directive_id` | `str` | ✅ | Auto-generated | TradePlanners, Journal | Pattern: `^STR_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `causality` | `CausalityChain` | ✅ | StrategyPlanner | TradePlanners, Journal | Must have origin, signal_ids, risk_ids |
| `scope` | `DirectiveScope` | ✅ | StrategyPlanner | All TradePlanners | Enum: NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING |
| `target_plan_ids` | `list[str]` | ❌ | StrategyPlanner | TradePlanners | For MODIFY/CLOSE: which TradePlan IDs to target |
| `entry_directive` | `EntryDirective` | ❌ | StrategyPlanner | EntryPlanner | Entry constraints/hints |
| `size_directive` | `SizeDirective` | ❌ | StrategyPlanner | SizePlanner | Sizing constraints/hints |
| `exit_directive` | `ExitDirective` | ❌ | StrategyPlanner | ExitPlanner | Exit constraints/hints |
| `execution_directive` | `ExecutionDirective` | ❌ | StrategyPlanner | ExecutionPlanner | Execution constraints/hints |

### Sub-Directive: EntryDirective

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `symbol` | `str` | ✅ | Trading symbol (e.g., `BTC_USDT`) |
| `direction` | `str` | ✅ | Trade direction: `BUY` or `SELL` |
| `timing_preference` | `Decimal` | ❌ | Entry urgency [0.0-1.0], default 0.5 |
| `preferred_price_zone` | `tuple[Decimal, Decimal] \| None` | ❌ | Price zone (min, max) |
| `max_acceptable_slippage` | `Decimal` | ❌ | Max slippage decimal, default 0.005 |

### Sub-Directive: SizeDirective

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `aggressiveness` | `Decimal` | ❌ | Size aggressiveness [0.0-1.0], default 0.5 |
| `max_risk_amount` | `Decimal` | ✅ | Max risk in quote currency |
| `account_risk_pct` | `Decimal` | ❌ | Max account risk decimal, default 0.02 |

### Sub-Directive: ExitDirective

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `profit_taking_preference` | `Decimal` | ❌ | Profit-taking aggressiveness [0.0-1.0] |
| `risk_reward_ratio` | `Decimal` | ❌ | Min R:R ratio, default 2.0 |
| `stop_loss_tolerance` | `Decimal` | ❌ | SL distance decimal, default 0.02 |

### Sub-Directive: ExecutionDirective (sub-directive, NOT output DTO)

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `execution_urgency` | `Decimal` | ❌ | Urgency [0.0-1.0], default 0.5 |
| `iceberg_preference` | `Decimal \| None` | ❌ | Iceberg preference [0.0-1.0] |
| `max_total_slippage_pct` | `Decimal` | ❌ | Max total slippage, default 0.01 |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | **Post-causality** (first DTO with causality) |
| **Has causality field** | ✅ **YES** - CausalityChain |
| **ID tracked in CausalityChain** | `strategy_directive_id` added by StrategyPlanner |

**CausalityChain Creation Pattern:**
```python
# StrategyPlanner creates CausalityChain from PlatformDataDTO origin
causality = CausalityChain(
    origin=platform_data.origin,  # From PlatformDataDTO
    signal_ids=[sig.signal_id for sig in consumed_signals],
    risk_ids=[risk.risk_id for risk in consumed_risks],
    strategy_directive_id=directive_id  # Self-reference
)
```

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Strategic decision - never modified. Immutability ensures audit integrity. |

---

## 6. Examples

### NEW_TRADE Directive
```json
{
  "directive_id": "STR_20251201_144000_d4e5f6a7",
  "causality": {
    "origin": {"id": "TCK_20251201_143500_abc123", "type": "TICK"},
    "signal_ids": ["SIG_20251201_143522_def456"],
    "risk_ids": [],
    "strategy_directive_id": "STR_20251201_144000_d4e5f6a7"
  },
  "scope": "NEW_TRADE",
  "target_plan_ids": [],
  "entry_directive": {
    "symbol": "BTC_USDT",
    "direction": "BUY",
    "timing_preference": "0.7",
    "max_acceptable_slippage": "0.003"
  },
  "size_directive": {
    "aggressiveness": "0.6",
    "max_risk_amount": "1000.00",
    "account_risk_pct": "0.02"
  },
  "exit_directive": {
    "risk_reward_ratio": "2.5",
    "stop_loss_tolerance": "0.015"
  },
  "execution_directive": {
    "execution_urgency": "0.8"
  }
}
```

### MODIFY_EXISTING Directive (Trailing Stop)
```json
{
  "directive_id": "STR_20251201_150000_e5f6a7b8",
  "causality": {
    "origin": {"id": "TCK_20251201_145900_xyz789", "type": "TICK"},
    "signal_ids": [],
    "risk_ids": [],
    "strategy_directive_id": "STR_20251201_150000_e5f6a7b8"
  },
  "scope": "MODIFY_EXISTING",
  "target_plan_ids": ["TPL_20251201_144010_ghi012"],
  "entry_directive": null,
  "size_directive": null,
  "exit_directive": {
    "stop_loss_tolerance": "0.010"
  },
  "execution_directive": null
}
```

---

## 7. Dependencies

- `backend/dtos/causality.py` → `CausalityChain`
- `backend/utils/id_generators.py` → `generate_strategy_directive_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`

---

## 8. Breaking Changes Required

| Current | New | Impact |
|---------|-----|--------|
| `target_trade_ids: list[str]` | `target_plan_ids: list[str]` | Rename field. Per TRADE_LIFECYCLE.md, Level 1 = TradePlan. |

**Note:** Sub-directive `ExecutionDirective` remains as-is. No naming conflict exists:
- `StrategyDirective.execution_directive` = sub-directive with hints for ExecutionPlanner
- `ExecutionCommand` = aggregated output DTO (renamed from file `execution_directive.py`)

### Migration Checklist

- [ ] Rename `target_trade_ids` → `target_plan_ids`
- [ ] Update docstrings to reflect TradePlan terminology
- [ ] Update all tests
- [ ] Update StrategyPlanner implementations

---

## 9. Verification Checklist

### Design Document
- [x] All 8 sections completed
- [x] Reviewed against PIPELINE_FLOW.md
- [x] Reviewed against TRADE_LIFECYCLE.md
- [x] Breaking changes documented

### Implementation (post-refactor)
- [ ] Field renamed: `target_trade_ids` → `target_plan_ids`
- [ ] Follows CODE_STYLE.md structure
- [ ] model_config correct (frozen=True)

### Tests (post-refactor)
- [ ] Test file updated
- [ ] All tests pass

### Quality Gates
- [ ] `pytest tests/unit/dtos/strategy/test_strategy_directive.py` - ALL PASS
- [ ] `pyright backend/dtos/strategy/strategy_directive.py` - No errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
