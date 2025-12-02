# DTO Design Plan Prompt - S1mpleTraderV3

**Doel:** Creëer een gefaseerd plan voor het complete DTO-ontwerp en -implementatie in S1mpleTraderV3.

---

## Gefaseerde Aanpak

### Fase 1: Ontwerp (Design Documents)

**Output:** Eén ontwerpdocument per DTO in `docs/design/dtos/`

Per DTO een document met:
1. **DTO Identity** - Naam, ID prefix, layer, file location
2. **Contract Definition** - Producer(s), Consumer(s), data flow
3. **Field Specification** - Per veld: type, required/optional, producer, consumer, validation
4. **Causality Role** - Pre/post-causality, welke IDs in CausalityChain
5. **Immutability Decision** - frozen=True/False met rationale
6. **Examples** - Concrete JSON voorbeelden
7. **Dependencies** - Welke andere DTOs/enums nodig
8. **Breaking Changes** - Voor bestaande DTOs: wat moet refactored worden

**Naming convention:** `docs/development/backend/dtos/{DTO_NAME}_DESIGN.md`

### Fase 2: Implementatieplan

**Output:** Overkoepelend implementatieplan met:

#### 2A. Refactor Bestaande DTOs
- Prioriteit op basis van breaking change impact
- Per DTO: concrete wijzigingen (field renames, removals, type changes)
- TDD workflow: eerst tests aanpassen, dan implementatie
- Migration checklist

#### 2B. Implementatie Nieuwe DTOs  
- Dependency-volgorde (Order na ExecutionGroup, Fill na Order)
- Per DTO: volledige implementatie specificatie
- TDD workflow: RED → GREEN → REFACTOR
- Test coverage requirements

---

## Authoritative Documents (Leidend!)

De volgende 4 documenten zijn **volledig gerefactored** en bevatten de **definitieve terminologie**:

| Document | Versie | Core Focus |
|----------|--------|------------|
| `WORKER_TAXONOMY.md` | v2.0 | 6 worker categorieën, ExecutionWorker als 6e |
| `PIPELINE_FLOW.md` | v3.0 | 6+1 fase model, Signal/Risk terminologie |
| `EXECUTION_FLOW.md` | v2.0 | Sync/async flows, Ledger vs Journal SRP |
| `TRADE_LIFECYCLE.md` | v2.0 | Container hierarchy, Ledger access patterns |

**Alle terminologie in deze documenten is leidend!** Bij twijfel → raadpleeg deze docs.

---

## Kernprincipes

### Single Responsibility Principle (SRP)

Elk DTO heeft **één verantwoordelijkheid**: het transporteren van precies die data die nodig is voor communicatie tussen twee componenten. 

**DTO = Contract tussen Producer en Consumer**

Een DTO bevat:
- ✅ **Alleen velden die de consumer nodig heeft** om zijn taak uit te voeren
- ✅ **Typed identifiers** voor causality reconstruction (indien journaling vereist)
- ❌ **Geen meta-velden** ("status", "metadata", "context", "info") zonder concrete consumer
- ❌ **Geen duplicatie** van data die al via CausalityChain beschikbaar is
- ❌ **Geen business logic** (berekeningen, aggregaties, beslissingen)

### Lean DTO Design

**Vraag bij elk veld:**
1. Welke worker/component **produceert** dit veld?
2. Welke worker/component **consumeert** dit veld?
3. Wat gebeurt er als dit veld **ontbreekt**? (optioneel vs required)
4. Is dit veld al beschikbaar via **CausalityChain**? (geen duplicatie)

**Red Flags voor over-engineering:**
- `dict[str, Any]` - Ongetypeerde data = undefined contract
- `metadata: dict` - "We weten nog niet wat hier komt"
- `Optional[...]` zonder concrete use case
- Velden die "handig kunnen zijn" maar geen consumer hebben

### Scheiding Causality vs Business Data

**CausalityChain = Pure ID Tracking**
- Bevat ALLEEN IDs (geen timestamps, geen business data)
- Doel: Journal reconstruction ("Waarom bestaat deze order?")
- Immutable chain: workers **extend** via `model_copy(update={...})`

**Business DTOs = Operational Data**
- Bevatten de data die workers nodig hebben om hun taak uit te voeren
- Timestamps, prices, quantities, directions, etc.
- GEEN causality velden (die zitten in CausalityChain)

---

## Taak

### Fase 1: Ontwerpdocumenten Genereren

Voor **elke DTO** in de DTO Taxonomie, creëer een ontwerpdocument:

**Document Structuur:** `docs/development/backend/dtos/{DTO_NAME}_DESIGN.md`

```markdown
# {DTO_NAME} Design Document

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | {Name} |
| **ID Prefix** | {PREFIX_} |
| **Layer** | Platform / Analysis / Strategy / Planning / Execution / State |
| **File Path** | `backend/dtos/{layer}/{name}.py` |
| **Status** | ✅ Implemented / ⚠️ Needs Refactor / ❌ Not Implemented |

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | {WorkerType} |
| **Consumer(s)** | {WorkerType1}, {WorkerType2} |
| **Trigger** | {What causes this DTO to be created} |

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| {field_name} | {type} | ✅/❌ | {who sets} | {who reads} | {rules} |

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Pre-causality / Post-causality |
| **Has causality field** | Yes / No |
| **ID tracked in CausalityChain** | {field_name} by {component} |

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | True / False |
| **Why** | {explanation} |

## 6. Examples

\`\`\`json
{
  "example_field": "value"
}
\`\`\`

## 7. Dependencies

- {OtherDTO}
- {Enum from backend/core/enums.py}

## 8. Breaking Changes (if applicable)

| Current | New | Impact |
|---------|-----|--------|
| {old_field} | {new_field} | {what breaks} |
```

### Fase 2: Implementatieplan Genereren

Creëer één overkoepelend document: `docs/development/backend/dtos/DTO_IMPLEMENTATION_PLAN.md`

**Inhoud:**

#### Part A: Refactor Bestaande DTOs

Per DTO met issues:
1. **Wijzigingen** - Exacte field changes, type changes, removals
2. **Impact Analysis** - Welke files/tests breken
3. **TDD Steps:**
   - Update test expectations EERST
   - Run tests (RED)
   - Implement changes
   - Run tests (GREEN)
   - Refactor if needed
4. **Verification Checklist**

#### Part B: Nieuwe DTOs Implementeren

