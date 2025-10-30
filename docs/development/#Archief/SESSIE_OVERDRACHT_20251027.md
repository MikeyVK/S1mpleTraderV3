# Sessie Overdracht - Strategy Planning DTOs & Pipeline Architectuur

**Datum:** 2025-10-27  
**Sessie Focus:** Pipeline architectuur documentatie + voorbereiding DTO refactor  
**Status:** Documentatie compleet, klaar voor implementatie

---

## 🎯 Wat We Vandaag Hebben Bereikt

### 1. **Definitive Pipeline Architectuur Document**

**Bestand:** `docs/development/STRATEGY_PIPELINE_ARCHITECTURE.md` ✅ GECOMMIT

**Inhoud:**
- Complete 6+1 fase pipeline beschrijving (Bootstrapping → Finale)
- Confidence-driven specialization pattern
- Event-driven architectuur (geen Operators - alleen EventAdapters)
- Alle DTO specificaties met exacte fields
- Architectural patterns en rationale
- Config hierarchy overzicht

**Waarom belangrijk:**
- Dit is NU het **leidende document** voor alle pipeline discussies
- Vervangt versnipperde/verouderde info uit agent.md en V2 docs
- Valideert user's 6-fase schets tegen V2 proven patterns
- Borgt architecturale beslissingen (bus-agnostic, statische DTOs, etc.)

**Key Decisions Gedocumenteerd:**
1. **Geen causality in Plan DTOs** - Alleen in StrategyDirective en ExecutionDirective
2. **4 planners zijn sub-sub-planners** - Aangestuurd door StrategyPlanner via confidence
3. **Planners zijn DOM** - Config is SLIM (trigger ranges in YAML)
4. **Hybrid execution** - Parallel (Entry/Size/Exit) + Sequential (Routing)
5. **Statische DTOs** - Dynamiek = aparte workers (trailing stops, breakeven, etc.)

### 2. **Routing Planner Deep Dive**

**Bestand:** `docs/development/ROUTING_PLANNER_DEEP_DIVE.md` ✅ GECOMMIT

**Inhoud:**
- Waarom routing gescheiden van entry (SRP principle)
- De 4 kern beslissingen: timing, urgency, slippage, iceberg
- Concrete voorbeelden met verschillende confidence scenarios
- Specialisten (MarketOrderRouter, TWAPRouter, IcebergRouter, etc.)
- Platform config vs per-trade config

**Waarom belangrijk:**
- Routing was het meest abstracte concept - nu concreet uitgelegd
- User begreep entry/size/exit intuïtief, routing was onduidelijk
- Document maakt duidelijk: routing = execution tactics (HOE/WANNEER)

### 3. **TODO.md Updates**

**Wijzigingen:**
- Referenties naar nieuwe pipeline docs toegevoegd
- Gemarkeerd als leidende documenten

---

## 🧠 Architecturale Inzichten - De User's Visie

### **De 6+1 Fase Pipeline (User's Schets)**

User gaf ons deze flow - we hebben het gevalideerd en gedocumenteerd:

```
Fase 0: BOOTSTRAPPING
  - Rolling window opbouw voor alle timeframes
  - Worker initialisatie, event wiring

Fase 1a: CONTEXT ANALYSE (Sequential)
  - Markt "kaart" - Sterktes & Zwaktes
  - ContextWorkers verrijken data

Fase 1b: CONTEXT AGGREGATIE (Platform)
  - ContextAggregator produceert strength/weakness scores

Fase 2a & 2b: OPPORTUNITY + THREAT (Parallel)
  - Kansen detectie (confidence scores)
  - Bedreigingen detectie (severity scores)

Fase 3: STRATEGY PLANNING (Confrontatie)
  - SWOT confrontatie matrix
  - Output: StrategyDirective (confidence + hints)
  - KNOOPPUNT voor iteratieve strategieën (DCA, trailing stops, etc.)

Fase 4a: TRADE PLANNING (Hybrid)
  - Parallel: Entry, Size, Exit planners (confidence-filtered)
  - Sequential: Routing planner (krijgt context van eerdere plannen)
  - Planners zijn DOM - config filtert op confidence ranges

Fase 4b: TRADE PLAN AGGREGATIE (Platform)
  - PlanningAggregator verzamelt 4 plannen
  - Output: ExecutionDirective

Fase 5: EXECUTION (Environment-dependent)
  - BacktestHandler / PaperHandler / LiveHandler
  - Bus-agnostic pattern (DispositionEnvelope)

Fase 6: RUN FINALE (Cleanup & Logging)
  - FlowTerminator: causality reconstruction via TriggerContext
  - Journaling, metrics, garbage collection
```

