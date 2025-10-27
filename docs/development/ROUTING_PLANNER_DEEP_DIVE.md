# Routing Planner Deep Dive - Waarom & Hoe?

**Datum:** 2025-10-27  
**Doel:** Helder uitleggen wat routing planners doen en waarom ze cruciaal zijn

---

## Het Probleem: Entry/Exit/Size zijn Niet Genoeg

Je hebt een perfect plan:
- **EntryPlan:** "Koop BTCUSDT met LIMIT order op $50,000"
- **SizePlan:** "Handel 1.5 BTC ($75,000 waarde)"
- **ExitPlan:** "Stop loss $49,500, take profit $51,500"

**Vraag:** HOE voer je dit uit?

### Scenario 1: Klein Order ($5,000)
```
EntryPlan: LIMIT @ $50,000
SizePlan: 0.1 BTC ($5,000)

→ Simpel: 1 limit order, done!
```

### Scenario 2: Groot Order ($500,000)
```
EntryPlan: LIMIT @ $50,000
SizePlan: 10 BTC ($500,000)

→ Probleem! Order book heeft maar liquiditeit voor 3 BTC @ $50,000
→ Als je 1 grote order plaatst: slippage!
→ Je entry wordt $50,200 gemiddeld (niet $50,000)
```

**Dit is waar Routing Planners om de hoek komen kijken.**

---

## Wat Doet een Routing Planner?

Een **RoutingPlanner** bepaalt **HOE** en **WANNEER** je een trade execution-technisch uitvoert.

### De 4 Kern Beslissingen:

#### 1. **Timing Strategy** (WANNEER?)

**IMMEDIATE:**
```
Gebruik: High confidence (0.9) breakout
Trade-off: Snelheid > Prijs
Uitvoering: Market order, accepteer slippage
```

**TWAP (Time-Weighted Average Price):**
```
Gebruik: Grote orders, lage urgency (confidence 0.5)
Trade-off: Prijs > Snelheid  
Uitvoering: Splits order in 10 chunks over 10 minuten
Voorbeeld:
  10 BTC total → 10x 1 BTC elke 60 seconden
  Gemiddelde prijs = $50,100 (vs $50,300 bij 1 order)
```

**LAYERED:**
```
Gebruik: Range-bound market, patience
Trade-off: Beste prijs, accepteer partial fills
Uitvoering: Plaats limit orders op meerdere niveaus
Voorbeeld:
  10 BTC total:
    - 3 BTC @ $49,950
    - 4 BTC @ $50,000
    - 3 BTC @ $50,050
```

**PATIENT:**
```
Gebruik: Lage urgency, wil beste prijs
Trade-off: Tijd > Alles
Uitvoering: Limit order, wacht op fill (kan uren duren)
```

#### 2. **Execution Urgency** (Hoe agressief?)

```python
execution_urgency = 0.9  # Zeer agressief
→ Kies: IMMEDIATE, accepteer 0.5% slippage

execution_urgency = 0.3  # Patient
→ Kies: LAYERED, accepteer 0.1% slippage
```

Dit is een **gradient** - niet binair.

#### 3. **Slippage Tolerance** (Hoeveel prijs-afwijking acceptabel?)

```python
max_slippage_pct = 0.001  # 0.1% max
→ Bij market order: annuleer als prijs > $50,050
→ Bij TWAP: stop algoritme als gemiddelde > target + 0.1%
```

**Waarom per-trade?**
- High confidence trades: accepteer meer slippage (0.5%)
- Low confidence trades: strict (0.1%)

**Strategy Planner bepaalt dit via:**
```python
StrategyDirective(
    confidence=0.85,
    routing_directive=RoutingDirective(
        execution_urgency=0.85,  # Hoge urgency bij hoge confidence
        max_total_slippage_pct=Decimal("0.005")  # 0.5% acceptable
    )
)
```

#### 4. **Iceberg Orders** (Verberg je intentie?)

**Probleem:** Grote orders tonen je hand aan de markt.

**Scenario:**
```
Visible: 10 BTC sell order @ $50,000
→ Market ziet dit → drives price down
→ Je exit wordt $49,800 (slippage)
```

**Iceberg Oplossing:**
```
Visible: 0.5 BTC sell order @ $50,000
Hidden: 9.5 BTC (replenish automatically)
→ Market ziet alleen kleine order
→ Minder impact, betere fill
```

**Routing Planner Beslissing:**
```python
if position_size > Decimal("5.0"):  # Grote order
    iceberg_preference = Decimal("0.8")  # Use iceberg
else:
    iceberg_preference = None  # Normale order
```

---