Per nieuwe DTO:
1. **Prerequisites** - Welke DTOs/enums moeten eerst bestaan
2. **TDD Steps:**
   - Write failing tests EERST (RED)
   - Implement minimal DTO (GREEN)
   - Refactor for quality
3. **Test Coverage Requirements:**
   - Creation tests (required + optional fields)
   - ID validation tests (prefix, format)
   - Field validation tests (ranges, types)
   - Immutability tests (if frozen=True)
   - Serialization tests (JSON round-trip)
4. **Verification Checklist**

---

## Context: Worker → DTO Mapping (Producer/Consumer)

### Authoritative Worker Taxonomy (v2.0)

Per `WORKER_TAXONOMY.md` zijn er **6 worker categorieën**:

| Category | Worker Type | Output DTO | Consumer(s) |
|----------|-------------|------------|-------------|
| **1. Context** | ContextWorker | Plugin-specific DTOs | SignalDetector, RiskMonitor, StrategyPlanner |
| **2. Signal** | SignalDetector | `Signal` | StrategyPlanner (via EventBus) |
| **3. Risk** | RiskMonitor | `Risk` | StrategyPlanner (via EventBus) |
| **4. Planning** | StrategyPlanner | `StrategyDirective` | TradePlanners |
|  | EntryPlanner | `EntryPlan` | ExecutionPlanner |
|  | SizePlanner | `SizePlan` | ExecutionPlanner |
|  | ExitPlanner | `ExitPlan` | ExecutionPlanner |
|  | ExecutionPlanner | `ExecutionCommand` | ExecutionWorker |
| **5. State** | StrategyLedger | `TradePlan`, `ExecutionGroup`, `Order`, `Fill` | Journal, Quant |
|  | StrategyJournal | Read-only causality | Quant Analysis |
| **6. Execution** | ExecutionWorker (TWAP, Iceberg, etc.) | Order/Fill updates | StrategyLedger |

### DTO Taxonomie per Layer (Authoritative)

**Platform Layer** (data ingestion):
1. **Origin** - Platform data source identification (TICK/NEWS/SCHEDULE)
2. **PlatformDataDTO** - Minimal envelope (origin + timestamp + payload)

**Analysis Layer** (detection - pre-causality):
3. **Signal** - SignalDetector output (pattern detected) ⚠️ **GEEN causality veld!**
4. **Risk** - RiskMonitor output (threat detected) ⚠️ **GEEN causality veld!**

**Strategy Layer** (decision - post-causality start):
5. **StrategyDirective** - StrategyPlanner output (what to do + constraints)
   - Contains sub-directives: EntryDirective, SizeDirective, ExitDirective, ExecutionDirective

**Planning Layer** (tactical):
6. **EntryPlan** - EntryPlanner output (WHAT/WHERE to enter)
7. **SizePlan** - SizePlanner output (HOW MUCH)
8. **ExitPlan** - ExitPlanner output (WHERE OUT)
9. **ExecutionPlan** - ExecutionPlanner output (HOW/WHEN trade-offs)

**Execution Layer** (operational):
10. **ExecutionCommand** - ExecutionPlanner aggregated output (4 plans + causality)
11. **ExecutionCommandBatch** - Multi-command coordination

**State Layer** (persistence - Ledger owned):
12. **TradePlan** - Level 1: Trade lifecycle anchor
13. **ExecutionGroup** - Level 2: Atomic execution unit  
14. **Order** - Level 3: Exchange intent
15. **Fill** - Level 4: Execution reality

**Cross-Cutting**:
16. **CausalityChain** - ID-only tracking for journal reconstruction
17. **DispositionEnvelope** - Worker output routing (CONTINUE/PUBLISH/STOP)
18. **StrategyCache** - Point-in-time data container (was TickCache)

---

## Terminologie Standaardisatie (Authoritative Docs)

### Symbol Naming (per PIPELINE_FLOW.md, EXECUTION_FLOW.md)

**Probleem:** Inconsistente naamgeving (`asset`, `symbol`, `affected_asset`)

**Standaard: `symbol`** (trading domain convention)

| DTO | Huidig | Nieuw | Rationale |
|-----|--------|-------|-----------|
| Signal | `asset` | `symbol` | Trading pair identifier |
| Risk | `affected_asset` | `affected_symbol` | None = system-wide risk |
| EntryDirective | `symbol` | `symbol` | ✅ Already correct |
| EntryPlan | `symbol` | `symbol` | ✅ Already correct |

**Format:** Per architectuurdocs is format `BTCUSDT` (geen separator):
- ✅ `BTCUSDT`, `ETHEUR`, `SOLUSDT` (voorbeelden uit docs)
- ⚠️ Huidige DTOs gebruiken slash pattern `^[A-Z0-9_]+/[A-Z0-9_]+$` → **FIX NEEDED**

### Direction Naming (per PIPELINE_FLOW.md)

**Twee contexten:**

| Context | Values | Usage |
|---------|--------|-------|
| **Analysis** (Signal, StrategyDirective) | `"long"`, `"short"` | Strategic intent |
| **Execution** (EntryPlan, Order) | `"BUY"`, `"SELL"` | Exchange operation |

**Mapping door EntryPlanner:** `long` → `BUY`, `short` → `SELL`

### Type Naming Conventions

| Field | Convention | Example |
|-------|------------|---------|
| `signal_type` | UPPER_SNAKE_CASE | `FVG_ENTRY`, `MSS_REVERSAL` |
| `risk_type` | UPPER_SNAKE_CASE | `DRAWDOWN_BREACH`, `STOP_LOSS_HIT` |
| `action` | UPPER_SNAKE_CASE | `EXECUTE_TRADE`, `CANCEL_GROUP` |
| `status` | UPPER_CASE | `ACTIVE`, `CLOSED`, `PENDING` |

### ID Prefix Conventions (per `id_generators.py`)

