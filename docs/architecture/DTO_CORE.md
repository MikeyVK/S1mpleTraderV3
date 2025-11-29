# docs/architecture/DTO_CORE.md
# DTO Core - S1mpleTraderV3

**Status:** PRELIMINARY
**Version:** 1.0
**Last Updated:** 2025-11-29---

## 1. Purpose

This document defines the **platform and infrastructure DTOs** that form the foundation of data flow.

**Covered DTOs:**
- **Origin** - Type-safe platform data source identification
- **PlatformDataDTO** - Minimal envelope for platform data ingestion
- **CausalityChain** - ID-only causality tracking
- **DispositionEnvelope** - Worker output routing control

**Related:** See [DTO_ARCHITECTURE.md](DTO_ARCHITECTURE.md) for the complete DTO taxonomy and design principles.

---

## 2. Platform DTOs

### Origin

**Purpose:** Type-safe platform data source identification

**WHY this DTO exists:**
- Platform data arrives from fundamentally different sources (TICK/NEWS/SCHEDULE/ETC)
- Each source has distinct characteristics requiring different handling
- Type-safe discrimination prevents category errors (treating news as tick data)
- Immutable origin provides audit trail foundation
- Prefix validation (TCK_/NWS_/SCH_) enforces ID discipline

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | DataProvider | Creates Origin from exchange ticks, news feeds, or scheduler events |
| **Consumers** | PlatformDataDTO | Embeds origin for envelope routing |
| | CausalityChain | Foundation for causal ID chain (origin → signal_id → ...) |
| | FlowInitiator | Validates origin type matches payload structure |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `id` | str | Yes | Unique identifier with source-specific prefix (TCK_/NWS_/SCH_). Enables unambiguous origin reference throughout pipeline. |
| `type` | OriginType | Yes | Discriminator enum (TICK/NEWS/SCHEDULE). Enables type-safe routing without string parsing. |

**WHY frozen:** Origin is immutable fact - platform data source cannot retroactively change.

**WHY NOT included:**
- ❌ `timestamp` - Belongs to PlatformDataDTO (origin is timeless identifier)
- ❌ `metadata` - Origin is pure identity, not enrichment
- ❌ `priority` - Scheduling concern, not identity concern

**Lifecycle:**
```
Created:    DataProvider (from exchange/scheduler/news feed)
Copied:     FlowInitiator → PlatformDataDTO → CausalityChain
Propagated: Through entire pipeline via CausalityChain
Persisted:  StrategyJournal (causality reconstruction)
Never:      Modified (frozen model)
```

---

### PlatformDataDTO

**Purpose:** Minimal envelope for heterogeneous platform data ingestion

**WHY this DTO exists:**
- Platform data arrives in vastly different shapes (CandleWindow, NewsEvent, ScheduleEvent, etc.)
- Need uniform interface for FlowInitiator without coupling to payload structure
- Separates "envelope" concern (routing metadata) from "payload" concern (actual data) - SRP
- Point-in-time model enforcement (every data snapshot has explicit timestamp)

**Producer/Consumer:**

| Role | Component | Purpose |
|------|-----------|---------|
| **Producer** | DataProvider | Wraps platform-specific payloads with origin + timestamp |
| **Consumers** | FlowInitiator | Unwraps envelope, validates origin, stores payload in StrategyCache |
| | CausalityChain | Copies origin field as causal chain foundation |

**Field Rationale:**

| Field | Type | Required | WHY it exists |
|-------|------|----------|---------------|
| `origin` | Origin | Yes | Platform source discrimination. Type-safe origin tracking. |
| `timestamp` | datetime | Yes | Point-in-time anchor. ALL strategy decisions reference THIS moment. UTC-enforced. |
| `payload` | BaseModel | Yes | Actual platform data (CandleWindow, NewsEvent, etc). Plugin-specific structure. |

**WHY frozen:** Platform data is immutable snapshot of reality at specific moment.

**WHY NOT included:**
- ❌ `source_type: str` - String-based type lacks compiler enforcement
- ❌ `strategy_id` - Routing concern (handled by EventAdapter)
- ❌ `metadata: dict` - Belongs in payload (SRP violation)

**Lifecycle:**
```
Created:    DataProvider (wraps platform-specific data)
Validated:  FlowInitiator (timestamp check, origin validation)
Consumed:   FlowInitiator (unwraps payload → stores in StrategyCache)
Propagated: Origin field copied to CausalityChain
Discarded:  After FlowInitiator completes (envelope purpose fulfilled)
```

---

## 3. Infrastructure DTOs

### CausalityChain

**Purpose:** ID-only causality tracking from origin through execution

**WHY this DTO exists:**
- Every execution must trace back to origin (audit trail, debugging, regulatory)
- Lightweight ID-only chain (no payload duplication)
- Enables "WHY this decision?" reconstruction
- Foundation for StrategyJournal event correlation

**Structure:**