## Concrete Voorbeelden - Strategy Planner → Routing Planner

### Voorbeeld 1: High Confidence Breakout

**Strategy Planner Output:**
```python
StrategyDirective(
    confidence=Decimal("0.92"),  # Zeer hoge confidence
    entry_directive=EntryDirective(
        timing_preference=Decimal("0.95"),  # Zeer urgent!
        symbol="BTCUSDT",
        direction="BUY"
    ),
    routing_directive=RoutingDirective(
        execution_urgency=Decimal("0.95"),
        max_total_slippage_pct=Decimal("0.01")  # 1% acceptable
    )
)
```

**Routing Planner (AggressiveMarketRouter) Beslissing:**
```yaml
# Config: AggressiveMarketRouter triggers
triggers:
  confidence: [0.8, 1.0]
  execution_urgency: [0.8, 1.0]
```

**Output:**
```python
RoutingPlan(
    timing="IMMEDIATE",
    time_in_force="IOC",  # Immediate or Cancel
    max_slippage_pct=Decimal("0.01"),
    execution_urgency=Decimal("0.95"),
    iceberg_preference=None  # Don't care about hiding
)
```

**Executie:** Market order, nu direct, accepteer slippage

---

### Voorbeeld 2: Low Confidence, Large Position

**Strategy Planner Output:**
```python
StrategyDirective(
    confidence=Decimal("0.45"),  # Medium-low confidence
    size_directive=SizeDirective(
        aggressiveness=Decimal("0.3"),
        max_risk_amount=Decimal("10000")
    ),
    routing_directive=RoutingDirective(
        execution_urgency=Decimal("0.3"),  # Patient
        max_total_slippage_pct=Decimal("0.002")  # 0.2% strict
    )
)
```

**Routing Planner (TWAPRouter) Beslissing:**
```yaml
# Config: TWAPRouter triggers  
triggers:
  confidence: [0.3, 0.7]
  execution_urgency: [0.0, 0.5]
  position_value: [50000, 500000]  # Grote orders
```

**Output:**
```python
RoutingPlan(
    timing="TWAP",
    time_in_force="GTC",  # Good Till Canceled
    max_slippage_pct=Decimal("0.002"),
    execution_urgency=Decimal("0.3"),
    iceberg_preference=Decimal("0.6")  # Use iceberg
)
```

**Executie:**
- Platform TWAP config: 10 chunks, 60 sec interval
- 10 BTC → 10x 1 BTC limit orders
- Iceberg: show only 0.2 BTC per chunk
- Stop if average > $50,100 (0.2% slippage)

---

### Voorbeeld 3: DCA Strategy (Scheduled)

**Strategy Planner Output:**
```python
StrategyDirective(
    scope="NEW_TRADE",  # Scheduled DCA
    confidence=Decimal("0.60"),  # Neutral (DCA doesn't need high conf)
    routing_directive=RoutingDirective(
        execution_urgency=Decimal("0.1"),  # Very patient
        max_total_slippage_pct=Decimal("0.001")  # 0.1% strict
    )
)
```

**Routing Planner (PatientLimitRouter) Beslissing:**
```yaml
# Config: PatientLimitRouter
triggers:
  confidence: [0.0, 0.8]  # Any confidence
  execution_urgency: [0.0, 0.3]  # Low urgency
```

**Output:**
```python
RoutingPlan(
    timing="PATIENT",
    time_in_force="GTC",  # Wait hours if needed
    max_slippage_pct=Decimal("0.001"),
    execution_urgency=Decimal("0.1"),
    iceberg_preference=None
)
```

**Executie:**
- Limit order @ $50,000 (exact)
- Wacht tot filled (kan 2 uur duren)
- Annuleer alleen als niet filled binnen 24u

---

## Waarom Routing Gescheiden van Entry?

### Vergelijking: Wat als Entry EN Routing samen waren?

**Slecht Design:**
```python
class EntryPlan:
    order_type: str  # MARKET
    timing: str      # IMMEDIATE
    twap_chunks: int # Huh? MARKET heeft geen TWAP...
    iceberg: bool    # Confused responsibility
```

**Problemen:**
1. **Conceptuele Vervuiling:** Entry = "WAAR?", Routing = "HOE?"
2. **Inflexibel:** Kan niet routing wijzigen zonder entry wijzigen
3. **Moeilijk Testbaar:** Mixed concerns