| DTO | Prefix | Generator Function | Notes |
|-----|--------|-------------------|-------|
| Origin (TICK) | `TCK_` | `generate_tick_id()` | |
| Origin (NEWS) | `NWS_` | `generate_news_id()` | |
| Origin (SCHEDULE) | `SCH_` | `generate_schedule_id()` | |
| Signal | `SIG_` | `generate_signal_id()` | |
| Risk | `RSK_` | `generate_risk_id()` | |
| StrategyDirective | `STR_` | `generate_strategy_directive_id()` | |
| TradePlan | `TPL_` | `generate_trade_plan_id()` | ⚠️ Inconsistent: docs tonen soms `TDP_` |
| EntryPlan | `ENT_` | `generate_entry_plan_id()` | |
| SizePlan | `SIZ_` | `generate_size_plan_id()` | |
| ExitPlan | `EXT_` | `generate_exit_plan_id()` | |
| ExecutionPlan | `EXP_` | `generate_execution_plan_id()` | |
| ExecutionCommand | `EXC_` | `generate_execution_command_id()` | |
| ExecutionGroup | `EXG_` | `generate_execution_group_id()` | |
| ExecutionCommandBatch | `ECB_` | `generate_command_batch_id()` | |
| Order | `ORD_` | (to be added) | |
| Fill | `FIL_` | (to be added) | |

**ID Format:** `{PREFIX}_{YYYYMMDD}_{HHMMSS}_{hash}`

---

## CausalityChain: Strikte Regels (per EXECUTION_FLOW.md)

### Doel van CausalityChain

**Enige doel:** Reconstructie van de beslissingsketen voor StrategyJournal.

Per `EXECUTION_FLOW.md`:
> "StrategyJournal = WHY (causality) - Append-only causality chain"
> "Query pattern: `journal.get_decision_chain(order_id)` → returns full causal chain"

### Wat MOET in CausalityChain?

| ID | Toevoegen door | Waarom nodig voor Journal |
|----|---------------|--------------------------|
| `origin` | FlowInitiator | Birth of decision chain (TICK/NEWS/SCHEDULE) |
| `signal_ids[]` | StrategyPlanner | Welke signals triggerde de decision |
| `risk_ids[]` | StrategyPlanner | Welke risks waren actief |
| `strategy_directive_id` | StrategyPlanner | De strategische beslissing |
| `execution_command_id` | ExecutionPlanner | De execution command |
| `order_ids[]` | ExecutionWorker | Welke orders werden geplaatst |
| `fill_ids[]` | ExecutionWorker | Welke fills volgden |

### Wat HOORT NIET in CausalityChain?

**Intermediate Plan IDs - NIET nodig voor Journal reconstruction:**
- ❌ `entry_plan_id` - Intermediate, niet nodig voor "waarom deze order"
- ❌ `size_plan_id` - Intermediate planning artifact
- ❌ `exit_plan_id` - Intermediate planning artifact
- ❌ `execution_plan_id` - Intermediate planning artifact

**Business Data - NIET in CausalityChain:**
- ❌ Timestamps (elk DTO heeft eigen timestamp)
- ❌ Prices, quantities, directions (business data)
- ❌ Confidence scores (Signal/StrategyDirective hebben die)

### ⚠️ ISSUE: Huidige CausalityChain Implementatie

**Probleem:** `backend/dtos/causality.py` bevat intermediate plan IDs:
```python
entry_plan_id: str | None
size_plan_id: str | None  
exit_plan_id: str | None
execution_plan_id: str | None
```

**Decision:** Review of deze IDs werkelijk nodig zijn voor Journal reconstruction.
- **Argument PRO:** Fijnmazige traceability ("welke planner produceerde wat")
- **Argument CON:** Journal hoeft alleen te weten: Signal → Decision → Order
- **Actie:** Defer tot Journal implementation, documenteer design rationale
### Wie Extend CausalityChain?

| Component | Extends With | When |
|-----------|--------------|------|
| **FlowInitiator** | Creates chain with `origin` | PlatformDataDTO received |
| **StrategyPlanner** | `signal_ids`, `risk_ids`, `strategy_directive_id` | Decision made |
| **ExecutionPlanner** | `execution_directive_id` | Plans aggregated |
| **ExecutionWorker** | `order_ids` | Order placed |
| **ExecutionWorker** | `fill_ids` | Fill received |

### Pattern: Extending CausalityChain

```python
# Worker extends chain via model_copy (immutable pattern)
extended_causality = input_dto.causality.model_copy(update={
    "strategy_directive_id": directive_id
})
output_dto = StrategyDirective(
    causality=extended_causality,
    ...
)
```

---

## Openstaande Issues (TODO.md + DTO Scan Bevindingen)

### CRITICAL - Architectural Violations

1. **Signal DTO: Remove causality field** ⚠️ SCAN CONFIRMED
   - **Locatie:** `backend/dtos/strategy/signal.py` line ~40
   - **Issue:** Signal is pre-causality (pure detection fact), maar heeft `causality` field
   - **Fix:** Verwijder `causality: CausalityChain` field volledig
   - **Impact:** Signal constructor, tests, SignalDetector plugins

2. **Risk DTO: Remove causality field** ⚠️ SCAN CONFIRMED
   - **Locatie:** `backend/dtos/strategy/risk.py` line ~35
   - **Issue:** Risk is pre-causality, maar heeft `causality` field
   - **Fix:** Verwijder `causality` field volledig
   - **Impact:** Risk constructor, tests, RiskMonitor plugins

### HIGH Priority - Terminology Violations

3. **Signal: `asset` → `symbol`** ⚠️ SCAN CONFIRMED
   - **Locatie:** `backend/dtos/strategy/signal.py`
   - **Issue:** Gebruikt `asset` ipv standaard `symbol`
   - **Fix:** Rename field `asset` → `symbol`
   
4. **Risk: `affected_asset` → `affected_symbol`** ⚠️ SCAN CONFIRMED
   - **Locatie:** `backend/dtos/strategy/risk.py`
   - **Issue:** Gebruikt `affected_asset` ipv standaard `affected_symbol`
   - **Fix:** Rename field

5. **Symbol validation pattern mismatch** ⚠️ NEW FINDING
   - **Locatie:** Signal, Risk validation patterns
   - **Huidige pattern:** `^[A-Z0-9_]+/[A-Z0-9_]+$` (slash)
   - **Docs voorbeelden:** `BTCUSDT`, `ETHUSDT` (geen separator)
   - **Fix:** Update pattern naar `^[A-Z][A-Z0-9]{2,}$` of verwijder pattern

6. **ExecutionDirective → ExecutionCommand rename**
   - **Locatie:** `execution/execution_directive.py`
   - **Issue:** Naming conflict met sub-directive in StrategyDirective
   - **Fix:** Rename output DTO `ExecutionDirective` → `ExecutionCommand`
   - **Rationale:** Behoudt `{Role}Directive` patroon voor alle sub-directives, output is imperatief "command"

