# CausalityChain - Conceptueel Ontwerp

**Status:** DESIGN REVIEW - LASER FOCUS VERSIE  
**Datum:** 2025-10-26  
**Auteur:** AI Assistant + User Review

**⚠️ NOTITIE: ID Format Convention**

Alle voorbeelden in dit document gebruiken **uniform military datetime format**:
```
PREFIX_YYYYMMDD_HHMMSS_hash
```

**Voorbeelden:**
- `TCK_20251026_100000_a1b2c3d4` (tick birth)
- `OPP_20251026_100001_def5e6f7` (opportunity signal)
- `STR_20251026_100002_abc1d2e3` (strategy directive)

**Oude voorbeelden** (`TCK_123`, `OPP_456`) zijn **illustratief** - implementatie gebruikt altijd datetime format.

---

## 0. KERN PRINCIPE: Single Responsibility

**ENIGE VERANTWOORDELIJKHEID:**  
Verzamel **ALLEEN IDs** voor Journal causality reconstruction in FlowTerminator.

**GEEN verantwoordelijkheid voor:**
- ❌ Business data (symbol, price, direction, etc.)
- ❌ Timestamps (elke DTO heeft eigen timestamp)
- ❌ Confidence scores (OpportunitySignal/StrategyDirective hebben dat)
- ❌ Event details (ThreatSignal/CriticalEvent hebben metadata)
- ❌ Tick data (Position/Trade hebben price info)
- ❌ Strategy ID (StrategyDirective heeft dat)

**PRINCIPE:** Als het in een ander DTO zit, hoort het NIET in CausalityChain.

---

## 1. Architecturale Positie

### 1.1 Waar past dit component?

CausalityChain is een **ID-only container** die door de pipeline vloeit:

```
[OpportunityWorker] → OpportunitySignal
    ↓ (adds opportunity_signal_id to chain)
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

### 1.2 FlowTerminator Usage (ENIGE CONSUMER)

```python
def on_flow_stop(self, execution_directive: ExecutionDirective):
    chain = execution_directive.causality
    
    # Journal reconstruction via IDs
    opportunity = journal.get(chain.opportunity_signal_id)  # → OpportunitySignal
    directive = journal.get(chain.strategy_directive_id)     # → StrategyDirective
    entry_plan = journal.get(chain.entry_plan_id)            # → EntryPlan
    
    # Write causality chain
    journal.write_chain([
        opportunity.opportunity_signal_id,
        directive.strategy_directive_id,
        entry_plan.entry_plan_id,
        ...
    ])
```

---

## 2. Field Design - LASER FOCUS

### 2.1 ALLEEN IDs - GEEN Business Data

**Trigger Root IDs** (eerste worker in keten):
```python
opportunity_signal_id: str | None   # OpportunitySignal ID
threat_signal_id: str | None        # ThreatSignal ID  
context_assessment_id: str | None   # AggregatedContextAssessment ID
critical_event_id: str | None       # CriticalEvent ID
```

**Pipeline Stage IDs** (workers voegen toe tijdens flow):
```python
strategy_directive_id: str | None
entry_plan_id: str | None
size_plan_id: str | None
exit_plan_id: str | None
routing_plan_id: str | None
execution_directive_id: str | None
```

**DAT IS ALLES.** Geen tick data, geen event details, geen timestamps.

---

### 2.2 Waarom GEEN lists voor opportunity_ids/threat_ids?

**Oorspronkelijke gedachte:**
```python
opportunity_ids: list[str]  # Multiple opportunities kunnen fuseren
```

**PROBLEEM:** Feature creep!

**Vragen:**
1. Produceert OpportunityWorker **altijd 1 OpportunitySignal**?
2. Of kan een worker **meerdere OpportunitySignals tegelijk** produceren?

**Als 1-op-1:** Gebruik `opportunity_signal_id: str | None`  
**Als 1-op-N:** Gebruik `opportunity_signal_ids: list[str]`

**MIJN VERWACHTING:** Elke worker produceert **1 DTO per tick**:
- OpportunityWorker → **1** OpportunitySignal
- ThreatDetector → **1** ThreatSignal/CriticalEvent
- StrategyPlanner → **1** StrategyDirective

**Als dit klopt:** GEEN lists nodig, alleen `_id: str | None` fields.

---

### 2.3 Position Management / Scheduled Ops - HOE?

**VRAAG:** Hoe tracken we Position Management/Scheduled Ops **zonder tick/event/schedule data**?

#### **Optie A: Via StrategyDirective metadata**

```python
# TrailingStopPlanner
ctx = CausalityChain(
    # GEEN monitored_position_ids
    # GEEN trigger_tick
)

directive = StrategyDirective(
    strategy_directive_id="STR_123",
    causality=ctx,
    scope=DirectiveScope.MODIFY_EXISTING,
    target_trade_ids=["TRD_456"],  # ← Position tracking VIA directive
    # metadata heeft tick info als nodig
)
```

**Journal reconstruction:**
```python
directive = journal.get("STR_123")
directive.target_trade_ids  # → ["TRD_456"]
directive.scope  # → MODIFY_EXISTING
# Weten: "STR_123 adjusted position TRD_456"
```

#### **Optie B: Via dedicated Position/Schedule IDs**

```python
# TrailingStopPlanner
ctx = CausalityChain(
    position_monitor_event_id="PME_789",  # ← Position monitor logged event
)

