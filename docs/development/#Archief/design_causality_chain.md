# CausalityChain - Definitief Conceptueel Ontwerp

**Status:** READY FOR IMPLEMENTATION  
**Datum:** 2025-10-26  
**Auteur:** AI Assistant + User Review

**ID Format Convention:**  
Alle IDs gebruiken **uniform military datetime format**: `PREFIX_YYYYMMDD_HHMMSS_hash`

**Voorbeelden:**
- `TCK_20251026_100000_a1b2c3d4` (tick birth)
- `OPP_20251026_100001_def5e6f7` (opportunity signal)
- `STR_20251026_100002_abc1d2e3` (strategy directive)

---

## 0. KERN PRINCIPE: Single Responsibility

**ENIGE VERANTWOORDELIJKHEID:**  
Verzamel **ALLEEN IDs** voor Journal causality reconstruction in FlowTerminator.

**GEEN verantwoordelijkheid voor:**
- ❌ Business data (symbol, price, direction, etc.)
- ❌ Timestamps (elke DTO heeft eigen timestamp)
- ❌ Confidence scores (OpportunitySignal/StrategyDirective hebben dat)
- ❌ Event details (ThreatSignal/ThreatSignal hebben metadata)
- ❌ Tick data (Position/Trade hebben price info)
- ❌ Strategy ID (StrategyDirective heeft dat)

**PRINCIPE:** Als het in een ander DTO zit, hoort het NIET in CausalityChain.

---

## 1. Architecturale Positie

CausalityChain is een **ID-only container** die door de pipeline vloeit:

```
[OpportunityWorker] → OpportunitySignal
    ↓ (adds opportunity_signal_ids to chain)
[StrategyPlanner] → StrategyDirective  
    ↓ (adds strategy_directive_id to chain)
[EntryPlanner] → EntryPlan
    ↓ (adds entry_plan_id to chain)
[SizePlanner] → SizePlan
    ↓ (adds size_plan_id to chain)
[ExitPlanner] → ExitPlan
    ↓ (adds exit_plan_id to chain)
[RoutingPlanner] → RoutingPlan
    ↓ (adds routing_plan_id to chain)
[DirectiveAssembler] → ExecutionDirective
    ↓ (adds execution_directive_id to chain)
[FlowTerminator] → **USES IDs to query Journal**
```

### FlowTerminator Usage (ENIGE CONSUMER)

```python
def on_flow_stop(self, execution_directive: ExecutionDirective):
    chain = execution_directive.causality
    
    # Journal reconstruction via IDs
    opportunity = journal.get(chain.opportunity_signal_ids[0])  # → OpportunitySignal
    directive = journal.get(chain.strategy_directive_id)        # → StrategyDirective
    entry_plan = journal.get(chain.entry_plan_id)               # → EntryPlan
    
    # Write causality chain
    journal.write_chain([
        chain.tick_id,  # Birth
        opportunity.opportunity_signal_id,
        directive.strategy_directive_id,
        entry_plan.entry_plan_id,
        ...
    ])
```

---

## 2. Strategy Run "Geboorte" Concept

Elke strategy run **"wordt geboren"** bij één van de drie gebeurtenissen:

### 2.1 Geboorte Gebeurtenissen

**Market Tick Birth:**
```python
# SignalGenerator produceert OpportunitySignal
causality = CausalityChain(
    tick_id="TCK_20251026_100000_a1b2c3d4",  # ← Birth ID
    news_id=None,
    schedule_id=None
)
```

**News Event Birth:**
```python
# News-driven strategy
causality = CausalityChain(
    tick_id=None,
    news_id="NWS_20251026_100000_b2c3d4e5",  # ← Birth ID
    schedule_id=None
)
```

**Schedule Event Birth:**
```python
# DCA/Rebalancing strategy
causality = CausalityChain(
    tick_id=None,
    news_id=None,
    schedule_id="SCH_20251026_100000_abc1d2e3"  # ← Birth ID
)
```

### 2.2 Geboorte ID Format - UNIFORM

**✅ CORRECT:** Military datetime format met hash
- Format: `PREFIX_YYYYMMDD_HHMMSS_8charhash`
- Voorbeeld: `SCH_20251026_100000_abc1d2e3`
- Voordelen:
  - Temporeel sorteerbaar
  - Menselijk leesbaar (timestamp direct zichtbaar)
  - Uniform voor alle ID types

**❌ FOUT:** Business data in ID
  - ❌ NIET: `SCH_WEEKLY_MONDAY_1000` (trigger info in ID)
  - ❌ NIET: `TCK_BTCUSD_45000` (symbol/price in ID)

**Geboorte details** (weekly, Monday, 10:00) horen in **ScheduleEvent DTO**, NIET in ID.

### 2.3 Validatie: Minstens 1 Geboorte ID Vereist

