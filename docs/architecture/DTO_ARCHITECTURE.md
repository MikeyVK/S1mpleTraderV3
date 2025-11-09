# DTO Architecture - S1mpleTraderV3

**Status:** Architectural Foundation  
**Last Updated:** 2025-11-09  
**Version:** 1.0

---

## Executive Summary

This document describes **WHY each DTO exists** and **WHY each field exists**.

**Purpose:**
- Pure architectural rationale (no code, no examples)
- Field-level justification for every DTO
- Lifecycle tracking (Created → Consumed → Persisted/Discarded)
- Design decision documentation

**This document does NOT contain:**
- Code examples
- Implementation details
- Usage patterns (see WORKER_DATA_ACCESS.md)
- Pipeline sequencing (see PIPELINE_FLOW.md)

**Cross-references:**
- [PIPELINE_FLOW.md](PIPELINE_FLOW.md) - Phase sequencing (WHAT happens WHEN)
- [EXECUTION_FLOW.md](EXECUTION_FLOW.md) - Sync/async flows + SRP responsibilities
- [WORKER_DATA_ACCESS.md](WORKER_DATA_ACCESS.md) - Data access patterns

---

## DTO Taxonomy

### Platform DTOs (Origin Tracking & Data Ingestion)
1. **Origin** - Type-safe platform data source identification
2. **PlatformDataDTO** - Minimal envelope for platform data ingestion

### Analysis DTOs (Detection → Decision)
3. **Signal** - Trading opportunity detection output
4. **Risk** - Threat/risk detection output  
5. **StrategyDirective** - Strategy planning decision output

### Planning DTOs (Decision → Execution Intent)
6. **EntryPlan** - Entry execution specifications
7. **SizePlan** - Position sizing specifications
8. **ExitPlan** - Exit/stop-loss specifications
9. **ExecutionPlan** - Execution trade-offs (urgency, slippage, visibility)

### Execution DTOs (Orders & Coordination)
10. **ExecutionDirective** - Aggregated execution instruction
11. **ExecutionDirectiveBatch** - Multi-directive atomic coordination
12. **ExecutionGroup** - Multi-order relationship tracking

### Cross-Cutting DTOs (Infrastructure)
13. **CausalityChain** - ID-only causality tracking
14. **DispositionEnvelope** - Worker output routing control

---

## Platform DTOs

### Origin

**Purpose:** Type-safe platform data source identification

**WHY this DTO exists:**
- Platform data arrives from fundamentally different sources (TICK/NEWS/SCHEDULE/ETC)
- Each source has distinct characteristics requiring different handling:
  - TICK: Real-time market data (high frequency, time-sensitive)
  - NEWS: Event-driven data (irregular, context-rich)
  - SCHEDULE: Time-triggered data (predictable, no external dependency)
- Type-safe discrimination prevents category errors (treating news as tick data)
- Immutable origin provides audit trail foundation
- Prefix validation (TCK_/NWS_/SCH_) enforces ID discipline

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `id` | str | Yes | Unique identifier with source-specific prefix (TCK_/NWS_/SCH_). Enables unambiguous origin reference throughout pipeline. Validated format prevents ID pollution. |
| `type` | OriginType | Yes | Discriminator enum (TICK/NEWS/SCHEDULE). Enables type-safe routing without string parsing. Compiler-enforced correctness. |

**WHY frozen:**
- Origin is immutable fact - platform data source cannot retroactively change
- Prevents accidental modification during pipeline flow
- Enables safe sharing across workers without defensive copying
- Causality chain integrity depends on immutable origin reference

**WHY NOT included:**
- ❌ `timestamp` - Belongs to PlatformDataDTO (origin is timeless identifier, not point-in-time)
- ❌ `metadata` - Origin is pure identity, not enrichment (metadata belongs in payload)
- ❌ `priority` - Scheduling concern, not identity concern

**Lifecycle:**
```
Created:    DataProvider (from exchange/scheduler/news feed)
Copied:     FlowInitiator → PlatformDataDTO → CausalityChain
Propagated: Through entire pipeline via CausalityChain
Persisted:  StrategyJournal (causality reconstruction)
Never:      Modified (frozen model)
```

**Design Decisions:**
- **Decision 1:** Enum over string for `type`
  - Rationale: Compiler-enforced correctness, no typos, IDE autocomplete
  - Alternative rejected: String literals (error-prone, no type safety)
  
- **Decision 2:** Prefix validation in ID
  - Rationale: Self-documenting IDs, prevents ID pollution, enables visual debugging
  - Alternative rejected: Separate prefix field (redundant with type enum)

- **Decision 3:** Frozen model
  - Rationale: Origin is immutable fact, prevents accidental mutation
  - Alternative rejected: Mutable (breaks causality chain integrity)

---

### PlatformDataDTO

**Purpose:** Minimal envelope for heterogeneous platform data ingestion