directive = StrategyDirective(
    strategy_directive_id="STR_123",
    causality=ctx,
)
```

**Journal reconstruction:**
```python
pme = journal.get("PME_789")  # → PositionMonitorEvent
pme.monitored_position_id  # → "POS_456"
pme.trigger_price  # → 45000
directive = journal.get("STR_123")
# Chain: PME_789 → STR_123
```

**VRAAG:** Hebben we PositionMonitorEvent/ScheduleEvent DTOs?  
**OF:** Is StrategyDirective.target_trade_ids + scope genoeg?

---

### 2.4 SWOT Context - Altijd samen?

**VRAAG:** Komt `context_assessment_id` altijd samen met `opportunity_signal_id`?

**Scenario A: SWOT Entry Strategy**
```python
ctx = CausalityChain(
    opportunity_signal_id="OPP_123",
    context_assessment_id="CTX_456"  # ← Altijd samen?
)
```

**Scenario B: Pure Opportunity (geen SWOT)**
```python
ctx = CausalityChain(
    opportunity_signal_id="OPP_123",
    context_assessment_id=None  # ← Geen context assessment
)
```

**VRAAG:** Bestaat scenario B? Of is SWOT altijd volledig?

---

## 3. Herziende Field Lijst - ALLEEN IDs

### 3.1 Trigger Root IDs (1 vereist)

**Als workers 1-op-1 DTOs produceren:**
```python
opportunity_signal_id: str | None
threat_signal_id: str | None
critical_event_id: str | None
context_assessment_id: str | None
```

**Optioneel (afhankelijk van antwoorden):**
```python
position_monitor_event_id: str | None  # Als we PositionMonitorEvent DTO hebben
schedule_event_id: str | None          # Als we ScheduleEvent DTO hebben
```

### 3.2 Pipeline Stage IDs

```python
strategy_directive_id: str | None
entry_plan_id: str | None
size_plan_id: str | None
exit_plan_id: str | None
routing_plan_id: str | None
execution_directive_id: str | None
```

**DAT IS ALLES. GEEN andere fields.**

---

## 4. Naming: CausalityChain

**Oude naam:** TriggerContext  
**Nieuwe naam:** CausalityChain

**Rationale:**
- ✅ Doel voorop: **Causality** reconstruction
- ✅ Benadrukt **Chain** concept (linked IDs)
- ✅ Past in CausalityFramework documentatie
- ✅ Duidelijker dan "Context" (wat is context?)

**Alternative:** `DecisionChain`, `AuditChain`?

---

## 5. Open Vragen - GEFOCUST

### 5.1 Worker Output Pattern

**VRAAG 1:** Produceert elke worker **1 DTO per tick** of **meerdere DTOs mogelijk**?

**Impact:**
- 1 DTO → `opportunity_signal_id: str | None`
- Meerdere DTOs → `opportunity_signal_ids: list[str]`

**MIJN VERWACHTING:** 1-op-1 (maar bevestiging nodig).

---

### 5.2 Position Management Tracking

**VRAAG 2:** Hoe tracken we Position Management zonder tick/event data?

**Optie A:** Via StrategyDirective.target_trade_ids + scope  
**Optie B:** Via dedicated PositionMonitorEvent DTO (met eigen ID)

**Welke optie verkies je?**

---

### 5.3 Scheduled Operations Tracking

**VRAAG 3:** Hoe tracken we Scheduled Ops (DCA, rebalancing)?

**Optie A:** StrategyDirective heeft metadata "scheduled=true"  
**Optie B:** Dedicated ScheduleEvent DTO (met eigen ID)

**Welke optie verkies je?**

---

### 5.4 SWOT Context Coupling

**VRAAG 4:** Komt `context_assessment_id` **altijd** samen met `opportunity_signal_id`?

**Of:** Kunnen we pure Opportunity hebben zonder Context?

---

### 5.5 Threat vs CriticalEvent

**VRAAG 5:** Hebben we beide nodig?

```python
threat_signal_id: str | None        # ThreatSignal
critical_event_id: str | None       # CriticalEvent
```

**Of:** Is dit hetzelfde concept?

---

## 6. Herziende Design Principes

### 6.1 LASER FOCUS Rules

1. ✅ **ONLY IDs** - Geen business data, timestamps, scores
2. ✅ **ONLY Journal Keys** - Als FlowTerminator het niet opzoekt, hoort het er niet in
3. ✅ **ONLY Immutable** - Copy + extend, never mutate
4. ✅ **ONLY String IDs** - Geen dicts, geen nested DTOs

### 6.2 Feature Creep Checklist

**Voordat je een field toevoegt, vraag:**
1. Is dit een **ID** voor Journal lookup? (JA → toevoegen, NEE → weglaten)
2. Zit deze data al in **ander DTO**? (JA → weglaten, NEE → check vraag 1)
3. Gebruikt **FlowTerminator** dit? (NEE → weglaten)

---

## 7. Implementatie Checklist (NA goedkeuring antwoorden)

- [ ] Beantwoord 5 open vragen
- [ ] Finaliseer field lijst (ONLY IDs)
- [ ] Implement CausalityChain DTO
- [ ] Write 15+ unit tests (ID accumulation, immutability, serialization)
- [ ] Add `causality: CausalityChain` to ALL pipeline DTOs
- [ ] Update FlowTerminator met Journal reconstruction logic

---

## 8. Beslissingen - BEANTWOORD

### Antwoord 1: Worker Output Pattern
**VRAAG:** 1 DTO of meerdere DTOs per tick?  
**ANTWOORD:** Meerdere mogelijk (complexe strategieën, parallelle workers).  
**IMPACT:** Gebruik `list[str]` voor opportunity/threat IDs.

```python
opportunity_signal_ids: list[str] = Field(default_factory=list)
threat_ids: list[str] = Field(default_factory=list)
```

---

### Antwoord 2: Position Management Tracking
**VRAAG:** Hoe tracken zonder tick/position details?  
**ANTWOORD:** ❌ VRAAG WAS VERWARREND.

**CORRECTIE:**
- TrailingStopPlanner is een **StrategyPlanner** (niet ExitPlanner!)
- TrailingStopPlanner produceert **StrategyDirective** → voegt `strategy_directive_id` toe aan chain
- ExitPlanner leest StrategyDirective → produceert **ExitPlan** → voegt `exit_plan_id` toe aan chain

**GEEN EXTRA IDs NODIG** - workers loggen hun output IDs zoals bedoeld.

**MAAR:** Wat triggert TrailingStopPlanner?

**Optie A - Tick Trigger:**
```python
# Tick trigger logged als initiator
ctx = CausalityChain(
    tick_trigger_id="TCK_123"  # ← Tick event ID
)
# TrailingStopPlanner
ctx = ctx.model_copy(update={"strategy_directive_id": "STR_456"})
```

**Optie B - Monitor Event:**
```python
# Position monitor logged als initiator  
ctx = CausalityChain(
    position_monitor_id="PMN_123"  # ← Monitor event ID
)
# TrailingStopPlanner
ctx = ctx.model_copy(update={"strategy_directive_id": "STR_456"})
```

**VRAAG:** Hoe initiëren we Position Management flows? Wat is de eerste ID in de keten?

---

### Antwoord 3: Scheduled Operations Tracking
**VRAAG:** Hoe tracken scheduled ops?  
**ANTWOORD:** Via **schedule_trigger_id** in causality chain (NIET metadata).

```python
ctx = CausalityChain(
    schedule_trigger_id="SCH_789"  # ← Schedule event ID
)
# DCAPlanner
ctx = ctx.model_copy(update={"strategy_directive_id": "STR_456"})
```

**Schedule event** wordt gelogd in Journal als initiator.

---

### Antwoord 4: SWOT Context Coupling
**VRAAG:** Context altijd samen met Opportunity?  
**ANTWOORD:** NEE - StrategyDirective kan ontstaan zonder ContextAssessment.

```python
# Pure Opportunity (zonder context)
ctx = CausalityChain(
    opportunity_signal_ids=["OPP_123"],
    context_assessment_id=None  # ← ALLOWED
)

