# Strategy Cardinality & Safety Contracts

Dit document definieert de relatie tussen `StrategyDirective` en `TradePlan`, en formaliseert de veiligheidsregels voor modificaties.

## 1. Cardinaliteit: Uniform Rule vs. Specific Context

De vraag: *Hanteren we 1 StrategyDirective voor meerdere TradePlans (1:N), of batches van 1:1?*

### Het "Uniform Rule" Model (Aanbevolen)
We moeten onderscheid maken tussen de **Regel** (Directive) en het **Resultaat** (Plan).

*   **StrategyDirective (De Generaal):** Geeft een *beleidsinstructie*.
    *   *"Zet de stop loss op 1% afstand."*
    *   *"Verkoop 50% van de positie."*
    *   *"Sluit alles nu (Panic)."*
*   **TradePlan (De Context):** De specifieke situatie per trade.
    *   Plan A: Entry $100.
    *   Plan B: Entry $200.
*   **Planner (De Specialist):** Past de regel toe op de context.
    *   Plan A: Stop = $99.
    *   Plan B: Stop = $198.

**Conclusie:**
Omdat de *Specialist* (ExitPlanner/SizePlanner) de contextuele berekening doet, kan de **StrategyDirective** vaak **uniform** zijn voor meerdere plannen.

### Waarom 1:N (List) krachtig is:
1.  **Efficiëntie:** Een "Emergency Flatten" of "Global Trailing Stop Update" is één bericht.
2.  **Consistentie:** Je garandeert dat dezelfde policy ("1% risk") op alle geselecteerde trades wordt toegepast.
3.  **Flexibiliteit:** Als je *wel* variatie wilt (Plan A krijgt 1%, Plan B krijgt 5%), stuur je simpelweg twee aparte directives (in opeenvolgende ticks of via een batch-mechanisme).

**Besluit:**
We behouden `target_plan_ids` als een **lijst (List[str])**.
*   Standaard gebruik: Pas deze *uniforme policy* toe op al deze plannen.
*   Specifiek gebruik: Lijst met lengte 1 voor unieke behandeling.

---

## 2. Safety Contract: Absolute Position Sizing

Om fouten bij modificaties (zoals dubbele executie) te voorkomen, dwingen we **Absolute Idempotentie** af.

### De Regel
`SizeDirective.position_size` (indien aanwezig) vertegenwoordigt altijd de **Gewenste Eindstaat (Target State)**, nooit een relatieve verandering (Delta).

### Voorbeeld: Scale In
*   Huidige Positie: 1.0 BTC.
*   Wens: 0.5 BTC erbij.
*   **Fout (Relatief):** `size_directive(add=0.5)`.
    *   *Risico:* Als bericht 2x verwerkt wordt -> +1.0 BTC totaal.
*   **Goed (Absoluut):** `size_directive(target=1.5)`.
    *   *Veiligheid:* Als bericht 2x verwerkt wordt -> Translator ziet "Huidig 1.5, Target 1.5 -> Doe niets".

### Implementatie & Validatie
1.  **DTO Veld:** `SizeDirective` krijgt een veld `is_absolute: bool = True` (standaard, of impliciet aangenomen).
2.  **Translator Logica:**
    *   `delta = target_size - current_size`
    *   Als `delta > 0`: `EXECUTE_TRADE (BUY)`
    *   Als `delta < 0`: `EXECUTE_TRADE (SELL)`
    *   Als `delta == 0`: No-op.

---

## 3. Samenvatting Architectuur Wijzigingen

1.  **StrategyDirective:**
    *   `target_trade_ids` -> **`target_plan_ids`** (List[str]).
    *   Sub-directive: Uses `ExecutionDirective` (field: `execution_directive`) - per code SSOT.
2.  **SizeDirective:**
    *   Documentatie update: "Values are ABSOLUTE target states".
3.  **Validatie:**
    *   `target_plan_ids` mag niet leeg zijn bij `MODIFY/CLOSE`.
    *   `symbol` moet `BASE_QUOTE` format zijn.
