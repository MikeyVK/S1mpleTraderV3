# Deep Dive: What is an ExecutionAlgorithm?

Dit document definieert de **harde grenzen** en **verantwoordelijkheden** van een `ExecutionAlgorithm` binnen S1mpleTraderV3.

## 1. De Definitie
Een `ExecutionAlgorithm` is een **Gespecialiseerde Worker** die verantwoordelijk is voor de tactische uitvoering van een `ExecutionDirective`.

### Wat het WEL is (Tactisch)
*   **TWAP:** "Hak deze 10 BTC in stukjes over tijd."
*   **Iceberg:** "Verberg deze 10 BTC order in het boek."
*   **POV:** "Koop mee met 10% van het marktvolume."
*   **Pegged:** "Blijf 1 tick boven de Best Bid."

### Wat het NIET is (Strategisch)
*   **Grid:** "Koop op 10k, 11k, 12k." (Dit is een Strategie die *meerdere* besluiten neemt).
*   **DCA:** "Koop elke maandag." (Dit is een Strategie die *periodieke* besluiten neemt).

> **Vuistregel:** Als het algoritme bepaalt *OF* we blootstelling aangaan, is het een Strategie. Als het bepaalt *HOE* we die blootstelling verkrijgen, is het een ExecutionAlgorithm.

## 2. De Relatie met RoutingPlanner
De `RoutingPlanner` (of `ExecutionPlanner`) is de strateeg.

*   **Rol:** De Strateeg.
*   **Output:** `ExecutionPlan` (De 4e pijler naast Entry, Size, Exit).
*   **Inhoud:** Universele trade-offs (Urgency, Visibility) en hints (`preferred_execution_style="TWAP"`).

## 3. De ExecutionDirective (De Complete Instructie)
De `ExecutionService` ontvangt de **ExecutionDirective**. Dit is de "Master Instruction" vanuit de `PlanningAggregator`.

```python
class ExecutionDirective(BaseModel):
    # Context & Causality (Het "Waarom")
    directive_id: str
    causality: CausalityChain
    
    # De 4 Sub-Plannen (Het "Wat")
    entry_plan: EntryPlan      # "Koop BTC Limit @ 95k"
    size_plan: SizePlan        # "10.0 Units"
    exit_plan: ExitPlan        # "Stop @ 90k, Target @ 100k"
    execution_plan: ExecutionPlan # "Urgency=Low, Style=TWAP" <-- Consistent Naming
```

## 4. De ExecutionGroup (De Dynamic State)
Elk draaiend `ExecutionAlgorithm` is **Eigenaar** van precies één `ExecutionGroup`.

*   **ExecutionGroup:** De DTO in de `StrategyLedger` die de **runtime state** bevat.

### De Interactie: Algo als Worker
De Algo werkt volgens het **Point-in-Time** principe, net als andere Workers. Hij krijgt geen data "geduwd" door de Service, maar haalt het op via Providers.

1.  **ExecutionService:**
    *   Managet Lifecycle (Start/Stop).
    *   Roept `algo.process()` aan (op basis van triggers).
2.  **ExecutionAlgorithm (in `process()`):**
    *   `self.ledger_provider.get_execution_group(id)` -> Haalt eigen state op.
    *   `self.market_data_provider.get_current_tick()` -> Haalt markt data op.
    *   `self.strategy_cache.get_directive()` -> Haalt instructies op.
    *   **Logic:** Beslist en update `ExecutionGroup`.
    *   `self.ledger_provider.update_execution_group(group)` -> Slaat state op.

## 5. Samenvatting van de Chain

1.  **StrategyPlanner:** "Ik wil 10 BTC hebben."
2.  **RoutingPlanner:** "Doe maar via TWAP." -> `ExecutionPlan`.
3.  **PlanningAggregator:** Bundelt in `ExecutionDirective`.
4.  **ExecutionService:** Start `TwapAlgo`.
5.  **TwapAlgo:**
    *   Haalt Directive (Cache) en Group (Ledger).
    *   Ziet: "Ik moet nog 5 chunks."
    *   Plaatst order via `ExecutionConnector`.

Hiermee is de Algo een volwaardige burger in het Worker-ecosysteem: **State via Ledger, Data via Providers, Logica in Process.**