### **Kernprincipes (User's Filosofie)**

1. **SRP Overal**
   - Elke component één verantwoordelijkheid
   - Dynamiek = aparte workers, niet embedded in DTOs
   - Trailing stops? → Aparte PositionMonitor worker publiceert nieuwe ExitPlan

2. **Plugin-First**
   - Alle quant logica in configureerbare plugins
   - Platform = framework, quant plugt specialisten in via YAML

3. **Bus-Agnostic Workers**
   - Geen EventBus dependency in workers
   - Return DispositionEnvelope, EventAdapter handles routing

4. **Confidence-Driven Specialization**
   - StrategyPlanner produceert confidence score
   - Planners filteren op confidence ranges (config, niet code)
   - Voorbeeld: AggressiveMarketEntry [0.8-1.0], PatientLimit [0.3-0.7]

5. **Platform = Configureerbaar, UI-Gestuurd**
   - Maximaal configureerbaar binnen logische grenzen
   - UI genereert configs, gebruiker kiest expertise niveau
   - Geen hardcoded behavior

---

## 📋 DTO Analyse - Klaar voor Implementatie

### **De 4 Lean Plan DTOs (Definitief)**

User vroeg mij als quant te kijken naar zuivere inhoud. Conclusie:

#### **EntryPlan - WHAT/WHERE**
```python
class EntryPlan(BaseModel):
    plan_id: str  # ENT_YYYYMMDD_HHMMSS_xxxxx (military datetime)
    
    # Trade identiteit
    symbol: str
    direction: Literal["BUY", "SELL"]
    
    # Order spec (statisch)
    order_type: Literal["MARKET", "LIMIT", "STOP_LIMIT"]
    limit_price: Decimal | None
    stop_price: Decimal | None
```

**GEEN causality** - Sub-planners doen geen causality tracking  
**WEG:** created_at, planner_id, timing (→ Routing), reference_price, valid_until, rationale

#### **SizePlan - HOW MUCH**
```python
class SizePlan(BaseModel):
    plan_id: str  # SIZ_YYYYMMDD_HHMMSS_xxxxx
    
    # Position sizing (absolute values)
    position_size: Decimal
    position_value: Decimal
    risk_amount: Decimal
    leverage: Decimal  # default 1.0
```

**WEG:** created_at, planner_id, account_risk_pct (was input), max_position_value (was constraint)

#### **ExitPlan - WHERE OUT**
```python
class ExitPlan(BaseModel):
    plan_id: str  # EXT_YYYYMMDD_HHMMSS_xxxxx
    
    # Risk boundaries (statisch)
    stop_loss_price: Decimal
    take_profit_price: Decimal | None
```

**GEEN trailing/breakeven config** - Aparte PositionMonitor worker  
**GEEN partial_exits** - ExecutionHandler splits orders

#### **RoutingPlan - HOW/WHEN**
```python
class RoutingPlan(BaseModel):
    plan_id: str  # ROU_YYYYMMDD_HHMMSS_xxxxx
    
    # Execution tactics
    timing: Literal["IMMEDIATE", "TWAP", "LAYERED", "PATIENT"]
    time_in_force: Literal["GTC", "IOC", "FOK"]
    
    # Risk controls
    max_slippage_pct: Decimal
    
    # Preferences
    execution_urgency: Decimal  # 0.0-1.0
    iceberg_preference: Decimal | None
```

**GEEN TWAP params** - Platform config (uniform algorithm)  
**WEG:** Alle velden die in huidige EntryPlan zaten maar routing concerns zijn

### **Causality Propagation Pattern**

User clarified: **Sub-planners hebben GEEN causality field**

```
StrategyDirective (heeft causality: CausalityChain)
    ↓
4 Sub-Planners (krijgen StrategyDirective als input)
    ↓
Plan DTOs (GEEN causality field - pure execution)
    ↓
PlanningAggregator (pakt causality uit StrategyDirective + voegt plan IDs toe)
    ↓
ExecutionDirective (heeft causality: CausalityChain - compleet)
```

**Rationale:** BaseWorker boilerplate bepaalt later hoe causality propagates

