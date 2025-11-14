# Issue #6: ExecutionDirectiveBatch Coordination - Discussion Status

**Date:** 2025-11-13  
**Status:** OPEN - Architectural Design Phase  
**Related:** TODO.md Issue #6

---

## Problem Statement

ExecutionDirectiveBatch heeft velden die batch-level execution coordination specificeren:
- `execution_mode` (SEQUENTIAL / PARALLEL / ATOMIC)
- `timeout_seconds` (batch timeout)
- `rollback_on_failure` (rollback policy)

**Kernvraag:** Wie bepaalt deze waarden en op basis waarvan?

**Current State:** PlanningAggregator hardcodeert deze waarden (execution_mode=ATOMIC altijd).

---

## Discussion Progress

### 1. Fundamentele Analyse (2025-11-13)

**Wat is een ExecutionDirective?**
- Complete uitvoerbare instructie voor 1 trade
- Bevat 4 plans: Entry, Size, Exit, Execution
- Frozen (immutable), met causality tracking

**Wat is een verzameling ExecutionDirectives?**
- N trades die samen uitgevoerd moeten worden
- Ontstaan uit 1 StrategyDirective
- Voorbeelden: pair trade (BTC+ETH), hedged entry (main+hedges)

**Wat betekent dit voor ExecutionHandler?**
ExecutionHandler moet 3 beslissingen nemen:

1. **Volgorde:** Parallel / Sequentieel / Specifieke volgorde?
2. **Falen:** Best-effort / Stop direct / Rollback alles?
3. **Tijd:** Onbeperkt / Timeout / Per-directive timeout?

### 2. Kernvraag: Wie Bepaalt Batch Coordination?

**Observatie:** Deze 3 vragen (volgorde, falen, tijd) gaan specifiek over de verzameling directives die op moment T zijn ontstaan, onder regie van de StrategyPlanner.

**→ Dit suggereert dat StrategyPlanner deze beslissingen moet kunnen sturen.**

### 3. Analyse: Kan StrategyDirective dit communiceren?

**Huidige StrategyDirective interface:**
```python
StrategyDirective(
    scope=DirectiveScope.NEW_TRADE,
    confidence=Decimal("0.85"),
    target_trade_ids=[],
    
    # Sub-directives (PER trade):
    entry_directive=EntryDirective(...),    # 1 symbol
    size_directive=SizeDirective(...),      # 1 risk amount
    exit_directive=ExitDirective(...),      # 1 stop/target
    routing_directive=ExecutionDirective(...)  # 1 execution urgency
)
```

**Probleem voor pair trade (BTC long + ETH short):**

1. **Multipliciteit:** Geen manier om "2 trades" te communiceren
   - `entry_directive.symbol` = 1 symbol (niet 2)
   - Geen lijst van sub-directives

2. **Batch coordination:** Geen manier om te zeggen:
   - "Voer parallel uit"
   - "Als één faalt, cancel de ander (ATOMIC)"
   - "60 seconden timeout voor beide"

**→ CONCLUSIE:** StrategyDirective kan momenteel NIET batch-level policies communiceren.

---

## Open Questions

### Q1: Heeft StrategyDirective multipliciteit nodig?

**Scenario:** Pair trade vereist 2 ExecutionDirectives (BTC + ETH)

**Opties:**
- **A:** StrategyDirective blijft single-trade, StrategyPlanner produceert 2 StrategyDirectives
- **B:** StrategyDirective krijgt lijst van sub-directives (multi-trade in 1 directive)
- **C:** Intermediair object tussen StrategyDirective en ExecutionDirective

**Status:** NIET BESPROKEN

### Q2: Moet StrategyDirective batch policies kunnen sturen?

**Als JA:**

**Optie A: Uitbreiden StrategyDirective**
```python
class StrategyDirective:
    # ... bestaande fields ...
    
    # NIEUW: Batch-level coordination
    batch_execution_policy: BatchExecutionPolicy | None = None
```