# SWOT volledig
ctx = CausalityChain(
    opportunity_signal_ids=["OPP_123"],
    context_assessment_id="CTX_456"  # ← OPTIONAL
)
```

---

### Antwoord 5: ThreatSignal vs CriticalEvent
**VRAAG:** Twee termen voor hetzelfde?  
**ANTWOORD:** JA - **CriticalEvent IS de ThreatSignal**.

**Code analyse:**
- `backend/dtos/strategy/critical_event.py` → ThreatWorker output
- Docstring: "Part of SWOT framework: ThreatWorkers → CriticalEvent (Threats)"
- Geen aparte ThreatSignal DTO

**CONCLUSIE:** Gebruik **1 field** - `threat_ids: list[str]` (verwijst naar CriticalEvent.threat_id)

---

## 9. Definitieve Field Lijst - FINAAL

### 9.1 Trigger Initiator IDs (worker output IDs)

```python
# SWOT Framework
opportunity_signal_ids: list[str] = Field(
    default_factory=list,
    description="OpportunitySignal IDs (SWOT Opportunities)"
)
threat_ids: list[str] = Field(
    default_factory=list,
    description="CriticalEvent.threat_id values (SWOT Threats)"
)
context_assessment_id: str | None = Field(
    default=None,
    description="AggregatedContextAssessment ID (SWOT Strengths/Weaknesses)"
)

