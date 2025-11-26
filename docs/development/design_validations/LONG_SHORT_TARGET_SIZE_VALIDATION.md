# Long/Short Target Size Validation

## Design Guideline: Self-Descriptive Naming
**Besluit:** `position_size` → **`target_position_size`**
*   Maakt expliciet dat dit de *gewenste eindstaat* is, niet de huidige of delta.
*   Consistent met andere "target" velden in het systeem.

---

## Scenario Matrix: Long vs Short met Modificaties

### Definitie van Termen
*   **`target_position_size`:** Gewenste absolute positie (altijd positief getal).
*   **`direction`:** `BUY` (long) of `SELL` (short).
*   **`current_position`:** Huidige positie (positief = long, negatief = short).

---

## Scenario 1: LONG Position Lifecycle

### 1A. Initial Entry (NEW_TRADE)
```json
{
  "scope": "NEW_TRADE",
  "entry_directive": { "direction": "BUY" },
  "size_directive": { "target_position_size": 1.0 }
}
```
*   **Translator Logic:** `current = 0`, `target = 1.0`, `delta = +1.0`
*   **Action:** BUY 1.0 BTC
*   **Result:** Position = +1.0 BTC (long)

### 1B. Scale In (MODIFY_EXISTING)
```json
{
  "scope": "MODIFY_EXISTING",
  "target_plan_ids": ["TPL_1"],
  "size_directive": { "target_position_size": 1.5 }
}
```
*   **Translator Logic:** `current = +1.0`, `target = 1.5`, `delta = +0.5`
*   **Action:** BUY 0.5 BTC
*   **Result:** Position = +1.5 BTC (long)

### 1C. Partial Take Profit (MODIFY_EXISTING)
```json
{
  "scope": "MODIFY_EXISTING",
  "target_plan_ids": ["TPL_1"],
  "size_directive": { "target_position_size": 0.75 }
}
```
*   **Translator Logic:** `current = +1.5`, `target = 0.75`, `delta = -0.75`
*   **Action:** SELL 0.75 BTC
*   **Result:** Position = +0.75 BTC (long)

### 1D. Full Close (CLOSE_EXISTING)
```json
{
  "scope": "CLOSE_EXISTING",
  "target_plan_ids": ["TPL_1"],
  "size_directive": { "target_position_size": 0.0 }
}
```
*   **Translator Logic:** `current = +0.75`, `target = 0.0`, `delta = -0.75`
*   **Action:** SELL 0.75 BTC
*   **Result:** Position = 0.0 (flat)

**Status:** ✅ Long scenario werkt perfect.

---

## Scenario 2: SHORT Position Lifecycle

### 2A. Initial Entry (NEW_TRADE)
```json
{
  "scope": "NEW_TRADE",
  "entry_directive": { "direction": "SELL" },
  "size_directive": { "target_position_size": 1.0 }
}
```
*   **Translator Logic:** `current = 0`, `target = -1.0` (short), `delta = -1.0`
*   **Action:** SELL 1.0 BTC
*   **Result:** Position = -1.0 BTC (short)

**WAIT! Probleem gedetecteerd:**
Als `target_position_size` altijd positief is, hoe weet de Translator dat dit een SHORT moet zijn?

**Oplossing:**
De `direction` uit `EntryDirective` bepaalt het teken:
*   `direction = BUY` → `target_position_size` = positief
*   `direction = SELL` → `target_position_size` = negatief (intern)

### 2B. Scale In (SHORT vergroten)
```json
{
  "scope": "MODIFY_EXISTING",
  "target_plan_ids": ["TPL_2"],
  "size_directive": { "target_position_size": 1.5 }
}
```
*   **Context:** Plan is SHORT (direction = SELL).
*   **Translator Logic:** `current = -1.0`, `target = -1.5`, `delta = -0.5`
*   **Action:** SELL 0.5 BTC (meer short)
*   **Result:** Position = -1.5 BTC (short)

### 2C. Partial Cover (SHORT verkleinen)
```json
{
  "scope": "MODIFY_EXISTING",
  "target_plan_ids": ["TPL_2"],
  "size_directive": { "target_position_size": 0.75 }
}
```
*   **Translator Logic:** `current = -1.5`, `target = -0.75`, `delta = +0.75`
*   **Action:** BUY 0.75 BTC (cover)
*   **Result:** Position = -0.75 BTC (short)

### 2D. Full Close
```json
{
  "scope": "CLOSE_EXISTING",
  "target_plan_ids": ["TPL_2"],
  "size_directive": { "target_position_size": 0.0 }
}
```
*   **Translator Logic:** `current = -0.75`, `target = 0.0`, `delta = +0.75`
*   **Action:** BUY 0.75 BTC (cover)
*   **Result:** Position = 0.0 (flat)

**Status:** ✅ Short scenario werkt, mits Translator de `direction` van het Plan kent.

---

## Kritieke Inzicht: Direction Context

De `target_position_size` is altijd een **magnitude** (positief getal).
Het **teken** (long/short) wordt bepaald door:
1.  **Bij NEW_TRADE:** `EntryDirective.direction` (BUY = long, SELL = short).
2.  **Bij MODIFY_EXISTING:** De Translator leest de `TradePlan.direction` uit de Ledger.

**Translator Pseudo-code:**
```python
def calculate_delta(plan_id: str, target_size: Decimal) -> Decimal:
    plan = ledger.get_plan(plan_id)
    current_size = plan.net_position  # +1.5 (long) of -1.5 (short)
    
    # Bepaal target met teken
    if plan.direction == "BUY":
        target_signed = target_size  # Positief
    else:  # SELL
        target_signed = -target_size  # Negatief
    
    delta = target_signed - current_size
    return delta  # Positief = BUY meer, Negatief = SELL meer
```

---

## Conclusie & Implementatie

### ✅ Validatie Geslaagd
De `target_position_size` (absoluut, positief) werkt voor zowel Long als Short, mits:
1.  De Translator toegang heeft tot de `TradePlan.direction`.
2.  De magnitude wordt gecombineerd met de direction om het teken te bepalen.

### 📝 Wijzigingen
1.  **SizeDirective:** `position_size` → **`target_position_size`**
2.  **SizePlan:** `position_size` → **`target_position_size`** (consistentie)
3.  **Documentatie:** Expliciet maken dat dit de *magnitude* is, teken komt van direction.
4.  **Test Coverage:**
    *   Long: Entry, Scale In, Scale Out, Close.
    *   Short: Entry, Scale In, Cover, Close.
    *   Edge: Flip (long → short in 1 directive? Waarschijnlijk NIET toestaan).