7. **StrategyDirective: `target_trade_ids` → `target_plan_ids`**
   - **Locatie:** `strategy_directive.py`
   - **Issue:** Field name uses "trade" maar tracked TradePlan IDs
   - **Per TRADE_LIFECYCLE.md:** Level 1 abstraction = TradePlan
   - **Fix:** Rename naar `target_plan_ids`

### MEDIUM Priority - Code Smells

8. **ExecutionGroup: DCA in ExecutionStrategyType** ⚠️ SCAN CONFIRMED
   - **Locatie:** `backend/dtos/execution/execution_group.py`
   - **Issue:** `DCA` is PLANNING concept, niet EXECUTION strategy
   - **Per WORKER_TAXONOMY.md:** ExecutionWorker = TWAP, Iceberg, MarketMaker
   - **Fix:** Verwijder `DCA` uit `ExecutionStrategyType` enum

9. **ExecutionGroup: `metadata: Dict[str, Any]`** ⚠️ SCAN CONFIRMED
   - **Locatie:** `backend/dtos/execution/execution_group.py`
   - **Issue:** Untyped dict = undefined contract, violates lean principle
   - **Fix:** Analyseer usage → type specifieke velden of verwijder

10. **Signal/Risk: `float` voor confidence/severity** ⚠️ NEW FINDING
    - **Locatie:** Signal.confidence, Risk.severity
    - **Issue:** Financiële precisie vereist Decimal
    - **Fix:** `confidence: float` → `confidence: Decimal`

11. **ExecutionDirective examples: oude causality format** ⚠️ NEW FINDING
    - **Locatie:** `execution_directive.py` json_schema_extra examples
    - **Issue:** Examples tonen `tick_id` ipv `origin: {id, type}`
    - **Fix:** Update examples naar Origin format

### LOW Priority - Cleanup

12. **Enums Centralisatie**
    - **Issue:** Enums verspreid over DTOs
    - **Fix:** Centraliseer in `backend/core/enums.py`
    - **Scope:** OriginType, DirectiveScope, ExecutionMode, ExecutionAction, etc.

13. **TickCache → StrategyCache rename**
    - **Per EXECUTION_FLOW.md:** StrategyCache is de correcte naam
    - **Fix:** Rename class en alle references

### PENDING - Design Decisions

14. **CausalityChain intermediate plan IDs**
    - **Question:** Zijn entry_plan_id, size_plan_id, etc. nodig voor Journal?
    - **Status:** Defer tot Journal implementation

15. **TradePlan ID prefix inconsistentie**
    - **Implementatie:** `TPL_` prefix
    - **Sommige docs:** Refereren naar `TDP_`
    - **Fix:** Documenteer definitieve prefix en update indien nodig

---

## Design Guidelines Checklist

### Per DTO verifiëren:

#### 1. SRP & Lean Check
- [ ] Elk veld heeft concrete producer EN consumer
- [ ] Geen `dict[str, Any]` of ongetypeerde metadata
- [ ] Geen duplicatie van CausalityChain data
- [ ] Geen "might be useful" velden

#### 2. Structuur (STRATEGY_DTO_TEMPLATE.md)
- [ ] File header met @layer, @dependencies, @responsibilities
- [ ] 3 import groups met comment headers (Standard, Third-party, Project)
- [ ] Field order: primary_id → timestamp → core fields → optional fields
- [ ] model_config met frozen/validate_assignment/extra="forbid"
- [ ] field_validators waar nodig (ID prefix, UPPER_SNAKE_CASE, ranges)

#### 3. Immutability Beslissing
- [ ] **frozen=True:** Pure data containers (Signal, Risk, Origin, PlatformDataDTO, Plans)
- [ ] **frozen=False:** DTOs die post-creatie worden verrijkt (ExecutionGroup, TradePlan)

#### 4. Causality Rules
- [ ] **Pre-causality DTOs:** Signal, Risk (GEEN causality field)
- [ ] **Post-causality DTOs:** StrategyDirective → ExecutionDirective (HEBBEN causality)
- [ ] Causality extended via `model_copy(update={...})`

#### 5. Terminologie
- [ ] Asset identifier = `symbol` (format: `BASE_QUOTE`)
- [ ] Direction = `"long"` | `"short"` (analysis) of `"BUY"` | `"SELL"` (execution)
- [ ] Types = UPPER_SNAKE_CASE
- [ ] Status = UPPER_CASE
---

## Coding Standards Checklist (CODE_STYLE.md, TDD_WORKFLOW.md)

### Per DTO + Tests verifiëren:

#### Code Quality
- [ ] PEP 8 compliant
- [ ] Full type hinting (geen `Any` behalve waar absoluut nodig)
- [ ] Google-style docstrings
- [ ] Class docstring: one-line summary (uitgebreide docs in header)
- [ ] **Decimal voor financiële waarden** (price, quantity, risk_amount - NIET float)
- [ ] **UTC timestamps** (timezone-aware datetime vereist)

#### TDD Workflow
- [ ] Tests geschreven VOOR implementatie (RED phase)
- [ ] Test coverage voor:
  - Creation tests (required + optional fields)
  - ID validation tests (prefix, format)
  - Timestamp validation tests (UTC, timezone-aware)
  - Field validation tests (ranges, formats, types)
  - Immutability tests (indien frozen=True)
  - Cross-field validation tests (indien van toepassing)
  - Edge cases

#### Test File Structure (DTO_TEST_TEMPLATE.md)
- [ ] pyright suppressions voor Pydantic FieldInfo
- [ ] Test classes per aspect (Creation, Validation, Immutability, etc.)
- [ ] Arrange-Act-Assert pattern
- [ ] Descriptieve test namen

---

## Stap-voor-Stap Analyse-Instructies

### Stap 1: DTO Scan Resultaten (Pre-Analysis)

De volgende DTOs zijn gescand tegen de authoritative docs:

#### ✅ GOOD - Conform Authoritative Docs

| DTO | File | Status | Notes |
|-----|------|--------|-------|
| **Origin** | `shared/origin.py` | ✅ Clean | Lean, typed, correct prefixes |
| **CausalityChain** | `causality.py` | ✅ Good | Uses Origin, correct pattern |
| **DispositionEnvelope** | `shared/disposition_envelope.py` | ✅ Good | Clean flow control |
| **EntryPlan** | `strategy/entry_plan.py` | ✅ Lean | Refactored, no causality |
| **SizePlan** | `strategy/size_plan.py` | ✅ Lean | Pure sizing output |
| **ExitPlan** | `strategy/exit_plan.py` | ✅ Lean | Pure exit levels |
| **ExecutionPlan** | `strategy/execution_plan.py` | ✅ Good | Universal trade-offs |
| **TradePlan** | `strategy/trade_plan.py` | ✅ Minimal | Correct anchor pattern |