# Flow Initiators (non-SWOT)
tick_trigger_id: str | None = Field(
    default=None,
    description="Tick event ID (position management trigger)"
)
schedule_trigger_id: str | None = Field(
    default=None,
    description="Schedule event ID (DCA, rebalancing trigger)"
)
news_trigger_id: str | None = Field(
    default=None,
    description="News event ID (news-driven strategy trigger)"
)
```

### 9.2 Pipeline Stage IDs (worker adds during flow)

```python
strategy_directive_id: str | None = Field(
    default=None,
    description="StrategyDirective ID (added by StrategyPlanner)"
)
entry_plan_id: str | None = Field(
    default=None,
    description="EntryPlan ID (added by EntryPlanner)"
)
size_plan_id: str | None = Field(
    default=None,
    description="SizePlan ID (added by SizePlanner)"
)
exit_plan_id: str | None = Field(
    default=None,
    description="ExitPlan ID (added by ExitPlanner)"
)
routing_plan_id: str | None = Field(
    default=None,
    description="RoutingPlan ID (added by RoutingPlanner)"
)
execution_directive_id: str | None = Field(
    default=None,
    description="ExecutionDirective ID (added by DirectiveAssembler)"
)
```

**TOTAAL:** 12 fields - ALLEEN IDs, GEEN business data.

---

## 10. FINAAL: Strategy Run "Geboorte" Concept

### 10.1 Geboorte van een Strategy Run

**KERN CONCEPT:** Elke strategy run **wordt geboren** bij één van deze events:
1. **Market Tick** → `tick_id` (TCK_ prefix)
2. **News Event** → `news_id` (NWS_ prefix)
3. **Schedule Event** → `schedule_id` (SCH_ prefix)

**Geboorte = Eerste ID in CausalityChain.**

### 10.2 Geboorte ID Initialisatie

**Bij strategy run start:**
```python
# Market Tick trigger
### 10.2 Geboorte ID Format - UNIFORM

**KRITIEK: Alle IDs volgen uniform military datetime format.**

**Format:** `PREFIX_YYYYMMDD_HHMMSS_hash`

**Bij strategy run start:**
```python
# Market Tick trigger
ctx = CausalityChain(
    tick_id="TCK_20251026_100000_a1b2c3d4"  # ← GEBOORTE
)

# News Event trigger
ctx = CausalityChain(
    news_id="NWS_20251026_100500_def5e6f7"  # ← GEBOORTE
)

# Schedule Event trigger
ctx = CausalityChain(
    schedule_id="SCH_20251026_100000_abc1d2e3"  # ← GEBOORTE
)
```

**ID Format Voordelen:**
- ✅ **Uniformity**: Alle IDs volgen zelfde patroon
  - ❌ NIET: `SCH_WEEKLY_MONDAY_1000` (te veel trigger info in ID)
  - ✅ WEL: `SCH_20251026_100000_abc1d2e3` (uniform format)
- ✅ **Temporal sortability**: Chronologische ordering in Journal
- ✅ **Human readability**: Zie direct wanneer ID gecreëerd
- ✅ **Uniqueness**: Hash suffix voorkomt collisions

**Trigger details** (weekly, Monday, 10:00) horen in **ScheduleEvent DTO**, NIET in ID.

**Dan:** Workers kopiëren + extenden deze chain.

### 10.3 Worker Boilerplate Verantwoordelijkheid

**KRITIEK:** BaseWorker boilerplate handelt causality automatisch:

```python
# BaseWorker boilerplate (pseudo-code)
class BaseWorker:
    def process(self, input_dto: BaseModel) -> DispositionEnvelope:
        # 1. Extract causality from input
        chain = input_dto.causality if hasattr(input_dto, 'causality') else None
        
        # 2. Worker-specific logic
        output_dto = self._do_work(input_dto)
        
        # 3. Copy + extend chain (auto-add worker's output ID)
        if chain:
            output_dto.causality = chain.model_copy(
                update={f"{self.output_type}_id": output_dto.id}
            )
        
        # 4. Return
        return DispositionEnvelope(disposition="CONTINUE", payload=output_dto)
```

**Workers NOOIT handmatig causality managen** - boilerplate doet dit.

### 10.4 Volledige Flow Voorbeeld

```python
# GEBOORTE: Market Tick
ctx = CausalityChain(tick_id="TCK_123")

# OpportunityWorker
opportunity = OpportunitySignal(
    opportunity_signal_id="OPP_456",
    causality=ctx.model_copy(update={"opportunity_signal_ids": ["OPP_456"]})
)
# Chain: TCK_123 → OPP_456

# StrategyPlanner
directive = StrategyDirective(
    strategy_directive_id="STR_789",
    causality=opportunity.causality.model_copy(
        update={"strategy_directive_id": "STR_789"}
    )
)
# Chain: TCK_123 → OPP_456 → STR_789

# EntryPlanner
entry_plan = EntryPlan(
    entry_plan_id="ENT_012",
    causality=directive.causality.model_copy(
        update={"entry_plan_id": "ENT_012"}
    )
)
# Chain: TCK_123 → OPP_456 → STR_789 → ENT_012

# ... etc tot ExecutionDirective

# FlowTerminator
journal.reconstruct_chain(execution_directive.causality)
# Volledige chain: TCK_123 → OPP_456 → STR_789 → ENT_012 → SIZ_345 → EXT_678 → ROU_901 → EXE_234
```