```python
@dataclass
class CausalityChain:
    origin_id: str              # TCK_/NWS_/SCH_ prefix
    signal_ids: List[str]       # SIG_ prefix (0-N signals)
    risk_ids: List[str]         # RSK_ prefix (0-N risks)
    strategy_directive_id: str  # STR_ prefix
    plan_id: str | None         # TPL_ prefix (optional)
```

**WHY these fields:**

| Field | WHY it exists |
|-------|---------------|
| `origin_id` | Traces back to platform data source |
| `signal_ids` | Which signals triggered this decision (can be multiple) |
| `risk_ids` | Which risks influenced this decision (can be multiple) |
| `strategy_directive_id` | The planning decision point |
| `plan_id` | Links to TradePlan execution anchor (optional) |

**Chain Formation:**

```
1. FlowInitiator receives PlatformDataDTO
   → CausalityChain.origin_id = origin.id

2. SignalDetector emits Signal
   → Signal.signal_id recorded (not in chain yet - pre-causality)

3. RiskMonitor emits Risk  
   → Risk.risk_id recorded (not in chain yet - pre-causality)

4. StrategyPlanner makes decision
   → Creates CausalityChain with:
     - origin_id (from context)
     - signal_ids (signals that triggered decision)
     - risk_ids (risks that influenced decision)
     - strategy_directive_id (new directive ID)

5. Downstream propagation
   → ExecutionDirective receives same CausalityChain
   → All orders traceable to origin
```

**Design Decisions:**
- **Decision 1:** Lists for signal_ids/risk_ids
  - Rationale: Multiple signals/risks may contribute to single decision
  
- **Decision 2:** ID-only (no embedded objects)
  - Rationale: Lightweight, avoids payload duplication, enables lazy loading

- **Decision 3:** Frozen after creation
  - Rationale: Causality is immutable fact, cannot retroactively change

---

### DispositionEnvelope

**Purpose:** Worker output routing control

**WHY this DTO exists:**
- Workers need standardized way to signal outcome to pipeline
- Three dispositions: CONTINUE (pass data), PUBLISH (emit event), STOP (halt pipeline)
- Decouples worker logic from event bus mechanics
- Enables testable worker outputs

**Structure:**

```python
@dataclass
class DispositionEnvelope:
    disposition: Disposition    # CONTINUE, PUBLISH, STOP
    payload: BaseModel | None   # Optional DTO to pass/publish
    event_name: str | None      # Event name for PUBLISH disposition
    reason: str | None          # Reason for STOP disposition
```

**Disposition Semantics:**

| Disposition | Payload | Event Name | Behavior |
|-------------|---------|------------|----------|
| `CONTINUE` | DTO to pass | None | Pass data to next worker in wiring |
| `PUBLISH` | DTO to publish | Required | Emit event to EventBus |
| `STOP` | None | None | Halt pipeline (reason logged) |

**Usage Example:**

```python
class SignalDetector(StandardWorker):
    def on_market_trigger(self, candle: CandleCloseEvent) -> DispositionEnvelope:
        signal = self._detect_pattern(candle)
        
        if signal:
            return DispositionEnvelope(
                disposition=Disposition.PUBLISH,
                payload=signal,
                event_name="SIGNAL_DETECTED"
            )
        else:
            return DispositionEnvelope(
                disposition=Disposition.CONTINUE,
                payload=None  # No signal, continue pipeline
            )
```

**Design Decisions:**
- **Decision 1:** Enum-based disposition
  - Rationale: Type-safe, clear semantics, exhaustive switch handling

- **Decision 2:** Optional payload
  - Rationale: STOP disposition doesn't need payload, CONTINUE may be no-op

- **Decision 3:** event_name only for PUBLISH
  - Rationale: Other dispositions don't emit events

---

## 4. Validation Conventions

### ID Formats

All IDs follow pattern: `PREFIX_YYYYMMDD_HHMMSS_hash`

| Prefix | DTO | Example |
|--------|-----|---------|
| `TCK_` | Origin (tick) | `TCK_20251129_143052_a1b2c` |
| `NWS_` | Origin (news) | `NWS_20251129_090000_x9y8z` |
| `SCH_` | Origin (schedule) | `SCH_20251129_000000_daily` |

### Symbol Format

All symbols: `BASE_QUOTE` format

- ✅ `BTC_USD`, `ETH_USDT`, `SOL_EUR`
- ❌ `BTCUSD`, `BTC/USD`, `btc-usd`

### Timestamp Convention

All timestamps: UTC, timezone-aware

```python
from datetime import datetime, timezone

# Correct
timestamp = datetime.now(timezone.utc)

# Incorrect
timestamp = datetime.now()  # Naive datetime
```

---

## 5. Related Documents

- [DTO Architecture](DTO_ARCHITECTURE.md) - Overview and design principles
- [DTO Pipeline](DTO_PIPELINE.md) - Analysis and strategic DTOs
- [DTO Execution](DTO_EXECUTION.md) - Planning and execution DTOs
- [Data Flow](DATA_FLOW.md) - DispositionEnvelope patterns
- [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md) - EventBus integration

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-29 | AI Assistant | Split from DTO_ARCHITECTURE.md |