#### ⚠️ ISSUES - Requires Fixes

| DTO | File | Issues Found |
|-----|------|--------------|
| **Signal** | `strategy/signal.py` | `causality` field (remove), `asset` (→symbol), slash pattern |
| **Risk** | `strategy/risk.py` | `causality` field (remove), `affected_asset` (→affected_symbol), slash pattern |
| **StrategyDirective** | `strategy/strategy_directive.py` | `ExecutionDirective` class name conflict, `target_trade_ids` naming |
| **ExecutionGroup** | `execution/execution_group.py` | `DCA` in enum, `metadata: Dict[str,Any]` |
| **ExecutionCommand** | `execution/execution_directive.py` → rename to `execution_command.py` | Example uses old `tick_id` format, file rename needed |

#### ❌ MISSING - Not Implemented

| DTO | Expected Location | Notes |
|-----|-------------------|-------|
| **Order** | `state/order.py` | Needed for Ledger |
| **Fill** | `state/fill.py` | Needed for Ledger |
| **StrategyCache** | `core/strategy_cache.py` | Was TickCache - rename |

### Stap 2: Issue → DTO Mapping (Complete)

| Issue # | DTOs Affected | Change Type | Priority |
|---------|---------------|-------------|----------|
| #1 | Signal | Field removal (causality) | CRITICAL |
| #2 | Risk | Field removal (causality) | CRITICAL |
| #3 | Signal | Field rename (asset→symbol) | HIGH |
| #4 | Risk | Field rename (affected_asset→affected_symbol) | HIGH |
| #5 | Signal, Risk | Validation pattern fix | HIGH |
| #6 | ExecutionDirective | Class/file rename (ExecutionDirective→ExecutionCommand) | HIGH |
| #7 | StrategyDirective | Field rename (target_trade_ids→target_plan_ids) | HIGH |
| #8 | ExecutionGroup | Enum value removal (DCA) | MEDIUM |
| #9 | ExecutionGroup | Field removal/typing (metadata) | MEDIUM |
| #10 | Signal, Risk | Type change (float→Decimal) | MEDIUM |
| #11 | ExecutionDirective | Example update (tick_id→origin) | LOW |
| #12 | Multiple | Enum centralization | LOW |
| #13 | TickCache | Class rename (→StrategyCache) | LOW |

### Stap 3: Dependency Graph (Authoritative)

Per TRADE_LIFECYCLE.md Container Hierarchy:

```
Origin (no deps) - Birth of data
  │
  ├── PlatformDataDTO (depends: Origin)
  │
  └── CausalityChain (depends: Origin)
        │
        │  ┌─────────────────────────────────────┐
        │  │ PRE-CAUSALITY (geen causality veld) │
        │  └─────────────────────────────────────┘
        │
        ├── Signal (NO causality - detection fact)
        │     └── signal_id → added to CausalityChain by StrategyPlanner
        │
        ├── Risk (NO causality - detection fact)  
        │     └── risk_id → added to CausalityChain by StrategyPlanner
        │
        │  ┌─────────────────────────────────────┐
        │  │ POST-CAUSALITY (heeft causality)    │
        │  └─────────────────────────────────────┘
        │
        └── StrategyDirective (EERSTE consumer met causality)
              │
              ├── EntryPlan ──┐
              ├── SizePlan ───┼── ExecutionPlanner aggregeert
              ├── ExitPlan ───┤
              └── ExecutionPlan ──┘
                    │
                    └── ExecutionCommand (aggregated plans + causality)
                          │
                          └── ExecutionCommandBatch (optional multi)
                                │
                                │  ┌─────────────────────────────────┐
                                │  │ STATE CONTAINERS (Ledger owned) │
                                │  └─────────────────────────────────┘
                                │
                                └── TradePlan (Level 1: Lifecycle Anchor)
                                      │
                                      └── ExecutionGroup (Level 2: Atomic Unit)
                                            │
                                            └── Order (Level 3: Exchange Intent)
                                                  │
                                                  └── Fill (Level 4: Reality)

DispositionEnvelope (independent - worker flow routing)
StrategyCache (independent - point-in-time data store)
```

### Stap 4: Implementatieplan met Phases
### Stap 4: Implementatieplan met Phases

```markdown
## Phase 1: Critical Architectural Fixes (Issues #1-2)

1. [ ] **Signal DTO - Remove causality** (Issue #1)
   - Remove `causality: CausalityChain` field
   - Update constructor, tests
   - Impact: SignalDetector plugins

2. [ ] **Risk DTO - Remove causality** (Issue #2)
   - Remove `causality: CausalityChain` field
   - Update constructor, tests
   - Impact: RiskMonitor plugins

## Phase 2: Terminology Alignment (Issues #3-7)

3. [ ] **Signal DTO - Terminology** (Issues #3, #5, #10)
   - Rename `asset` → `symbol`
   - Fix validation pattern (remove slash)
   - Change `confidence: float` → `Decimal`
   - Update tests

4. [ ] **Risk DTO - Terminology** (Issues #4, #5, #10)
   - Rename `affected_asset` → `affected_symbol`
   - Fix validation pattern
   - Change `severity: float` → `Decimal`
   - Update tests

5. [ ] **StrategyDirective refactor** (Issue #7)
   - Rename field `target_trade_ids` → `target_plan_ids`
   - Update imports, tests

5b. [ ] **ExecutionDirective → ExecutionCommand** (Issue #6)
   - Rename class `ExecutionDirective` → `ExecutionCommand`
   - Rename file `execution_directive.py` → `execution_command.py`
   - Update ID prefix `EXE_` → `EXC_`
   - Update CausalityChain field `execution_directive_id` → `execution_command_id`
   - Update all imports, tests

## Phase 3: Code Smell Cleanup (Issues #8-11)

6. [ ] **ExecutionGroup cleanup** (Issues #8, #9)
   - Remove `DCA` from `ExecutionStrategyType` enum
   - Analyze `metadata` usage → type or remove
   - Update tests

7. [ ] **ExecutionCommand examples** (Issue #11)
   - Update json_schema_extra examples
   - Change `tick_id` → `origin: {id, type}`

## Phase 4: Infrastructure (Issues #12-13)

8. [ ] **Enums centralization** (Issue #12)
   - Create/expand `backend/core/enums.py`
   - Move: OriginType, DirectiveScope, ExecutionMode, ExecutionAction
   - Update all imports

9. [ ] **TickCache → StrategyCache** (Issue #13)
   - Rename class in `backend/core/strategy_cache.py`
   - Update all references

## Phase 5: Missing DTOs

10. [ ] **Order DTO** (`backend/dtos/state/order.py`)
    - Define based on TRADE_LIFECYCLE.md Level 3
    - Add `generate_order_id()` to id_generators.py

11. [ ] **Fill DTO** (`backend/dtos/state/fill.py`)
    - Define based on TRADE_LIFECYCLE.md Level 4
    - Add `generate_fill_id()` to id_generators.py

## Phase 6: CausalityChain Review

12. [ ] **Review intermediate plan IDs**
    - Decide: keep or remove entry_plan_id, size_plan_id, etc.
    - Document design rationale
```