---

## 🔍 Belangrijke Discussies - Architecturale Keuzes

### **Q1: Partial Exits - Waar?**

**User's keuze:** ExecutionHandler splits (niet in ExitPlan)

**Rationale:**
- ExitPlan = statisch snapshot (1 TP)
- StrategyDirective kan suggereren: partial_exit_levels [50%, 50%]
- ExecutionHandler gebruikt hint, maakt 2 child orders
- SRP: DTO = snapshot, Handler = execution logic

### **Q2: TWAP Parameters - Waar?**

**User's keuze:** Platform config (niet in RoutingPlan)

**Rationale:**
- RoutingPlan zegt alleen: timing="TWAP"
- Platform heeft fixed TWAP algorithm (10 min, 5 chunks)
- Quant configureert in platform.yaml, niet per trade
- Uniform algorithms - trade kiest strategie, platform bepaalt implementatie

### **Q3: Trailing/Breakeven - Waar?**

**User's keuze:** Aparte PositionMonitor worker (niet in ExitPlan)

**Rationale:**
- ExitPlan = statisch (SL = $49,500)
- TrailingStopWorker (scheduled) monitort position
- Publiceert nieuwe ExitPlan bij update (SL = $50,100)
- ExecutionHandler ziet nieuwe plan, update order
- SRP: Plan = snapshot, Worker = dynamiek

### **Q4: Timing Field - Entry of Routing?**

**Conclusie:** ROUTING (niet entry)

**Rationale:**
- Entry = "WAAR kom ik binnen?" (MARKET vs LIMIT vs STOP_LIMIT)
- Routing = "HOE/WANNEER voer ik uit?" (IMMEDIATE vs TWAP vs LAYERED)
- TWAP is execution tactic, niet order type
- SRP: Entry = trade parameters, Routing = execution tactics

---

## 📚 Documentatie Status

### **Nieuwe Documenten (Gecommit)**

1. ✅ `docs/development/STRATEGY_PIPELINE_ARCHITECTURE.md`
   - Leidend document voor pipeline discussies
   - 1200+ regels complete architectuur
   - Vervangt versnipperde info

2. ✅ `docs/development/ROUTING_PLANNER_DEEP_DIVE.md`
   - Concrete uitleg routing execution tactics
   - 400+ regels met voorbeelden

3. ✅ `docs/TODO.md` (updated)
   - Referenties naar nieuwe docs

### **Te Updaten (Later)**

- `agent.md` - Verwijder duplicate pipeline tekst, add reference
- `TODO.md` - Update DTO implementation tasks met nieuwe inzichten

---

## 🚀 Volgende Stappen - Implementation Roadmap

### **Immediate Next (Klaar voor implementatie):**

1. **EntryPlan Refactor**
   - Verwijder: created_at, planner_id, timing, reference_price, valid_until, planner_metadata, rationale, max_slippage_pct
   - Houd: plan_id, symbol, direction, order_type, limit_price, stop_price
   - Update tests (verwacht RED phase)

2. **SizePlan Refactor**
   - Verwijder: created_at, planner_id, rationale, planner_metadata, max_position_value, account_risk_pct, valid_until
   - Houd: plan_id, position_size, position_value, risk_amount, leverage
   - Update tests (verwacht RED phase)

3. **ExitPlan DTO (Nieuw)**
   - Create: plan_id, stop_loss_price, take_profit_price
   - Tests vanaf scratch (RED → GREEN)

4. **RoutingPlan DTO (Nieuw)**
   - Create: plan_id, timing, time_in_force, max_slippage_pct, execution_urgency, iceberg_preference
   - Tests vanaf scratch (RED → GREEN)

5. **Test Refactor (RED → GREEN)**
   - Fix alle broken tests
   - Validate military datetime IDs
   - Target: all tests GREEN

### **Later (Platform Components):**

6. **PlanningAggregator** (Platform worker)
   - Aggregates 4 plans → ExecutionDirective
   - Mode detection (Direct vs SWOT)

7. **DirectiveAssembler** (Mogelijk duplicate met PlanningAggregator?)
   - Check: Is dit hetzelfde component?

8. **FlowTerminator** (Platform worker)
   - Causality reconstruction via TriggerContext
   - Journal writes, cleanup

---

## 🎨 Git Status