```python
@model_validator(mode='after')
def validate_birth_id(self) -> 'CausalityChain':
    """At least one birth ID required."""
    if not any([self.tick_id, self.news_id, self.schedule_id]):
        raise ValueError(
            "CausalityChain requires at least one birth ID "
            "(tick_id, news_id, or schedule_id)"
        )
    return self
```

---

## 3. Definitieve Field Lijst

### 3.1 Birth IDs (Geboorte Gebeurtenissen)

```python
tick_id: str | None = Field(
    default=None,
    description="Market tick ID - strategy run geboren bij market data event"
)
news_id: str | None = Field(
    default=None,
    description="News event ID - strategy run geboren bij news event"
)
schedule_id: str | None = Field(
    default=None,
    description="Schedule event ID - strategy run geboren bij DCA/rebalancing schedule"
)
```

**Validatie:** Minstens 1 van de 3 birth IDs moet ingevuld zijn (via Pydantic validator).

### 3.2 Worker Output IDs (Toegevoegd tijdens pipeline flow)

```python
opportunity_signal_ids: list[str] = Field(
    default_factory=list,
    description="OpportunitySignal IDs - multiple signals mogelijk"
)
threat_ids: list[str] = Field(
    default_factory=list,
    description="ThreatSignal IDs (ThreatSignal = ThreatSignal in causality)"
)
context_assessment_id: str | None = Field(
    default=None,
    description="AggregatedContextAssessment ID (SWOT context)"
)
strategy_directive_id: str | None = Field(
    default=None,
    description="StrategyDirective ID - SWOT planning bridge"
)
entry_plan_id: str | None = Field(
    default=None,
    description="EntryPlan ID - entry execution plan"
)
size_plan_id: str | None = Field(
    default=None,
    description="SizePlan ID - position sizing plan"
)
exit_plan_id: str | None = Field(
    default=None,
    description="ExitPlan ID - exit/stop management plan"
)
routing_plan_id: str | None = Field(
    default=None,
    description="RoutingPlan ID - broker routing plan"
)
execution_directive_id: str | None = Field(
    default=None,
    description="ExecutionDirective ID - final execution command"
)
```

**Type Safety:**
- ✅ `opportunity_signal_ids: list[str]` - Meerdere signals mogelijk
- ✅ Alle andere IDs: `str | None` - Enkele ID per worker output
- ✅ Birth IDs: `str | None` - Validator eist minstens 1

---

## 4. Immutability & Flow Pattern

### 4.1 Worker Responsibility - Auto-Propagation

**BaseWorker boilerplate** (plugin developers ONBEWUST):

```python
class BaseWorker(ABC):
    def _process(self, input_dto: WorkerInput) -> WorkerOutput:
        # 1. Extract causality from input DTO
        causality = input_dto.causality
        
        # 2. Worker-specific logic (plugin developer schrijft dit)
        output_dto = self.process(input_dto)
        
        # 3. Auto-copy + extend causality met worker output ID
        extended_causality = causality.model_copy(update={
            "strategy_directive_id": output_dto.strategy_directive_id
        })
        
        # 4. Auto-propagate naar output DTO
        output_dto.causality = extended_causality
        
        return output_dto
```

**Plugin developer code** (GEEN causality awareness):
```python
class MyStrategyPlanner(StrategyPlanner):
    def process(self, input: OpportunitySignal) -> StrategyDirective:
        # GEEN causality management - BaseWorker regelt het!
        return StrategyDirective(
            strategy_directive_id=generate_directive_id(),
            scope=DirectiveScope.OPEN_NEW,
            # ...business logic...
        )
```

### 4.2 Model Copy Pattern

```python
# OpportunityWorker produces OpportunitySignal
signal = OpportunitySignal(
    causality=CausalityChain(
        tick_id="TCK_20251026_100000_a1b2c3d4"
    ),
    opportunity_signal_id="OPP_20251026_100001_def5e6f7"
)

# StrategyPlanner extends chain
directive_causality = signal.causality.model_copy(update={
    "opportunity_signal_ids": ["OPP_20251026_100001_def5e6f7"],
    "strategy_directive_id": "STR_20251026_100002_abc1d2e3"
})
```

---

## 5. Design Beslissingen - BEANTWOORD

### 5.1 Multiple Signals?

**ANTWOORD:** Ja - `opportunity_signal_ids: list[str]`

**Rationale:**
- 📊 Confluence patterns (multiple signals converge)
- 🔄 Correlation strategies (cross-asset signals)
- 🎯 Multi-timeframe signals (HTF + LTF alignment)

### 5.2 Position Management via Tick Birth?

**ANTWOORD:** Ja - Position management strategy run "geboren" bij tick event.