---

## Verwachte Output

### 1. DTO Status Matrix

| DTO | File | Impl | Tests | SRP | Issues | Priority |
|-----|------|------|-------|-----|--------|----------|
| Origin | ✅ | ✅ Complete | ✅ | ✅ | - | - |
| CausalityChain | ✅ | ✅ Complete | ✅ | ⚠️ | #14 (plan IDs) | LOW |
| DispositionEnvelope | ✅ | ✅ Complete | ✅ | ✅ | - | - |
| Signal | ✅ | ⚠️ Issues | ⚠️ | ❌ | #1,#3,#5,#10 | **CRITICAL** |
| Risk | ✅ | ⚠️ Issues | ⚠️ | ❌ | #2,#4,#5,#10 | **CRITICAL** |
| StrategyDirective | ✅ | ⚠️ Issues | ⚠️ | ⚠️ | #6,#7 | **HIGH** |
| EntryPlan | ✅ | ✅ Lean | ✅ | ✅ | - | - |
| SizePlan | ✅ | ✅ Lean | ✅ | ✅ | - | - |
| ExitPlan | ✅ | ✅ Lean | ✅ | ✅ | - | - |
| ExecutionPlan | ✅ | ✅ Good | ✅ | ✅ | - | - |
| ExecutionCommand | ✅ | ⚠️ Rename needed | ⚠️ | ✅ | #6,#11 | HIGH |
| ExecutionGroup | ✅ | ⚠️ Issues | ⚠️ | ❌ | #8,#9 | MEDIUM |
| TradePlan | ✅ | ✅ Minimal | ✅ | ✅ | - | - |
| Order | ❌ | Not impl | - | - | - | MEDIUM |
| Fill | ❌ | Not impl | - | - | - | MEDIUM |
| StrategyCache | ⚠️ | Rename needed | - | - | #13 | LOW |

### 2. Per-DTO Fix Specifications

```markdown
### Signal - CRITICAL Fixes Required

**Current violations:**
| Field | Issue | Fix |
|-------|-------|-----|
| `causality` | Pre-causality DTO has causality | REMOVE field |
| `asset` | Wrong terminology | RENAME → `symbol` |
| pattern | Uses slash `A/B` | UPDATE → match `BTCUSDT` |
| `confidence` | Uses float | CHANGE → Decimal |

**Files to modify:**
- `backend/dtos/strategy/signal.py`
- `tests/unit/dtos/strategy/test_signal.py`
- All SignalDetector plugin implementations

---

### Risk - CRITICAL Fixes Required

**Current violations:**
| Field | Issue | Fix |
|-------|-------|-----|
| `causality` | Pre-causality DTO has causality | REMOVE field |
| `affected_asset` | Wrong terminology | RENAME → `affected_symbol` |
| pattern | Uses slash | UPDATE pattern |
| `severity` | Uses float | CHANGE → Decimal |

**Files to modify:**
- `backend/dtos/strategy/risk.py`
- `tests/unit/dtos/strategy/test_risk.py`
- All RiskMonitor plugin implementations

---

### StrategyDirective - HIGH Priority Fixes

**Current violations:**
| Issue | Location | Fix |
|-------|----------|-----|
| Class naming conflict | `ExecutionDirective` sub-class | RENAME → `RoutingDirective` |
| Field naming | `target_trade_ids` | RENAME → `target_plan_ids` |

**Files to modify:**
- `backend/dtos/strategy/strategy_directive.py`
- All StrategyPlanner implementations
- Tests
```

### 3. Prioritized Implementation Roadmap

| Phase | Task | Effort | Issues Fixed | Deps |
|-------|------|--------|--------------|------|
| **P1** | Signal architectural fix | 2h | #1,#3,#5,#10 | - |
| **P1** | Risk architectural fix | 2h | #2,#4,#5,#10 | - |
| **P1** | StrategyDirective refactor | 3h | #6,#7 | - |
| **P2** | ExecutionGroup cleanup | 2h | #8,#9 | P1 |
| **P1** | ExecutionCommand rename | 2h | #6 | - |
| **P2** | ExecutionCommand examples | 30m | #11 | P1 |
| **P3** | Enum centralization | 2h | #12 | P1,P2 |
| **P3** | StrategyCache rename | 1h | #13 | - |
| **P4** | Order DTO | 3h | - | - |
| **P4** | Fill DTO | 2h | - | Order |
| **P5** | CausalityChain review | 1h | #14 | P4 |

### 4. New DTO Specifications