### 10.5 Implicaties

**Volume:**
- ✅ Ja, veel tick_ids in Journal (elke tick = potentiële geboorte)
- ✅ MAAR: Meeste ticks produceren geen workers → geen verdere chain
- ✅ Journal optimalisatie: Auto-cleanup orphaned birth IDs (geen downstream)

**Causality Garanties:**
- ✅ ALTIJD geboorte ID (tick/news/schedule)
- ✅ ALTIJD volledige chain (workers auto-propagate)
- ✅ GEEN orphaned flows (geboorte = root)

**Worker Simplicity:**
- ✅ Workers NOOIT causality managen
- ✅ BaseWorker boilerplate = single point of truth
- ✅ Plugin developers onbewust van causality mechanism

---

## 11. DEFINITIEVE Field Lijst - FINAL FINAL

### 11.1 Geboorte IDs (strategy run initiators)

```python
tick_id: str | None = Field(
    default=None,
    description="Market tick ID (TCK_ prefix) - strategy run birth"
)
news_id: str | None = Field(
    default=None,
    description="News event ID (NWS_ prefix) - strategy run birth"
)
schedule_id: str | None = Field(
    default=None,
    description="Schedule event ID (SCH_ prefix) - strategy run birth"
)
```

**MINSTENS 1 VEREIST** - elke strategy run heeft geboorte.

### 11.2 Worker Output IDs (SWOT + Planning)

```python
# SWOT Framework
opportunity_signal_ids: list[str] = Field(
    default_factory=list,
    description="OpportunitySignal IDs (SWOT Opportunities)"
)
threat_ids: list[str] = Field(
    default_factory=list,
    description="CriticalEvent.threat_id values (SWOT Threats)"
)
context_assessment_id: str | None = Field(
    default=None,
    description="AggregatedContextAssessment ID (SWOT Context)"
)

# Planning Pipeline
strategy_directive_id: str | None = Field(
    default=None,
    description="StrategyDirective ID (StrategyPlanner output)"
)
entry_plan_id: str | None = Field(
    default=None,
    description="EntryPlan ID (EntryPlanner output)"
)
size_plan_id: str | None = Field(
    default=None,
    description="SizePlan ID (SizePlanner output)"
)
exit_plan_id: str | None = Field(
    default=None,
    description="ExitPlan ID (ExitPlanner output)"
)
routing_plan_id: str | None = Field(
    default=None,
    description="RoutingPlan ID (RoutingPlanner output)"
)
execution_directive_id: str | None = Field(
    default=None,
    description="ExecutionDirective ID (DirectiveAssembler output)"
)
```

**TOTAAL:** 12 fields - 3 birth IDs + 9 worker output IDs.

---

## 12. Validatie: Minstens 1 Geboorte ID

**Pydantic Validator:**
```python
@model_validator(mode='after')
def require_birth_id(self) -> 'CausalityChain':
    """Validate at least one birth ID is present."""
    if not any([self.tick_id, self.news_id, self.schedule_id]):
        raise ValueError(
            "CausalityChain requires at least one birth ID "
            "(tick_id, news_id, or schedule_id)"
        )
    return self
```

**Rationale:** Elke strategy run MOET een geboorte hebben.

---

## 13. Implementatie Checklist

- [ ] Implement CausalityChain DTO met 12 fields
- [ ] Add birth ID validator (minstens 1 vereist)
- [ ] Write 20+ unit tests:
  - [ ] Birth ID validation (tick/news/schedule)
  - [ ] Worker ID accumulation (copy + extend)
  - [ ] Immutability pattern
  - [ ] Serialization (JSON/dict)
  - [ ] Multiple opportunity/threat IDs
- [ ] Update BaseWorker boilerplate:
  - [ ] Auto-extract causality from input DTO
  - [ ] Auto-copy + extend with worker output ID
  - [ ] Auto-propagate to output DTO
- [ ] Add `causality: CausalityChain` to ALL pipeline DTOs:
  - [ ] OpportunitySignal
  - [ ] CriticalEvent
  - [ ] StrategyDirective
  - [ ] EntryPlan, SizePlan, ExitPlan, RoutingPlan
  - [ ] ExecutionDirective
- [ ] Implement FlowTerminator Journal reconstruction
- [ ] Journal auto-cleanup orphaned birth IDs

---

## 14. Open Issues

### 14.1 Future Birth Types

**Vraag:** Andere geboorte types dan tick/news/schedule?

**Mogelijkheden:**
- Manual trigger (user-initiated trade)
- Portfolio rebalancing trigger
- Risk limit breach trigger

**Besluit:** Start met 3 (tick/news/schedule), extend later indien nodig.

### 14.2 BaseWorker Boilerplate Locatie

**Vraag:** Waar implementeren we causality auto-propagation?

**Optie A:** `BaseWorker._process()` wrapper  
**Optie B:** `EventAdapter` (voor workers aanroept)  
**Optie C:** Pydantic `__init__` hook in DTOs

**Aanbeveling:** Optie A - BaseWorker heeft volledige controle.