**Voorbeeld:**
```python
# TrailingStopPlanner
causality = CausalityChain(
    tick_id="TCK_20251026_100000_a1b2c3d4",  # ← Position tick birth
)

directive = StrategyDirective(
    strategy_directive_id="STR_20251026_100001_b2c3d4e5",
    causality=causality,
    scope=DirectiveScope.MODIFY_EXISTING,
    target_trade_ids=["TRD_456"],  # ← Position tracking VIA directive
)
```

### 5.3 Schedule Ops via Schedule Birth?

**ANTWOORD:** Ja - DCA/rebalancing "geboren" bij schedule event.

**Voorbeeld:**
```python
# DCA ScheduleWorker
causality = CausalityChain(
    schedule_id="SCH_20251026_100000_abc1d2e3"  # ← Schedule birth
)
```

**Schedule details** (frequency, day-of-week) in **ScheduleEvent DTO**, NIET in schedule_id.

### 5.4 SWOT Context Altijd Samen?

**ANTWOORD:** Nee - `context_assessment_id` is optioneel.

**Scenario A: SWOT Entry Strategy**
```python
causality = CausalityChain(
    opportunity_signal_ids=["OPP_123"],
    context_assessment_id="CTX_456"  # ← Optioneel SWOT context
)
```

**Scenario B: Pure Opportunity (geen SWOT)**
```python
causality = CausalityChain(
    opportunity_signal_ids=["OPP_123"],
    context_assessment_id=None  # ← Geen SWOT assessment
)
```

### 5.5 ThreatSignal = ThreatSignal?

**ANTWOORD:** Ja - één field voor beide.

```python
threat_ids: list[str]  # ← Covers both ThreatSignal AND ThreatSignal
```

**Rationale:**
- ThreatSignal IS een ThreatSignal (risk control)
- Naming: `threat_ids` dekt beide use cases
- Eenvoud: Geen aparte `threat_signal_ids` field

---

## 6. Implementatie Checklist

### 6.1 CausalityChain DTO

- [ ] backend/dtos/causality.py aanmaken
- [ ] 3 birth ID fields (tick_id, news_id, schedule_id)
- [ ] 9 worker output ID fields
- [ ] Birth ID validator (minstens 1 vereist)
- [ ] Pydantic model_config (frozen=False voor copy)

### 6.2 Unit Tests

- [ ] Birth ID validation (tick/news/schedule)
- [ ] Empty chain validation (should fail)
- [ ] Worker ID accumulation
- [ ] Multiple opportunity_signal_ids
- [ ] Model copy pattern
- [ ] Serialization (JSON/dict)

### 6.3 BaseWorker Boilerplate

- [ ] Auto-extract causality from input DTO
- [ ] Auto-copy + extend with worker output ID
- [ ] Auto-propagate to output DTO
- [ ] Integration test voor causality flow

### 6.4 Pipeline DTO Updates

- [ ] OpportunitySignal.causality: CausalityChain
- [ ] ThreatSignal.causality: CausalityChain
- [ ] StrategyDirective.causality: CausalityChain
- [ ] EntryPlan/SizePlan/ExitPlan/RoutingPlan (future)
- [ ] ExecutionDirective (future)

### 6.5 FlowTerminator Implementation

- [ ] Journal reconstruction logic
- [ ] Query Journal met CausalityChain IDs
- [ ] Write causality chain naar Journal
- [ ] Metrics/audit trail generation

---

## 7. Open Issues

### 7.1 Volume Concern

**Issue:** Veel birth IDs produceren geen downstream chain (garbage collection?).

**Optie A:** Journal auto-cleanup orphaned birth IDs  
**Optie B:** Retention policy (7 dagen)  
**Optie C:** Lazy loading (query on-demand)

**Status:** 🟡 OPEN - implementatie fase beslissing

### 7.2 Birth ID Prefix Uniformity

**Status:** ✅ RESOLVED - Military datetime format implemented

**Prefixes:**
- `TCK_` - Market tick events
- `NWS_` - News events
- `SCH_` - Schedule events

**Format:** `PREFIX_YYYYMMDD_HHMMSS_8charhash`

---

## 8. DESIGN GOEDGEKEURD? ✅

**STATUS:** ✅ **APPROVED - READY FOR TDD IMPLEMENTATION**

**Kernpunten:**
- ✅ Laser focus: ALLEEN IDs
- ✅ 12 fields finalized (3 birth + 9 worker outputs)
- ✅ Birth ID validator (minstens 1 vereist)
- ✅ BaseWorker boilerplate auto-propagation
- ✅ FlowTerminator als enige consumer
- ✅ Military datetime ID format uniform
- ✅ All 5 design vragen beantwoord

**Volgende stap:** TDD implementatie (Red → Green → Refactor)

**Start met:**
1. Failing tests voor CausalityChain DTO
2. Implementation om tests groen te maken
3. Refactor voor elegantie
