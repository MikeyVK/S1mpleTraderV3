# Scenario: Trailing Stop Modificatie Flow

Dit document beschrijft stap-voor-stap hoe een **Trailing Stop** update door de pipeline vloeit, om de abstractie van `target_plan_ids` te valideren.

## De Spelers
1.  **StrategyPlanner (Level 1):** De "General". Beslist *dat* de stop omhoog moet. Kent alleen het `TradePlan`.
2.  **ExitPlanner (Level 1.5):** De "Specialist". Rekent de exacte prijs uit.
3.  **ExecutionTranslator (Level 2):** De "Vertaler". Zoekt de orders erbij en maakt de technische instructie.
4.  **ExecutionHandler (Level 3):** De "Uitvoerder". Praat met de exchange.

## De Situatie
*   **Active TradePlan:** `TPL_BTC_001` (Long BTCUSDT).
*   **Huidige Prijs:** $102,000.
*   **Huidige Stop Loss:** $100,000.
*   **Trigger:** Tick update ($102,000).

---

### Stap 1: StrategyPlanner (De Beslissing)
De `TrailingStopStrategy` ontvangt de tick. Hij vraagt de `StrategyLedger` naar de status van `TPL_BTC_001`.
*   *Analyse:* "Prijs is $2k gestegen. Ik wil mijn risico verkleinen. Ik wil de stop 'tighten' naar 1% onder de huidige prijs."
*   *Actie:* Publiceer `StrategyDirective`.

**Output (StrategyDirective):**
```json
{
  "directive_id": "STR_002",
  "scope": "MODIFY_EXISTING",
  "target_plan_ids": ["TPL_BTC_001"],  // <--- REFERENTIE NAAR HET PLAN (Niet de order!)
  "confidence": 1.0,
  "exit_directive": {
    "stop_loss_tolerance": 0.01  // "Zet stop op 1% afstand"
  }
  // Entry/Size/Routing directives zijn leeg (geen wijziging nodig)
}
```

### Stap 2: ExitPlanner (De Berekening)
De `ExitPlanner` ontvangt de directive. Hij ziet `MODIFY_EXISTING` en een `exit_directive`.
*   *Input:* Huidige prijs ($102,000), Tolerance (0.01).
*   *Berekening:* $102,000 * (1 - 0.01) = $100,980.
*   *Actie:* Publiceer `ExitPlan`.

**Output (ExitPlan):**
```json
{
  "plan_id": "EXT_002",
  "stop_loss_price": 100980.00,
  "take_profit_price": null // Geen wijziging
}
```

### Stap 3: PlanningAggregator (De Bundeling)
Bundelt het plan in een `ExecutionDirective`.

**Output (ExecutionDirective):**
```json
{
  "directive_id": "EXE_002",
  "target_plan_ids": ["TPL_BTC_001"], // Propageert de target
  "exit_plan": { "stop_loss_price": 100980.00 },
  "causality": [...]
}
```

### Stap 4: ExecutionTranslator (De Vertaling)
Hier gebeurt de magie. De Translator moet de abstracte wens ("Update TPL_BTC_001") vertalen naar concrete orders.

*   *Lookup:* "StrategyLedger, geef mij alle open orders voor `TPL_BTC_001`."
*   *Resultaat:* `["ORD_BINANCE_555"]` (De huidige Stop Loss order).
*   *Logica:* "Ik moet `ORD_BINANCE_555` aanpassen naar prijs $100,980."
*   *Actie:* Genereer `ConnectorExecutionSpec`.

**Output (ConnectorExecutionSpec - CEX):**
```json
{
  "action": "MODIFY_ORDER",
  "order_id": "ORD_BINANCE_555",
  "new_stop_price": 100980.00
}
```

### Stap 5: ExecutionHandler (De Uitvoering)
Stuurt het request naar Binance: `cancel_replace_order(id="ORD_BINANCE_555", price=100980.00)`.

---

## Conclusie
Door `target_plan_ids` te gebruiken:
1.  **SRP is gewaarborgd:** De `StrategyPlanner` hoeft niet te weten dat er toevallig order `ORD_BINANCE_555` loopt. Hij managet zijn *Plan*.
2.  **Flexibiliteit:** Als de positie uit 10 kleine orders bestond (ladder), had de `ExecutionTranslator` in Stap 4 besloten om *alle 10* orders te updaten, zonder dat de StrategyPlanner daar logica voor hoeft te hebben.
3.  **Correcte Abstractie:** De StrategyPlanner praat "Business Logic" (Risk management), de Translator praat "Infra Logic" (Order IDs).