---

## 15. DESIGN GOEDGEKEURD? ✅

**Alle vragen beantwoord:**
- ✅ Multiple signals mogelijk (lists)
- ✅ Position management via tick_id birth
- ✅ Schedule ops via schedule_id birth
- ✅ SWOT context optioneel
- ✅ CriticalEvent = ThreatSignal (1 field)
- ✅ Birth concept = tick/news/schedule IDs

**Klaar voor TDD?**

JA → Start implementatie (Red → Green → Refactor)  
NEE → Welke onderdelen nog onduidelijk?

### 1.1 Waar past dit component?

TriggerContext is een **universele causality tracking DTO** die door de **hele pipeline** vloeit:

```
[OpportunityWorker] → OpportunitySignal (causality: TriggerContext)
    ↓
[StrategyPlanner] → StrategyDirective (causality: TriggerContext + strategy_directive_id)
    ↓
[EntryPlanner] → EntryPlan (causality: TriggerContext + entry_plan_id)
[SizePlanner] → SizePlan (causality: TriggerContext + size_plan_id)
[ExitPlanner] → ExitPlan (causality: TriggerContext + exit_plan_id)
[RoutingPlanner] → RoutingPlan (causality: TriggerContext + routing_plan_id)
    ↓
[DirectiveAssembler] → ExecutionDirective (causality: TriggerContext + execution_directive_id)
    ↓
[ExecutionHandler] → STOP disposition
    ↓
[FlowTerminator] → **GEBRUIKT TriggerContext voor Journal reconstruction**
```

### 1.2 Input Producers

**Trigger Initiators** (eerste in keten):
- OpportunityWorker: `opportunity_ids`
- ThreatDetector: `threat_ids`
- ContextAggregator: `context_assessment_id`
- PositionMonitor: `monitored_position_ids`, `trigger_tick`
- ScheduleTrigger: `schedule_trigger`

**Pipeline Workers** (copy + extend):
- StrategyPlanner: adds `strategy_directive_id`
- EntryPlanner: adds `entry_plan_id`
- SizePlanner: adds `size_plan_id`
- ExitPlanner: adds `exit_plan_id`
- RoutingPlanner: adds `routing_plan_id`
- DirectiveAssembler: adds `execution_directive_id`

### 1.3 Output Consumer

**FlowTerminator** (ENIGE consumer die TriggerContext GEBRUIKT):
- Query's Journal met verzamelde IDs
- Reconstrueert volledige decision chain
- Schrijft causality naar Journal
- Produceert metrics/audit trail

## 2. Verantwoordelijkheden & Contract

### 2.1 Single Responsibility

**Verantwoordelijkheid:**  
Immutable container die decision chain IDs verzamelt tijdens pipeline flow.

**NIET verantwoordelijk voor:**
- ❌ Business logic (workers doen dat)
- ❌ Validation (workers valideren hun eigen inputs)
- ❌ Journal queries (alleen FlowTerminator doet dat)
- ❌ Event routing (EventAdapter doet dat)

### 2.2 Inkomende Data

**Trigger Initiator Fields** (eerste worker vult in):
- `opportunity_ids: list[str]` - SWOT OpportunitySignal IDs
- `threat_ids: list[str]` - SWOT ThreatSignal IDs
- `context_assessment_id: str | None` - SWOT ContextAssessment ID
- `monitored_position_ids: list[str]` - Position management position IDs
- `trigger_tick: dict[str, Any] | None` - Tick data voor position management
- `trigger_event: dict[str, Any] | None` - Event data voor risk control
- `schedule_trigger: dict[str, Any] | None` - Schedule info voor DCA/rebalancing

**Pipeline Stage IDs** (workers voegen toe tijdens flow):
- `strategy_directive_id: str | None`
- `entry_plan_id: str | None`
- `size_plan_id: str | None`
- `exit_plan_id: str | None`
- `routing_plan_id: str | None`
- `execution_directive_id: str | None`

### 2.3 Uitgaande Data

**Output:** Identiek aan input (immutable pattern).  
Workers krijgen TriggerContext via `.model_copy(update={...})` en produceren nieuwe instance.

### 2.4 Invarianten

**MUST HOLD:**
1. ✅ **Immutability**: Workers NOOIT direct muteren, altijd `.model_copy()`
2. ✅ **Monotonic Growth**: IDs kunnen alleen toegevoegd, nooit verwijderd
3. ✅ **Single Consumer**: Alleen FlowTerminator query't met IDs
4. ✅ **Optional Fields**: Alle trigger fields zijn optioneel (verschillende worker types)

**MAY BE VIOLATED (allowed):**
- ⚠️ Meerdere trigger types tegelijk (bijv. opportunity + threat)
- ⚠️ Pipeline IDs ontbreken (flow terminated early)

## 3. Field Design

### 3.1 Absoluut Noodzakelijke Fields

