# Scenario: Advanced Modification Flows

Dit document toetst de `target_plan_ids` abstractie aan de hand van drie complexe modificatie-scenario's, naast de reeds gevalideerde Trailing Stop.

## De Kernvraag
Houdt de abstractie stand?
*   **Abstractie:** `StrategyPlanner` praat tegen `TradePlan` (Level 1).
*   **Implementatie:** `ExecutionWorker` praat tegen `Order` (Level 3) via `IExecutionConnector`.

---

## Scenario 1: Trailing Stop (Reeds Gevalideerd)
*   **Intentie:** "Verklein risico, zet stop op 1%."
*   **Directive:** `MODIFY_EXISTING`, `target_plan_ids=["TPL_1"]`, `exit_directive={stop_loss_tolerance: 0.01}`.
*   **Vertaling:** Zoek open SL order -> `MODIFY_ORDER` (nieuwe prijs).
*   **Status:** ✅ Geslaagd.

---

## Scenario 2: Scale In (Pyramiding)
De strategie ziet bevestiging en wil de positie vergroten.

### Stap 1: StrategyPlanner
*   **Situatie:** `TPL_1` is actief, 1 BTC long. Prijs breekt weerstand.
*   **Intentie:** "Koop 0.5 BTC erbij."
*   **Actie:**
    ```json
    {
      "scope": "MODIFY_EXISTING", // Of ADD_TO_POSITION? (Zie discussie onder)
      "target_plan_ids": ["TPL_1"],
      "size_directive": {
        "position_size": 0.5, // Delta? Of Totaal? (Zie discussie)
        "aggressiveness": 0.8
      },
      "entry_directive": {
        "direction": "BUY",
        "order_type": "MARKET"
      }
    }
    ```

### Stap 2: ExecutionWorker
*   **Context:** Ziet `target_plan_ids=["TPL_1"]`. Weet dat dit een "Scale In" is omdat er een `entry_directive` bij zit voor een bestaand plan.
*   **Vertaling:**
    *   Dit is géén modificatie van een bestaande order (want we willen *meer*).
    *   Dit is een **nieuwe order** die gekoppeld moet worden aan het bestaande plan.
*   **Output (via IExecutionConnector):**
    ```json
    {
      "action": "EXECUTE_TRADE", // Nieuwe order!
      "parent_plan_id": "TPL_1", // Koppel aan bestaand plan
      "quantity": 0.5,
      "type": "MARKET"
    }
    ```

### Stap 3: ExecutionHandler
*   Voert order uit.
*   Voegt `ORD_NEW_1` toe aan `ExecutionGroup` van `TPL_1`.
*   `StrategyLedger` update: `TPL_1` heeft nu 1.5 BTC.

*   **Status:** ✅ Geslaagd. De abstractie werkt. De StrategyPlanner hoeft niet te weten dat dit een *nieuwe* order vereist; hij zegt gewoon "Ik wil dit plan vergroten".

---

## Scenario 3: Partial Take Profit (Scale Out)
De strategie wil winst veiligstellen (50% sluiten).

### Stap 1: StrategyPlanner
*   **Situatie:** `TPL_1` (1.5 BTC) staat op dikke winst.
*   **Intentie:** "Sluit 50% van de positie (0.75 BTC)."
*   **Actie:**
    ```json
    {
      "scope": "MODIFY_EXISTING",
      "target_plan_ids": ["TPL_1"],
      "size_directive": {
        "position_size": -0.75 // Negatief voor verkleinen? Of expliciete 'close_fraction'?
      },
      "entry_directive": {
        "direction": "SELL", // Tegenovergestelde richting
        "order_type": "MARKET"
      }
    }
    ```

### Stap 2: ExecutionWorker
*   **Context:** Ziet `direction="SELL"` terwijl Plan `BUY` is. Conclusie: Reduce Position.
*   **Vertaling:**
    *   Maak nieuwe Sell Order voor 0.75 BTC.
    *   Koppel aan `TPL_1`.
*   **Output:** `EXECUTE_TRADE` (Sell 0.75).

*   **Status:** ✅ Geslaagd. Wederom, StrategyPlanner denkt in "Plan aanpassing", ExecutionWorker regelt de orders.

---

## Scenario 4: Emergency Flatten (Panic)
RiskMonitor detecteert Black Swan. Alles moet NU dicht.

### Stap 1: StrategyPlanner (Risk Mode)
*   **Situatie:** Markt crasht.
*   **Intentie:** "SLUIT ALLES NU!"
*   **Actie:**
    ```json
    {
      "scope": "CLOSE_EXISTING",
      "target_plan_ids": ["TPL_1", "TPL_2", "TPL_3"], // Batch!
      "execution_directive": {
        "execution_urgency": 1.0, // Panic mode
        "max_total_slippage_pct": 0.05  // Accepteer 5% slippage
      }
    }
    ```

### Stap 2: ExecutionWorker
*   **Context:** `CLOSE_EXISTING` op lijst plannen.
*   **Vertaling:**
    *   Voor elk plan:
        1.  Annuleer alle open orders (Limit buys, Stop losses).
        2.  Kijk naar `net_position`.
        3.  Indien `net_position != 0`: Stuur Market Close order.
*   **Output:** Batch van `CANCEL_ALL` en `MARKET_CLOSE` orders.

*   **Status:** ✅ Geslaagd. Dit is de ultieme test. De StrategyPlanner stuurt 1 simpele directive, de ExecutionWorker genereert misschien wel 20 API calls (cancels + closes) via IExecutionConnector.

---

## Conclusie & Verfijning
De abstractie `target_plan_ids` houdt stand in alle scenario's. Het stelt de `StrategyPlanner` in staat om **intentie** te communiceren zonder **implementatie** (orders) te kennen.

**Aandachtspunt voor Implementation:**
Bij Scenario 2 (Scale In) en 3 (Scale Out) moeten we duidelijke afspraken maken over hoe `SizeDirective` werkt bij modificatie:
*   Is `position_size` absoluut ("Ik wil totaal 1.5 BTC hebben")?
*   Of relatief ("Voeg 0.5 BTC toe")?

*Advies:* **Absoluut** is veiliger (idempotent).
*   StrategyPlanner leest huidige size (1.0).
*   Berekent nieuwe size (1.5).
*   Stuurt `size_directive(position_size=1.5)`.
*   ExecutionWorker ziet verschil (1.5 - 1.0 = +0.5) en koopt het verschil bij.
*   Dit voorkomt dat per ongeluk 2x 0.5 wordt gekocht als het bericht dubbel verwerkt wordt.