**Current Branch:** `main`  
**Last Commit:** `1f208e4` - "docs: add definitive Strategy Pipeline Architecture + Routing Planner deep dive"

**Committed Files:**
- docs/development/STRATEGY_PIPELINE_ARCHITECTURE.md (nieuw)
- docs/development/ROUTING_PLANNER_DEEP_DIVE.md (nieuw)
- docs/TODO.md (updated)

**Working Tree:** Clean ✅

**Remote:** Synced met origin/main (remote heeft CausalityChain implementation)

---

## 💡 Key Takeaways - Wat Je Moet Weten

### **1. Planners Zijn DOM - Config Is SLIM**

Dit is het centrale pattern:

```yaml
# Quant definieert ranges in YAML
planning:
  entry:
    - plugin: "AggressiveMarketEntry"
      triggers: {confidence: [0.8, 1.0]}
```

```python
# Planner blijft dom - filtering via injected PlannerMatcher
class BaseEntryPlanner:
    def should_handle(self, directive: StrategyDirective) -> bool:
        return self.matcher.matches(confidence=directive.confidence)
```

**Geen quant logic in planner code** - alleen specialisatie (MARKET vs LIMIT)

### **2. DTOs = Snapshots, Workers = Dynamiek**

- ExitPlan = statisch ($49,500 stop)
- TrailingStopWorker = dynamisch (publiceert nieuwe ExitPlan @ $50,100)
- ExecutionHandler ziet nieuwe plan, update order

**SRP:** DTO state, Worker behavior

### **3. Event-Driven, Niet Operator-Driven**

**GEEN Operators** - alleen EventAdapters + wiring_map.yaml

```yaml
event_wirings:
  - event: "ENTRY_PLAN_CREATED"
    subscribers:
      - worker: "planning_aggregator"
        method: "on_entry_plan"
```

Workers zijn bus-agnostic, EventAdapters handle routing.

### **4. Causality = Alleen in Directive/Aggregation DTOs**

- StrategyDirective: heeft causality ✅
- EntryPlan/SizePlan/ExitPlan/RoutingPlan: **GEEN causality** ❌
- ExecutionDirective: heeft causality ✅

BaseWorker boilerplate bepaalt later propagation.

### **5. Confidence Drives Everything**

```
SWOT Confrontatie → confidence=0.85
    ↓
AggressiveMarketEntry filters [0.8-1.0] ✅ Match
    ↓
Output: IMMEDIATE market order, 1% slippage OK
```

Hele pipeline gestuurd door confidence score uit StrategyPlanner.

---

## 🔧 Development Environment

**Python:** 3.13.9 (venv @ d:\1Voudig\99_Programming\st3)  
**Repository:** S1mpleTraderV3 (GitHub: MikeyVK/S1mpleTraderV3)  
**Current Tests:** 246 passing (remote state)

**Tools:**
- Pytest (unit tests)
- Pylance (type checking)
- Military datetime IDs (PREFIX_YYYYMMDD_HHMMSS_xxxxx)

---

## 📞 Open Questions (Voor User)

1. **PlanningAggregator vs DirectiveAssembler**
   - Zijn dit dezelfde componenten?
   - TODO.md noemt beide - mogelijk duplicate?

2. **ExitPlan: take_profit_price singular of plural?**
   - Huidige gedachte: singular (Decimal | None)
   - Partial exits = ExecutionHandler verantwoordelijkheid

3. **RoutingPlan: execution_strategy field nodig?**
   - Of is timing voldoende?
   - V2 had execution_strategy: "twap" - is dit hetzelfde als timing?

---

## 🎯 Session Summary

**Wat we bereikten:**
- ✅ Complete pipeline architectuur gedocumenteerd (leidend document)
- ✅ Routing planner uitgelegd (was onduidelijk, nu concreet)
- ✅ DTO specificaties definitief (klaar voor implementatie)
- ✅ Architecturale patterns geborgd (confidence-driven, bus-agnostic, SRP)
- ✅ Alle commits gedaan, working tree clean

**Ready for implementation:**
- Alle DTOs gespecificeerd met exacte fields
- Rationale gedocumenteerd voor elke keuze
- V2 patterns gevalideerd
- TDD roadmap helder (RED → GREEN per DTO)

**Volgende sessie:**
Start EntryPlan refactor - verwijder feature creep, fix tests, validate architecture.

---

**Overdracht Compleet** ✅  
**Veel succes op andere machine!** 🚀