**Optie B: Aparte BatchPolicy directive**
```python
# StrategyPlanner produceert 2 outputs:
1. StrategyDirective (trade constraints)
2. BatchPolicy (execution coordination)
```

**Optie C: Impliciet via interpreter**
```python
# PlanningAggregator heeft configureerbare interpreter
interpreter.derive_batch_policy(
    strategy_directive=...,
    directives=...
)
# Leest signals (scope, confidence, urgency) en BESLUIT
```

**Pro/Con:**
- **Optie A:** Expliciet, StrategyPlanner heeft controle, maar kent execution details
- **Optie B:** Separation of concerns, maar meer DTOs
- **Optie C:** Indirecte controle, configureerbaar, geen nieuwe DTOs

**Status:** VRAAG GESTELD, NIET BEANTWOORD

### Q3: Moeten batch policies expliciet of impliciet zijn?

**Expliciet:** BatchExecutionPolicy DTO (StrategyPlanner geeft duidelijke instructie)
**Impliciet:** Interpreter met config (PlanningAggregator interpreteert signals)

**Trade-off:**
- Expliciet = meer controle, maar meer kennis vereist van StrategyPlanner
- Impliciet = minder controle, maar configureerbaar en separation of concerns

**Status:** VRAAG GESTELD, NIET BEANTWOORD

### Q4: Hoe configureerbaar moet dit zijn?

- Per strategy verschillende batch policies?
- Runtime configureerbaar (thresholds)?
- Plugin-based (verschillende interpreters)?

**Status:** NIET BESPROKEN

---

## Related Design Tensions

### 1. TradePlan vs StrategyDirective (temp.md)

**Context:** Er wordt gewerkt aan trade_lifecycle.md met TradePlan DTO concept.

**TradePlan concept:**
- Container voor complete set: orders → fills → positions → results
- Geboren bij StrategyPlanner
- Sterft bij StrategyLedger (laatste close) of StrategyJournalWriter (journaling)

**Relatie met StrategyDirective:** Nog onduidelijk
- Is TradePlan een container waarin StrategyDirective zit?
- Of is StrategyDirective de geboorte van TradePlan?

**Status:** PARALLEL DISCUSSIE, NIET GEÏNTEGREERD

### 2. ExecutionDirective Naming Conflict

**Issue:** Twee klassen genaamd `ExecutionDirective`:
1. `backend/dtos/strategy/strategy_directive.py` line 164 - Sub-directive (routing constraints)
2. `backend/dtos/execution/execution_directive.py` - Execution layer DTO

**TODO item:** Rename strategy sub-directive → `RoutingDirective`

**Status:** GEÏDENTIFICEERD, NIET OPGELOST

---

## Next Steps

**Immediate:**
1. Beantwoorden Q1: Multipliciteit in StrategyDirective?
2. Beantwoorden Q2: Welke optie voor batch policies (A/B/C)?
3. Beantwoorden Q3: Expliciet vs impliciet?

**Integration:**
4. Integreer TradePlan concept discussie
5. Resolve ExecutionDirective naming conflict

**Documentation:**
6. Document final decision in TODO.md Issue #6
7. Update DTO_ARCHITECTURE.md met gekozen oplossing
8. Update PLANNING_AGGREGATOR_DESIGN.md met implementatie

---

## Decision Criteria

**Wat is belangrijk bij de keuze?**
1. **Separation of concerns:** StrategyPlanner moet niet execution details kennen
2. **Configureerbaar:** Verschillende strategies verschillende policies
3. **Explicitheid:** Duidelijke communicatie tussen componenten
4. **Simpliciteit:** Niet meer complexiteit dan nodig
5. **Testbaarheid:** Behavior moet testbaar zijn

**Nog te bepalen:** Prioritering van deze criteria

---

**Status:** Wachtend op architectuurbeslissing over Q1-Q3