**Goed Design (V3):**
```python
# Entry = Pure trade parameters
EntryPlan(
    symbol="BTCUSDT",
    direction="BUY",
    order_type="LIMIT",  # WHAT type
    limit_price=Decimal("50000")  # WHERE
)

# Routing = Pure execution tactics  
RoutingPlan(
    timing="TWAP",  # HOW split?
    execution_urgency=0.3,  # HOW urgent?
    max_slippage_pct=0.002,  # HOW strict?
    iceberg_preference=0.6  # HOW hide?
)
```

**Voordelen:**
1. ✅ **SRP:** Elke planner één verantwoordelijkheid
2. ✅ **Flexibel:** Zelfde entry, verschillende routing per situatie
3. ✅ **Testbaar:** Test entry logic apart van routing logic

---

## Routing Planner Specialisaties - Concrete Use Cases

### 1. MarketOrderRouter
```yaml
specialty: "Speed above all"
triggers:
  confidence: [0.8, 1.0]
  execution_urgency: [0.8, 1.0]
output:
  timing: IMMEDIATE
  time_in_force: IOC
use_cases:
  - Breakout trades (miss het niet!)
  - Stop loss triggers (exit NU)
  - High conviction scalps
```

### 2. TWAPRouter
```yaml
specialty: "Minimize market impact"
triggers:
  position_value: [50000, 1000000]
  execution_urgency: [0.0, 0.5]
output:
  timing: TWAP
  time_in_force: GTC
  iceberg_preference: 0.7
use_cases:
  - Grote DCA inkopen
  - Institutional-size orders
  - Illiquide assets
```

### 3. IcebergRouter
```yaml
specialty: "Hide intentions"
triggers:
  position_size: [5.0, 100.0]  # BTC
  market_depth_ratio: [0.1, 0.5]  # Order / Orderbook
output:
  timing: LAYERED
  iceberg_preference: 0.9
use_cases:
  - Whale trades
  - Thin orderbook assets
  - Prevent front-running
```

### 4. SmartLimitRouter
```yaml
specialty: "Best price, patient"
triggers:
  confidence: [0.3, 0.7]
  execution_urgency: [0.0, 0.3]
output:
  timing: PATIENT
  time_in_force: GTC
use_cases:
  - DCA strategies
  - Range-bound setups
  - "Good price or nothing"
```

---

## Samenwerking: Strategy Planner ↔ Routing Planner

### Flow:

```
1. Strategy Planner (SWOT confrontation)
   ↓
   Produces: confidence=0.85 + routing_directive hints
   
2. Config matches Routing Planner
   ↓
   AggressiveMarketRouter: confidence [0.8-1.0] ✅ Match!
   
3. Routing Planner specializes
   ↓
   Output: timing=IMMEDIATE, slippage=0.01
   
4. Execution Handler implements
   ↓
   Places market order, monitors slippage
```

**Strategy Planner:** "Ik heb 85% vertrouwen, wees agressief"  
**Routing Planner:** "OK, ik doe IMMEDIATE market order met 1% slippage tolerance"  
**Execution Handler:** "Executing... filled @ $50,050 (0.1% slip) ✅"

---

## Platform Config vs. Per-Trade Config

### Platform Config (`platform.yaml`):
```yaml
execution:
  twap:
    default_duration_minutes: 10
    default_chunks: 10
    min_chunk_size_btc: 0.1
  
  iceberg:
    default_visible_ratio: 0.1  # 10% visible
    replenish_threshold: 0.05   # Refill at 5%
```

**Rationale:** Uniform algorithms - quant kiest TWAP, platform bepaalt hoe

### Per-Trade Config (RoutingPlan):
```python
RoutingPlan(
    timing="TWAP",  # Quant choice
    max_slippage_pct=0.002,  # Trade-specific
    execution_urgency=0.3  # Trade-specific
)
```

**Rationale:** Trade context bepaalt tolerances

---

## Conclusie

**Routing Planners zijn cruciaal omdat:**

1. **Entry/Exit/Size zijn "WAT"** - Routing is "HOE"
2. **Trade-specific execution** - Confidence bepaalt urgency/slippage
3. **Market impact minimalisatie** - TWAP, iceberg, layering
4. **SRP architectuur** - Elke planner één expertise

**Zonder Routing Planners:**
- ❌ EntryPlan moet weten over TWAP/iceberg (wrong responsibility)
- ❌ ExecutionHandler moet confidence interpreteren (wrong layer)
- ❌ Geen flexibiliteit (zelfde entry, verschillende routing)

**Met Routing Planners:**
- ✅ Entry = pure trade parameters
- ✅ Routing = pure execution tactics
- ✅ Confidence-driven specialization (config, niet code)
- ✅ Testbaar en modulair

**Het is de missing link tussen "Ik wil kopen" en "Hoe koop ik intelligent?"**