```markdown
### Order DTO (Level 3: Exchange Intent)

**File:** `backend/dtos/state/order.py`
**Per:** TRADE_LIFECYCLE.md - Level 3 container
**Producer:** ExecutionWorker
**Consumer:** StrategyLedger, StrategyJournal

**Fields (lean - only what's needed):**
| Field | Type | Required | Producer | Consumer |
|-------|------|----------|----------|----------|
| order_id | str (ORD_) | ✅ | ExecutionWorker | Ledger, Journal |
| parent_group_id | str (EXG_) | ✅ | ExecutionWorker | Ledger |
| connector_order_id | str | ❌ | ExchangeConnector | Ledger (mapping) |
| symbol | str | ✅ | From EntryPlan | Connector |
| side | Literal["BUY","SELL"] | ✅ | From EntryPlan | Connector |
| order_type | Literal[...] | ✅ | From EntryPlan | Connector |
| quantity | Decimal | ✅ | From SizePlan | Connector |
| price | Decimal | ❌ | From EntryPlan | Connector |
| status | OrderStatus | ✅ | Connector | Ledger |
| created_at | datetime | ✅ | ExecutionWorker | Journal |
| updated_at | datetime | ✅ | Connector | Ledger |

**NOT included (per lean principles):**
- ❌ causality - separate concern (CausalityChain tracks order_ids)
- ❌ strategy_id - available via parent_group_id → TradePlan lookup
- ❌ metadata - no concrete consumer

---

### Fill DTO (Level 4: Execution Reality)

**File:** `backend/dtos/state/fill.py`
**Per:** TRADE_LIFECYCLE.md - Level 4 container
**Producer:** ExchangeConnector
**Consumer:** StrategyLedger, StrategyJournal

**Fields:**
| Field | Type | Required | Producer | Consumer |
|-------|------|----------|----------|----------|
| fill_id | str (FIL_) | ✅ | System | Ledger, Journal |
| parent_order_id | str (ORD_) | ✅ | System | Ledger |
| connector_fill_id | str | ❌ | Connector | Ledger (mapping) |
| filled_quantity | Decimal | ✅ | Connector | Ledger |
| fill_price | Decimal | ✅ | Connector | Ledger, Quant |
| commission | Decimal | ❌ | Connector | Quant |
| commission_asset | str | ❌ | Connector | Quant |
| executed_at | datetime | ✅ | Connector | Ledger, Journal |

**Key insight:** Fill is REALITY (wat de exchange daadwerkelijk uitvoerde),
kan afwijken van Order intent (partial fills, price improvement).
```

---

## Referentie Documenten

Bij het uitvoeren van deze analyse, raadpleeg:

### Authoritative Architecture (v2.0/v3.0 - LEIDEND!)

1. **`docs/architecture/WORKER_TAXONOMY.md`** (v2.0)
   - 6 worker categorieën
   - ExecutionWorker als 6e categorie
   - Worker → DTO input/output mapping

2. **`docs/architecture/PIPELINE_FLOW.md`** (v3.0)
   - 6+1 fase model
   - Signal/Risk terminologie
   - Sync vs async flow

3. **`docs/architecture/EXECUTION_FLOW.md`** (v2.0)
   - Sync/async flows
   - StrategyLedger vs StrategyJournal SRP
   - ID propagation pattern

4. **`docs/architecture/TRADE_LIFECYCLE.md`** (v2.0)
   - Container hierarchy (TradePlan → ExecutionGroup → Order → Fill)
   - Ledger access patterns
   - Level 1-4 abstractions

### Coding Standards

5. **`docs/coding_standards/CODE_STYLE.md`**
   - PEP 8, imports, docstrings
   - Decimal voor financiële waarden

6. **`docs/coding_standards/TDD_WORKFLOW.md`**
   - RED → GREEN → REFACTOR

### Templates

7. **`docs/reference/dtos/STRATEGY_DTO_TEMPLATE.md`**
   - Code structure template

8. **`docs/reference/testing/DTO_TEST_TEMPLATE.md`**
   - Test structure template

### Existing Implementations (Reference)

9. **`backend/dtos/shared/origin.py`** - Good example (lean, typed)
10. **`backend/dtos/causality.py`** - CausalityChain pattern
11. **`backend/utils/id_generators.py`** - ID generation functions

### Issues & Technical Debt

12. **`docs/TODO.md`** - Technical Debt section

---

## Belangrijke Opmerkingen

### Architectural Rules

1. **SRP:** Elk DTO = contract tussen 1 producer en N consumers
2. **Lean:** Geen velden zonder concrete consumer
3. **Pre-causality:** Signal, Risk hebben GEEN causality field (detection facts)
4. **Post-causality:** StrategyDirective is eerste DTO met causality
5. **CausalityChain:** ALLEEN IDs voor journal reconstruction

### Terminology (Authoritative)

6. **Symbol:** `symbol` (niet `asset`), format per docs (`BTCUSDT`)
7. **Direction:** `long`/`short` (analysis) vs `BUY`/`SELL` (execution)
8. **ExecutionWorker:** TWAP, Iceberg, MarketMaker (geen DCA)
9. **StrategyCache:** (niet TickCache)

### Technical Standards

10. **Decimal:** Altijd voor financiële waarden (niet float)
11. **Enums:** Centraliseren in `backend/core/enums.py`
12. **ID Prefixes:** Per `id_generators.py` conventions

### Breaking Changes Required

13. **Signal:** Remove causality, rename asset→symbol, float→Decimal
14. **Risk:** Remove causality, rename affected_asset→affected_symbol, float→Decimal
15. **ExecutionDirective → ExecutionCommand:** Rename output DTO, file, ID prefix
16. **ExecutionGroup:** Remove DCA from enum, type or remove metadata

---

## Strikte Implementatieregels

### Code Structure (per CODE_STYLE.md)

```python
# backend/dtos/{layer}/{dto_name}.py
"""
{DTOName} DTO - {One-line description}.

{Extended description of purpose and responsibilities.}

@layer: DTO ({Layer})
@dependencies: [{dependency1}, {dependency2}]
@responsibilities: [{resp1}, {resp2}]
"""

# Standard Library Imports
from datetime import datetime
from decimal import Decimal
from typing import Literal

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.utils.id_generators import generate_{dto}_id
from backend.core.enums import {RelevantEnum}


class {DTOName}(BaseModel):
    """
    {One-line summary - keep docstring minimal, details in header}.
    """

    # === Primary Identity ===
    {dto}_id: str = Field(
        default_factory=generate_{dto}_id,
        description="Unique identifier ({PREFIX}_YYYYMMDD_HHMMSS_hash)"
    )

    # === Core Fields ===
    # ... fields in logical order ...

    # === Optional Fields ===
    # ... optional fields last ...

    model_config = {
        "frozen": True,  # or False with rationale
        "extra": "forbid",
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }

    @field_validator("{field_name}")
    @classmethod
    def validate_{field_name}(cls, v: {type}) -> {type}:
        """Validate {what}."""
        # validation logic
        return v
```

### TDD Workflow (per TDD_WORKFLOW.md)

#### Voor Refactor (bestaande DTOs):