**Trigger Initiator Fields** (minstens 1 vereist voor causality):
- `opportunity_ids` - SWOT entry triggers
- `threat_ids` - SWOT/risk control triggers
- `context_assessment_id` - SWOT context
- `monitored_position_ids` - Position management triggers
- `trigger_tick` - Tick-driven triggers
- `trigger_event` - Event-driven triggers
- `schedule_trigger` - Scheduled operation triggers

**Pipeline Stage IDs** (optioneel, toegevoegd door workers):
- `strategy_directive_id`
- `entry_plan_id`
- `size_plan_id`
- `exit_plan_id`
- `routing_plan_id`
- `execution_directive_id`

### 3.2 Optionele Fields & Rationale

**Vraag:** Zijn er fields die we NIET moeten toevoegen?

**Feature Creep Risico's:**
- ❌ `timestamp` - Elke DTO heeft al zijn eigen timestamp
- ❌ `strategy_id` - Zit al in StrategyDirective/ExecutionDirective
- ❌ `symbol` - Zit al in EntryPlan/ExecutionDirective
- ❌ `worker_chain` - Journal reconstruction doet dit al
- ❌ `confidence` - Zit in OpportunitySignal/StrategyDirective
- ❌ `severity` - Zit in ThreatSignal/CriticalEvent

**Principe:** TriggerContext bevat ALLEEN IDs voor Journal lookups, geen business data.

### 3.3 Type Design

**Field Types Rationale:**

```python
# IDs als strings (Journal lookup keys)
opportunity_ids: list[str]  # Multiple opportunities kunnen fuseren
threat_ids: list[str]  # Multiple threats kunnen triggeren
strategy_directive_id: str | None  # 1 directive per flow

# Trigger data als dict (flexibel, plugin-agnostic)
trigger_tick: dict[str, Any] | None  # Plugin-specifieke tick fields
trigger_event: dict[str, Any] | None  # Plugin-specifieke event fields
schedule_trigger: dict[str, Any] | None  # Plugin-specifieke schedule fields
```

**Waarom `dict[str, Any]` voor triggers?**
- ✅ Plugin-agnostic (verschillende workers, verschillende fields)
- ✅ Geen DTO dependencies (trigger_tick is geen TickDTO)
- ✅ Serializable (JSON/YAML compatible)
- ❌ Geen type safety (trade-off voor flexibiliteit)

**Alternatief:** Strict typing met Union types?
```python
# VERWORPEN - Te complex, te veel dependencies
trigger_tick: TickData | None
trigger_event: CriticalEvent | RiskEvent | None
```

## 4. Immutability & Flow Pattern

### 4.1 Copy + Extend Pattern

**Kernprincipe:** Workers NOOIT muteren, altijd kopiëren + uitbreiden.

```python
# OpportunityWorker (initiator)
ctx = TriggerContext(opportunity_ids=["OPP_123"])

# StrategyPlanner (copy + extend)
ctx = ctx.model_copy(update={"strategy_directive_id": "STR_456"})

# EntryPlanner (copy + extend)
ctx = ctx.model_copy(update={"entry_plan_id": "ENT_789"})
```

**Pydantic Support:**
- `model_config = {"frozen": False}` (allow copy)
- Workers gebruiken `.model_copy(update={...})`

### 4.2 Flow Pattern

**Sync Flow** (via TickCache):
```
Worker produceert DTO met TriggerContext
    ↓
set_result_dto(MyDTO(causality=ctx))
    ↓
Volgende worker: get_required_dtos(MyDTO)
    ↓
Kopieert ctx uit MyDTO, extend, produceert eigen DTO
```

**Async Flow** (via EventBus):
```
Worker publiceert event met payload (DTO met TriggerContext)
    ↓
EventAdapter roept subscriber aan
    ↓
Subscriber leest TriggerContext uit payload
    ↓
Kopieert ctx, extend, produceert eigen DTO
```

### 4.3 Eindbestemming

**FlowTerminator** (ENIGE component die TriggerContext GEBRUIKT):

```python
def on_flow_stop(self, execution_directive: ExecutionDirective):
    ctx = execution_directive.causality
    
    # Journal reconstruction
    if ctx.opportunity_ids:
        opportunities = journal.query(opportunity_ids=ctx.opportunity_ids)
    if ctx.strategy_directive_id:
        directive = journal.query(directive_id=ctx.strategy_directive_id)
    if ctx.entry_plan_id:
        entry_plan = journal.query(plan_id=ctx.entry_plan_id)
    
    # Write causality chain to Journal
    journal.write_causality_chain(
        root_ids=ctx.opportunity_ids,
        chain=[ctx.strategy_directive_id, ctx.entry_plan_id, ...]
    )
```

## 5. Edge Cases & Failure Modes

### 5.1 Partial Pipeline Execution

**Scenario:** Flow stopt vroeg (bijv. na EntryPlanner faalt).

**Gevolg:**
- TriggerContext heeft: opportunity_ids, strategy_directive_id, entry_plan_id
- TriggerContext mist: size_plan_id, exit_plan_id, routing_plan_id, execution_directive_id

**Handling:**
- FlowTerminator detecteert partial chain
- Journal markeert als "incomplete flow"
- Metrics track failure point

### 5.2 Multiple Trigger Types