**WHY this DTO exists:**
- Platform data arrives in vastly different shapes (CandleWindow, NewsEvent, ScheduleEvent, etc.)
- Need uniform interface for FlowInitiator without coupling to payload structure
- Separates "envelope" concern (routing metadata) from "payload" concern (actual data) - SRP
- Enables type-safe routing based on origin WITHOUT payload inspection
- Minimal coupling principle (only 3 fields - KISS)
- Point-in-time model enforcement (every data snapshot has explicit timestamp)

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `origin` | Origin | Yes | Platform source discrimination. Enables FlowInitiator to route/validate without inspecting payload. Type-safe origin tracking prevents category errors. |
| `timestamp` | datetime | Yes | Point-in-time anchor. ALL strategy decisions reference THIS moment. RunAnchor foundation. Enables tick boundary detection and stale data prevention. UTC-enforced for consistency. |
| `payload` | BaseModel | Yes | Actual platform data (CandleWindow, NewsEvent, etc). Plugin-specific structure. FlowInitiator stores in StrategyCache without interpretation. Type remains abstract (loose coupling). |

**WHY frozen:**
- Platform data is immutable snapshot of reality at specific moment
- Cannot change after creation (data integrity principle)
- Prevents accidental mutation during pipeline flow
- Payload immutability cascades (payload DTOs should also be frozen)

**WHY NOT included:**
- ❌ `source_type: str` - String-based type identification lacks compiler enforcement, error-prone
- ❌ `payload_type: Type` - Python type system handles this (unnecessary runtime metadata)
- ❌ `metadata: dict` - Belongs in payload, not envelope (SRP violation)
- ❌ `strategy_id` - Routing concern, not data concern (handled by EventAdapter)
- ❌ `validation_status` - Processing concern, not data concern (handle via exceptions)

**Lifecycle:**
```
Created:    DataProvider (wraps platform-specific data from exchange/scheduler/news)
Validated:  FlowInitiator (timestamp check, origin validation)
Consumed:   FlowInitiator (unwraps payload → stores in StrategyCache)
Propagated: Origin field copied to CausalityChain
Discarded:  After FlowInitiator completes (envelope purpose fulfilled)
Never:      Stored long-term (only payload persists in StrategyCache)
```

**Design Decisions:**
- **Decision 1:** Origin over source_type string
  - Rationale: Type safety, compiler-enforced correctness, no string parsing
  - Alternative rejected: `source_type: str` (error-prone, lacks type safety)
  
- **Decision 2:** Abstract BaseModel payload
  - Rationale: Loose coupling - FlowInitiator doesn't need payload knowledge
  - Alternative rejected: Generic[T] (unnecessary complexity, runtime type erasure anyway)

- **Decision 3:** Three fields only (minimalism)
  - Rationale: KISS principle, SRP (envelope ≠ payload), reduce coupling surface
  - Alternative rejected: Rich envelope with metadata (violates SRP, tight coupling)

- **Decision 4:** Frozen model
  - Rationale: Immutable snapshots, data integrity, safe concurrent access
  - Alternative rejected: Mutable (breaks point-in-time model guarantees)

**Validation Strategy:**
- Origin ID prefix matches origin type (TCK_ for TICK, etc.)
- Timestamp is timezone-aware (UTC enforced)
- Payload is frozen BaseModel subclass (immutability cascade)
- No cross-field business validation (payload responsibility)

---

## Analysis DTOs

**Status:** TODO - Next section to document

Planned coverage:
- Signal (opportunity detection)
- Risk (threat detection)
- StrategyDirective (planning decision)

---

## Planning DTOs

**Status:** TODO

Planned coverage:
- EntryPlan
- SizePlan
- ExitPlan
- ExecutionPlan

---

## Execution DTOs

**Status:** TODO

Planned coverage:
- ExecutionDirective
- ExecutionDirectiveBatch
- ExecutionGroup

---

## Cross-Cutting DTOs

**Status:** TODO

Planned coverage:
- CausalityChain (ID-only tracking)
- DispositionEnvelope (worker routing)

---

## Appendix A: Rejected DTO Designs

### ExecutionRequest (Rejected - Terminologie Conflict)

**Proposed:** Aggregation DTO for ExecutionIntentPlanner input

**WHY rejected:**
- Term "trade_id" incorrectly implied runtime tracking unit
- "Trade" is post-hoc quant analysis concept, NOT runtime entity
- Tracking unit is actually StrategyDirective → order_ids (via CausalityChain)
- One StrategyDirective can result in 0, 1, or N orders (not 1:1 mapping)
- **Resolution pending:** Architectural clarity needed on directive → order relationship

**Lessons learned:**
- Avoid terms that blur runtime vs analysis boundaries
- Question every field name for conceptual accuracy
- "Trade" = quant concept (orders grouped post-hoc), NOT runtime ID

---

## Document Maintenance

**Update triggers:**
- New DTO created (add rationale before implementation)
- Field added/removed from existing DTO (update rationale)
- Design decision changes (document old vs new rationale)
- Architecture discussions resolve ambiguity (capture in "WHY NOT included")

**Responsible:** Development Team  
**Review frequency:** Per DTO change (living document)