```
1. UPDATE TESTS FIRST
   - Wijzig test expectations naar nieuwe field names/types
   - Voeg nieuwe validation tests toe
   - Verwijder tests voor verwijderde velden

2. RUN TESTS → RED
   - Alle gewijzigde tests moeten FALEN
   - Dit bevestigt dat tests correct zijn aangepast

3. IMPLEMENT CHANGES
   - Pas DTO aan volgens ontwerpdocument
   - Minimale wijzigingen, geen scope creep

4. RUN TESTS → GREEN
   - Alle tests moeten SLAGEN
   - Geen nieuwe warnings/errors

5. REFACTOR (optional)
   - Code cleanup
   - Docstring updates
   - Import organization
```

#### Voor Nieuwe DTOs:

```
1. WRITE FAILING TESTS (RED)
   tests/unit/dtos/{layer}/test_{dto_name}.py
   
   Required test classes:
   - Test{DTOName}Creation
   - Test{DTOName}IdValidation
   - Test{DTOName}FieldValidation
   - Test{DTOName}Immutability (if frozen=True)
   - Test{DTOName}Serialization

2. IMPLEMENT MINIMAL DTO (GREEN)
   - Just enough code to pass tests
   - No gold-plating

3. REFACTOR
   - Add comprehensive docstrings
   - Optimize validators
   - Ensure CODE_STYLE compliance
```

### Test Structure (per DTO_TEST_TEMPLATE.md)

```python
# tests/unit/dtos/{layer}/test_{dto_name}.py
"""Unit tests for {DTOName} DTO."""

# pyright: reportPrivateUsage=false
# pyright: reportUnknownMemberType=false

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from backend.dtos.{layer}.{dto_name} import {DTOName}


class Test{DTOName}Creation:
    """Test {DTOName} instantiation."""

    def test_create_with_required_fields_only(self) -> None:
        """Should create with only required fields."""
        # Arrange
        # Act
        # Assert

    def test_create_with_all_fields(self) -> None:
        """Should create with all fields including optional."""
        pass


class Test{DTOName}IdValidation:
    """Test {dto}_id validation."""

    def test_auto_generates_id_with_correct_prefix(self) -> None:
        """Should auto-generate ID with {PREFIX}_ prefix."""
        pass

    def test_rejects_invalid_id_format(self) -> None:
        """Should reject ID without correct prefix."""
        pass


class Test{DTOName}FieldValidation:
    """Test field-specific validation."""

    def test_{field}_accepts_valid_value(self) -> None:
        pass

    def test_{field}_rejects_invalid_value(self) -> None:
        pass


class Test{DTOName}Immutability:
    """Test frozen behavior (if applicable)."""

    def test_cannot_modify_after_creation(self) -> None:
        """Should raise error when modifying frozen instance."""
        pass


class Test{DTOName}Serialization:
    """Test JSON serialization round-trip."""

    def test_serializes_to_json(self) -> None:
        pass

    def test_deserializes_from_json(self) -> None:
        pass
```

### Verification Checklist

Per DTO afvinken voor completion:

```markdown
## {DTOName} Verification

### Design Document
- [ ] `docs/development/backend/dtos/{DTO_NAME}_DESIGN.md` created
- [ ] All 8 sections completed
- [ ] Reviewed against authoritative docs

### Implementation
- [ ] File created: `backend/dtos/{layer}/{dto_name}.py`
- [ ] Follows CODE_STYLE.md structure
- [ ] All fields match design document
- [ ] Validators implemented
- [ ] model_config correct

### Tests
- [ ] Test file: `tests/unit/dtos/{layer}/test_{dto_name}.py`
- [ ] Creation tests pass
- [ ] ID validation tests pass
- [ ] Field validation tests pass
- [ ] Immutability tests pass (if frozen)
- [ ] Serialization tests pass

### Integration
- [ ] Added to `backend/dtos/{layer}/__init__.py`
- [ ] ID generator added to `backend/utils/id_generators.py`
- [ ] Enum added to `backend/core/enums.py` (if applicable)
- [ ] No import errors in dependent modules

### Quality Gates
- [ ] `pytest tests/unit/dtos/{layer}/test_{dto_name}.py` - ALL PASS
- [ ] `pyright backend/dtos/{layer}/{dto_name}.py` - No errors
- [ ] `ruff check backend/dtos/{layer}/{dto_name}.py` - No errors
```

---

## Verwachte Output Structuur

### Fase 1 Output: Design Documents

```
docs/development/backend/dtos/
├── ORIGIN_DESIGN.md
├── PLATFORM_DATA_DTO_DESIGN.md
├── CAUSALITY_CHAIN_DESIGN.md
├── SIGNAL_DESIGN.md
├── RISK_DESIGN.md
├── STRATEGY_DIRECTIVE_DESIGN.md
├── ENTRY_PLAN_DESIGN.md
├── SIZE_PLAN_DESIGN.md
├── EXIT_PLAN_DESIGN.md
├── EXECUTION_PLAN_DESIGN.md
├── EXECUTION_COMMAND_DESIGN.md
├── EXECUTION_COMMAND_BATCH_DESIGN.md
├── EXECUTION_GROUP_DESIGN.md
├── TRADE_PLAN_DESIGN.md
├── ORDER_DESIGN.md
├── FILL_DESIGN.md
├── DISPOSITION_ENVELOPE_DESIGN.md
└── STRATEGY_CACHE_DESIGN.md
```

### Fase 2 Output: Implementation Plan

```
docs/development/backend/dtos/
└── DTO_IMPLEMENTATION_PLAN.md
    ├── Part A: Refactor Schedule
    │   ├── Phase 1: Critical (Signal, Risk)
    │   ├── Phase 2: High (StrategyDirective, ExecutionCommand)
    │   ├── Phase 3: Medium (ExecutionGroup)
    │   └── Phase 4: Low (cleanup, renames)
    │
    └── Part B: New Implementation Schedule
        ├── Phase 5: State DTOs (Order, Fill)
        └── Phase 6: Infrastructure (enums, cache)
```

---

*Prompt Version: 4.0*  
*Created: 2025-12-01*  
*Updated: 2025-12-01*
*Changes v4.0:*
- *Gefaseerde aanpak: Ontwerp → Implementatie*
- *Per-DTO design document template toegevoegd*
- *Strikte implementatieregels uit CODE_STYLE.md*
- *TDD workflow stappen gedetailleerd*
- *Test structure template toegevoegd*
- *Verification checklist per DTO*
- *Verwachte output structuur gedefinieerd*