**Scenario:** Opportunity + Threat tegelijk (bijv. bullish breakout + risk warning).

**Gevolg:**
- TriggerContext heeft: opportunity_ids=["OPP_1"], threat_ids=["THR_2"]
- StrategyPlanner moet beide wegen

**Handling:**
- Allowed - StrategyPlanner logic beslist
- Journal reconstruction toont beide triggers

### 5.3 Missing Trigger Context

**Scenario:** Worker vergeet TriggerContext door te geven.

**Gevolg:**
- Downstream worker krijgt DTO zonder causality
- FlowTerminator kan chain niet reconstrueren

**Handling:**
- ❌ NIET allowed - Contract violation
- Validation tijdens bootstrap? (DependencyValidator check?)
- Runtime assertion in FlowTerminator?

**VRAAG VOOR REVIEW:** Hoe forceren we TriggerContext in alle DTOs?

### 5.4 ID Collision

**Scenario:** Twee workers genereren zelfde ID.

**Gevolg:**
- Journal lookup vindt verkeerde entry
- Causality chain corrupted

**Handling:**
- ID generators garanteren uniciteit (UUID + prefix)
- Journal primary keys preventeer duplicates

## 6. Open Vragen voor Review

### 6.1 Field Optionality

**Vraag:** Moeten we minstens 1 trigger field verplichten?

**Optie A:** Alle fields optioneel (huidige design)
```python
ctx = TriggerContext()  # Valid, maar geen causality
```

**Optie B:** Eis minstens 1 trigger field
```python
# Pydantic root_validator
if not any([self.opportunity_ids, self.threat_ids, ...]):
    raise ValueError("At least one trigger field required")
```

**Aanbeveling:** Optie A - FlowTerminator detecteert lege context, markeert als "orphaned flow".

### 6.2 Dict vs Structured Trigger Data

**Vraag:** Blijven we bij `dict[str, Any]` voor trigger_tick/event/schedule?

**Voordeel dict:**
- ✅ Plugin-agnostic
- ✅ Geen DTO dependencies
- ✅ Eenvoudig serializable

**Nadeel dict:**
- ❌ Geen type safety
- ❌ Runtime errors bij verkeerde keys
- ❌ Geen IDE autocomplete

**Alternatief:** Structured types
```python
class TickTrigger(BaseModel):
    symbol: str
    price: Decimal
    timestamp: datetime

trigger_tick: TickTrigger | None
```

**Aanbeveling:** Blijf bij dict - type safety is workers' verantwoordelijkheid.

### 6.3 TriggerContext als Mandatory Field

**Vraag:** Hoe forceren we `causality: TriggerContext` in ALLE pipeline DTOs?

**Opties:**
1. **BasePipelineDTO** met mandatory causality field?
2. **Manual enforcement** in code reviews?
3. **Bootstrap validation** via DependencyValidator?
4. **Runtime validation** in FlowTerminator (fail als causality ontbreekt)?

**Aanbeveling:** Combinatie 1 + 3 (BasePipelineDTO + bootstrap check).

### 6.4 Naming

**Vraag:** Is "TriggerContext" de juiste naam?

**Alternatieven:**
- `CausalityChain` - Benadrukt causality aspect
- `PipelineContext` - Benadrukt pipeline flow
- `DecisionChain` - Benadrukt decision tracking
- `TriggerContext` - Huidige naam

**Aanbeveling:** `TriggerContext` - Kort, duidelijk, trigger = causality root.

## 7. Implementatie Checklist

Na conceptuele goedkeuring, volgende stappen:

- [ ] Implementeer TriggerContext DTO in `backend/dtos/causality.py`
- [ ] Schrijf 20+ unit tests voor TriggerContext
- [ ] Implementeer BasePipelineDTO (optioneel, zie vraag 6.3)
- [ ] Update bestaande DTOs met `causality: TriggerContext` field:
  - [ ] OpportunitySignal
  - [ ] CriticalEvent
  - [ ] StrategyDirective (al gedaan)
  - [ ] EntryPlan, SizePlan, ExitPlan, RoutingPlan
  - [ ] ExecutionDirective
- [ ] Implementeer FlowTerminator Journal reconstruction logic
- [ ] Update DependencyValidator voor causality field check
- [ ] End-to-end causality test

## 8. Review Beslissingen

**TE BESPREKEN MET GEBRUIKER:**

1. ✅ Zijn alle trigger fields noodzakelijk? (opportunity, threat, context, position, tick, event, schedule)
2. ✅ Zijn alle pipeline IDs noodzakelijk? (strategy_directive, entry_plan, size_plan, exit_plan, routing_plan, execution_directive)
3. ❓ Moeten we minstens 1 trigger field verplichten? (Zie 6.1)
4. ❓ Blijven we bij `dict[str, Any]` voor trigger data? (Zie 6.2)
5. ❓ Hoe forceren we causality field in alle DTOs? (Zie 6.3)
6. ❓ Feature creep check: Missen we kritieke fields? Hebben we overbodige fields?

**NA REVIEW:** Start TDD workflow (Red → Green → Refactor).
