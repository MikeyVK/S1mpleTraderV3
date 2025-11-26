# Concrete Execution Scenario: Integrated Protection (Corrected)

Dit document corrigeert het scenario naar aanleiding van de feedback: **Stop Loss is onderdeel van de TWAP Algo en leeft op de Exchange.**

## 1. Het Scenario: "Institutional Entry with Native Protection"
**Doel:** Koop 10 BTC via TWAP.
**Protectie:** Stop Loss op 90k.
**Principe:** Geen platform-side monitoring (latency risk), maar echte Exchange Orders.

## 2. De Rol van de RoutingPlanner
De `RoutingPlanner` configureert **één** algoritme met parameters.

**Output (ExecutionDirective):**
```json
{
  "plan_id": "TPL_BTC_001",
  "instructions": [
    {
      "intent": "ENTRY_WITH_PROTECTION",
      "algo_type": "TWAP",
      "params": { 
          "duration": 60, 
          "slices": 12,
          "stop_loss_price": 90000  <-- Parameter van de TWAP
      }
    }
  ]
}
```

## 3. De ExecutionService & TwapAlgo
De Service start **één** instantie: `TwapAlgo`.

### De Logica (Integrated Protection)
De `TwapAlgo` beheert nu twee dingen:
1.  De **Entry Orders** (de chunks).
2.  De **Stop Loss Order** (de protectie op de exchange).

## 4. De Concrete Event Flow

### Stap 1: Start (T=0)
*   **TwapAlgo:** Plaatst Order 1 (Buy 0.83 BTC Limit/Market).
*   **TwapAlgo:** Plaatst (optioneel) alvast een Stop Loss order voor 0 BTC (indien exchange dat toestaat) of wacht op eerste fill.

### Stap 2: Fill Chunk 1 (T=1 min)
*   **Event:** `ORDER_FILLED` (Order 1 gevuld, 0.83 BTC).
*   **TwapAlgo:**
    1.  Registreert voortgang (Chunk 1 done).
    2.  **CRUCIAAL:** Stuurt `UpdateOrder` (of `PlaceOrder`) naar Exchange:
        *   *"Zet Stop Loss op 90k voor size 0.83 BTC."*
    *   Nu staat de protectie **op de exchange**.

### Stap 3: Timer (T=5 min)
*   **Event:** `TIMER_EXPIRED`.
*   **TwapAlgo:** Plaatst Order 2 (Buy 0.83 BTC).

### Stap 4: Fill Chunk 2 (T=6 min)
*   **Event:** `ORDER_FILLED` (Order 2 gevuld).
*   **TwapAlgo:**
    1.  Totaal nu 1.66 BTC.
    2.  Stuurt `UpdateOrder` naar Exchange:
        *   *"Verhoog Stop Loss size naar 1.66 BTC."*

### Stap 5: Crash (T=7 min)
*   **Gebeurtenis:** Prijs zakt naar 89k.
*   **Actie:** De **Exchange** triggert de Stop Loss order.
*   **Event:** `ORDER_FILLED` (Stop Loss Executed).
*   **TwapAlgo:**
    1.  Ziet dat SL is afgegaan.
    2.  Cancelt resterende TWAP chunks (Emergency Stop).
    3.  Meldt `finish("Stopped out")`.

## 5. Conclusie
Dit model is veel robuuster:
1.  **Geen Latency:** De stop loss staat op de exchange. Als de prijs crasht, ben je direct uit, zelfs als onze bot offline is.
2.  **Simpelere Architectuur:** Geen coördinatie tussen twee algo's. De `TwapAlgo` is eigenaar van de hele flow.
3.  **Event Driven op Fills:** We reageren alleen op `ORDER_FILLED` (om de SL te updaten) en `TIMER` (voor chunks). Geen dure `MARKET_TICK` processing nodig.

Dit is de juiste "Native-First" benadering.
