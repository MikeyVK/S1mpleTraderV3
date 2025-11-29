# docs/architecture/DTO_ARCHITECTURE.md
# DTO Architecture - S1mpleTraderV3

**Status:** PRELIMINARY
**Version:** 2.0
**Last Updated:** 2025-11-29---

## 1. Purpose

This document provides the **overview and design principles** for the DTO (Data Transfer Object) architecture.

**Purpose:**
- DTO taxonomy and categorization
- Design principles and conventions
- Cross-references to detailed DTO documentation

**Detailed DTO documentation:**
- [DTO Core](DTO_CORE.md) - Platform DTOs (Origin, PlatformDataDTO) and infrastructure (CausalityChain)
- [DTO Pipeline](DTO_PIPELINE.md) - Analysis DTOs (Signal, Risk) and Strategic DTOs (StrategyDirective, TradePlan)
- [DTO Execution](DTO_EXECUTION.md) - Planning DTOs and Execution DTOs

---

## 2. DTO Taxonomy

### 2.1 Platform DTOs (Origin Tracking & Data Ingestion)

| DTO | Purpose | Documentation |
|-----|---------|---------------|
| **Origin** | Type-safe platform data source identification | [DTO_CORE.md](DTO_CORE.md#origin) |
| **PlatformDataDTO** | Minimal envelope for platform data ingestion | [DTO_CORE.md](DTO_CORE.md#platformdatadto) |

### 2.2 Analysis DTOs (Detection → Decision)

| DTO | Purpose | Documentation |
|-----|---------|---------------|
| **Signal** | Trading opportunity detection output | [DTO_PIPELINE.md](DTO_PIPELINE.md#signal) |
| **Risk** | Threat/risk detection output | [DTO_PIPELINE.md](DTO_PIPELINE.md#risk) |
| **StrategyDirective** | Strategy planning decision output | [DTO_PIPELINE.md](DTO_PIPELINE.md#strategydirective) |

### 2.3 Strategic DTOs (Lifecycle Container)

| DTO | Purpose | Documentation |
|-----|---------|---------------|
| **TradePlan** | Execution Anchor & State Container | [DTO_PIPELINE.md](DTO_PIPELINE.md#tradeplan) |

### 2.4 Planning DTOs (Decision → Execution Intent)

| DTO | Purpose | Documentation |
|-----|---------|---------------|
| **EntryPlan** | Entry execution specifications | [DTO_EXECUTION.md](DTO_EXECUTION.md#entryplan) |
| **SizePlan** | Position sizing specifications | [DTO_EXECUTION.md](DTO_EXECUTION.md#sizeplan) |
| **ExitPlan** | Exit/stop-loss specifications | [DTO_EXECUTION.md](DTO_EXECUTION.md#exitplan) |
| **ExecutionPlan** | Execution trade-offs (urgency, slippage, visibility) | [DTO_EXECUTION.md](DTO_EXECUTION.md#executionplan) |

### 2.5 Execution DTOs (Orders & Coordination)

| DTO | Purpose | Documentation |
|-----|---------|---------------|
| **ExecutionDirective** | Aggregated execution instruction | [DTO_EXECUTION.md](DTO_EXECUTION.md#executiondirective) |
| **ExecutionDirectiveBatch** | Multi-directive atomic coordination | [DTO_EXECUTION.md](DTO_EXECUTION.md#executiondirectivebatch) |
| **ExecutionGroup** | Multi-order relationship tracking | [DTO_EXECUTION.md](DTO_EXECUTION.md#executiongroup) |

### 2.6 Cross-Cutting DTOs (Infrastructure)

| DTO | Purpose | Documentation |
|-----|---------|---------------|
| **CausalityChain** | ID-only causality tracking | [DTO_CORE.md](DTO_CORE.md#causalitychain) |
| **DispositionEnvelope** | Worker output routing control | [DTO_CORE.md](DTO_CORE.md#dispositionenvelope) |

---

## 3. Design Principles

### 3.1 Immutability by Default

**Frozen Models:** Most DTOs are frozen (immutable) after creation.
- Platform data is immutable snapshot of reality
- Signals/Risks are immutable facts ("detected at T")
- Execution plans are frozen coordination contracts

**Exceptions:** Mutable for lifecycle tracking:
- `StrategyDirective` - Enriched post-execution (order_ids tracking)
- `TradePlan` - Status field evolves (ACTIVE → CLOSED)
- `ExecutionGroup` - Tracking entity during execution lifecycle

### 3.2 Causality Chain

**Principle:** Every execution traces back to origin.

```
Origin (platform source)
  → Signal/Risk (detection facts)
    → StrategyDirective (planning decision)
      → ExecutionDirective (execution instruction)
        → Orders (connector operations)
```

**CausalityChain** carries ID-only references through the pipeline.

### 3.3 Lean Specifications

**Principle:** DTOs contain only execution-critical parameters.

- ❌ No metadata (timestamps, planner_id) - worker context handles this
- ❌ No computed fields (remaining_quantity) - calculate when needed
- ❌ No cross-references (strategy_id in execution) - causality provides traceability

### 3.4 Layer Separation

| Layer | DTOs | Concern |
|-------|------|---------|
| Platform | Origin, PlatformDataDTO | Data ingestion |
| Analysis | Signal, Risk | Detection facts (pre-causality) |
| Planning | StrategyDirective, *Plan DTOs | Strategic decisions, tactical plans |
| Execution | ExecutionDirective, ExecutionGroup | Execution instructions, tracking |

### 3.5 Validation Conventions

**ID Formats:** `PREFIX_YYYYMMDD_HHMMSS_hash`

| Prefix | DTO |
|--------|-----|
| `TCK_/NWS_/SCH_` | Origin |
| `SIG_` | Signal |
| `RSK_` | Risk |
| `STR_` | StrategyDirective |
| `TPL_` | TradePlan |
| `ENT_/SIZ_/EXT_/EXP_` | Planning DTOs |
| `EXE_` | ExecutionDirective |
| `BAT_` | ExecutionDirectiveBatch |
| `EXG_` | ExecutionGroup |

**Symbol Format:** `BASE_QUOTE` (e.g., `BTC_USD`, not `BTCUSD` or `BTC/USD`)

**Decimal Ranges:** Trade-offs use 0.0-1.0 normalized scale.

---

## 4. DTO Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ PLATFORM LAYER                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  DataProvider                                                        │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────┐                                                 │
│  │ PlatformDataDTO │ ← Origin (TCK_/NWS_/SCH_)                       │
│  └────────┬────────┘                                                 │
│           │                                                          │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ANALYSIS LAYER                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  SignalDetector        RiskMonitor                                   │
│       │                     │                                        │
│       ▼                     ▼                                        │
│  ┌─────────┐          ┌─────────┐                                    │
│  │ Signal  │          │  Risk   │  ← Pre-causality (detection facts) │
│  └────┬────┘          └────┬────┘                                    │
│       │                    │                                         │
└───────┼────────────────────┼─────────────────────────────────────────┘
        │                    │
        ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PLANNING LAYER                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  StrategyPlanner (combines Signal + Risk + Context)                  │
│       │                                                              │
│       ▼                                                              │
│  ┌───────────────────┐     ┌───────────┐                             │
│  │ StrategyDirective │ ──► │ TradePlan │  ← Causality chain starts   │
│  └────────┬──────────┘     └───────────┘                             │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────────────────────────────────────────┐             │
│  │ Specialized Planners                                 │             │
│  │  EntryPlanner → EntryPlan                           │             │
│  │  SizePlanner  → SizePlan                            │             │
│  │  ExitPlanner  → ExitPlan                            │             │
│  │  RoutingPlanner → ExecutionPlan                     │             │
│  └────────────────────────────┬────────────────────────┘             │
│                               │                                      │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ EXECUTION LAYER                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  PlanningAggregator                                                  │
│       │                                                              │
│       ▼                                                              │
│  ┌────────────────────┐                                              │
│  │ ExecutionDirective │  ← Aggregated execution instruction          │
│  └────────┬───────────┘                                              │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────────────┐                                         │
│  │ ExecutionDirectiveBatch │  ← Atomic coordination (1-N directives) │
│  └────────────┬────────────┘                                         │
│               │                                                      │
│               ▼                                                      │
│  ┌────────────────┐                                                  │
│  │ ExecutionGroup │  ← Multi-order tracking (TWAP, ICEBERG, etc)     │
│  └────────────────┘                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Related Documents

- [DTO Core](DTO_CORE.md) - Platform and infrastructure DTOs
- [DTO Pipeline](DTO_PIPELINE.md) - Analysis and strategic DTOs
- [DTO Execution](DTO_EXECUTION.md) - Planning and execution DTOs
- [Pipeline Flow](PIPELINE_FLOW.md) - Phase sequencing (WHAT happens WHEN)
- [Execution Flow](EXECUTION_FLOW.md) - Sync/async flows + SRP responsibilities
- [Data Flow](DATA_FLOW.md) - DispositionEnvelope patterns

---

## 6. Document Maintenance

**Update triggers:**
- New DTO created (add to taxonomy before implementation)
- DTO category changes (update taxonomy)
- Design principles evolve (document rationale)

**Detailed DTO documentation:** Update in DTO_CORE.md, DTO_PIPELINE.md, or DTO_EXECUTION.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-29 | Team | Initial DTO architecture |
| 1.1 | 2025-11-20 | Team | Added TradePlan DTO |
| 2.0 | 2025-11-29 | AI Assistant | Split into overview + 3 detailed documents, aligned with pipeline phases |
