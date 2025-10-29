# SWOT Decision Framework

**Status:** Architecture Approved, Implementation Pending  
**Version:** 1.0  
**Last Updated:** 2025-10-24

---

## Overview

Het SWOT Decision Framework is de besluitvormingsarchitectuur van SimpleTraderV3, waarbij marktcontext, kansen en risico's worden gecombineerd tot handelsbeslissingen via een mathematische confrontatiematrix.

**Kernprincipe:** Elke handelsbeslissing is een *confrontatie* tussen vier quadranten:
- **Strengths** (Sterktes): Gunstige marktcondities
- **Weaknesses** (Zwaktes): Ongunstige marktcondities  
- **Opportunities** (Kansen): Detecteerde trading opportunities
- **Threats** (Bedreigingen): Detecteerde risico's en gevaren

---

## Architecture Overview

### SWOT Quadrant Mapping

| SWOT Quadrant | Worker Category | Output DTO | Score Field | Range |
|---------------|----------------|------------|-------------|-------|
| **Strengths** | ContextWorker | ContextAssessment | `strength` | 0.0-1.0 |
| **Weaknesses** | ContextWorker | ContextAssessment | `weakness` | 0.0-1.0 |
| **Opportunities** | OpportunityWorker | OpportunitySignal | `confidence` | 0.0-1.0 |
| **Threats** | ThreatWorker | ThreatSignal | `severity` | 0.0-1.0 |

**Symmetrie:** Alle quadranten produceren 0.0-1.0 scores voor mathematische combinatie.

### Pipeline Flow

```
1. RAW_TICK arrives
   ↓
2. ContextWorkers (SEQUENTIAL)
   → EMADetector      → EMAOutputDTO
   → RSIDetector      → RSIOutputDTO  
   → RegimeClassifier → MarketRegimeDTO
   ↓
3. ContextAggregator (PLATFORM)
   → Aggregeert context DTOs
   → ContextAssessment(strength=0.75, weakness=0.30)
   ↓
4. OpportunityWorkers (PARALLEL)
   → FVGDetector → OpportunitySignal(confidence=0.85)
   ↓
5. ThreatWorkers (PARALLEL)
   → DrawdownMonitor → ThreatSignal(severity=0.60)
   ↓
6. SWOT Confrontation Worker (PLANNING)
   → Input: ContextAssessment + OpportunitySignals + ThreatSignals
   → Logic: Confrontation matrix calculation
   → Output: TradePlan(execute=true/false, reasoning=...)
```

---

## Component 1: ContextAggregator

### Responsibility

Platform component die atomaire context-metingen aggregeert naar een holistische strength/weakness assessment.

### Design Principles

**Platform Verantwoordelijkheid (NIET Plugin):**
- Cross-cutting concern: combineert data van meerdere plugins
- Configureerbaar beleid per strategie
- Framework intelligence: weet welke DTOs relevant zijn

### Architecture

```python
# backend/core/context_aggregator.py

class ContextAggregator:
    """
    Platform component voor context aggregatie.
    
    Aggregeert atomaire context DTOs (EMA, RSI, regime) naar een
    holistische ContextAssessment met strength/weakness scores.
    """
    
    def __init__(self, policy: AggregationPolicy):
        """
        Args:
            policy: Strategy-specific aggregation beleid
        """
        self._policy = policy
    
    def aggregate(self, tick_cache: TickCache) -> ContextAssessment:
        """
        Synthese van alle context DTOs naar S/W assessment.
        
        Returns:
            ContextAssessment met strength/weakness scores
        """
        # Extract alle context DTOs
        context_dtos = self._extract_context_dtos(tick_cache)
        
        # Policy bepaalt HOE te aggregeren
        return self._policy.synthesize(context_dtos)
```

### AggregationPolicy Interface

```python
class AggregationPolicy(ABC):
    """Strategy-specific aggregation logica."""
    
    @abstractmethod
    def synthesize(
        self, 
        context_dtos: Dict[Type[BaseModel], BaseModel]
    ) -> ContextAssessment:
        """Implementeer aggregation logica."""
        pass


class ConservativePolicy(AggregationPolicy):
    """Conservatieve aggregatie: strengths moeten duidelijk zijn."""
    
    def synthesize(self, context_dtos) -> ContextAssessment:
        # Trending regime + low volatility = strength
        # Ranging regime OR high volatility = weakness
        ...


class AggressivePolicy(AggregationPolicy):
    """Agressieve aggregatie: kleine strengths zijn voldoende."""
    
    def synthesize(self, context_dtos) -> ContextAssessment:
        # Elke trending indicator = strength
        # Alleen extreme volatility = weakness
        ...
```

### Timing & State

**Wanneer draait het:**
- Na **laatste** ContextWorker in sequential chain
- Vóór OpportunityWorkers (parallel)

**State:**
- GEEN persistentie nodig
- TickCache is ephemeral (per tick)
- Alle ContextWorkers zijn sync uitgevoerd

**Latency:**
- Lichtgewicht operatie (< 1ms)
- Geen I/O, pure berekening
- Geen blocking

---

## Component 2: ContextAssessment DTO

### Specification

```python
# backend/dtos/context/context_assessment.py

class StrengthFactor(BaseModel):
    """Individuele strength indicator."""
    
    factor_type: str = Field(
        ...,
        description="Type strength (TRENDING_REGIME, HIGH_LIQUIDITY, etc.)"
    )
    
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Strength score"
    )
    
    rationale: Optional[str] = Field(
        None,
        max_length=200,
        description="Why this is a strength"
    )


class WeaknessFactor(BaseModel):
    """Individuele weakness indicator."""
    
    factor_type: str = Field(
        ...,
        description="Type weakness (RANGING_REGIME, LOW_LIQUIDITY, etc.)"
    )
    
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weakness score"
    )
    
    rationale: Optional[str] = Field(
        None,
        max_length=200,
        description="Why this is a weakness"
    )


class ContextAssessment(BaseModel):
    """
    Aggregated context assessment met SWOT S/W quadranten.
    
    Output van ContextAggregator platform component.
    Combineert atomaire context metingen naar holistische duiding.
    
    SWOT Framework:
        strength: Gewogen gemiddelde van gunstige condities
        weakness: Gewogen gemiddelde van ongunstige condities
    
    Fields:
        initiator_id: Flow initiator (TCK_/SCH_/NWS_/MAN_)
        timestamp: Assessment timestamp (UTC)
        strength: Overall strength score [0.0, 1.0]
        weakness: Overall weakness score [0.0, 1.0]
        strength_factors: Individuele strength contributors
        weakness_factors: Individuele weakness contributors
    """
    
    initiator_id: str
    timestamp: datetime
    
    # Aggregated scores
    strength: float = Field(ge=0.0, le=1.0)
    weakness: float = Field(ge=0.0, le=1.0)
    
    # Detailed breakdown
    strength_factors: List[StrengthFactor] = Field(default_factory=list)
    weakness_factors: List[WeaknessFactor] = Field(default_factory=list)
    
    model_config = {
        "frozen": True,
        "extra": "forbid"
    }
```

### Example

```python
assessment = ContextAssessment(
    initiator_id="TCK_550e8400-e29b-41d4-a716-446655440000",
    timestamp=datetime.now(timezone.utc),
    strength=0.75,
    weakness=0.30,
    strength_factors=[
        StrengthFactor(
            factor_type="TRENDING_REGIME",
            score=0.85,
            rationale="Strong uptrend with consistent higher highs"
        ),
        StrengthFactor(
            factor_type="HIGH_LIQUIDITY",
            score=0.65,
            rationale="Deep orderbook supports position sizing"
        )
    ],
    weakness_factors=[
        WeaknessFactor(
            factor_type="HIGH_VOLATILITY",
            score=0.45,
            rationale="ATR elevated, wider stops needed"
        )
    ]
)
```

---

## Component 3: SWOT Confrontation Worker

### Responsibility

PlanningWorker die SWOT quadranten combineert via confrontatie matrix om handelsbeslissing te nemen.

### Classical SWOT Strategies

| Strategy | Combinatie | Logica |
|----------|-----------|--------|
| **Maxi-Maxi** | Strengths × Opportunities | Gebruik sterktes om kansen te benutten |
| **Mini-Maxi** | Weaknesses × Opportunities | Minimaliseer zwaktes om kansen te benutten |
| **Maxi-Mini** | Strengths × Threats | Gebruik sterktes om bedreigingen te counteren |
| **Mini-Mini** | Weaknesses × Threats | Minimaliseer zwaktes EN bedreigingen |

### Implementation Example

```python
# plugins/planning/swot_confrontation/worker.py

class SWOTConfrontationWorker(StandardWorker):
    """
    PlanningWorker: SWOT confrontation matrix.
    
    Input:
        - ContextAssessment (strength/weakness)
        - OpportunitySignal (confidence)
        - ThreatSignal (severity)
    
    Output:
        - TradePlan (execute decision + reasoning)
    """
    
    def process(self) -> DispositionEnvelope:
        # Haal SWOT inputs op
        context = self.context_provider.get_dto(ContextAssessment)
        opportunities = self.context_provider.get_dtos(OpportunitySignal)
        threats = self.context_provider.get_dtos(ThreatSignal)
        
        # Bereken confrontatie scores
        confrontation = self._calculate_matrix(
            context, opportunities, threats
        )
        
        # Neem beslissing
        trade_plan = self._decide(confrontation)
        
        # Produceer plan
        self.context_provider.set_result_dto(self, trade_plan)
        return DispositionEnvelope(disposition="CONTINUE")
    
    def _calculate_matrix(
        self,
        context: ContextAssessment,
        opportunities: List[OpportunitySignal],
        threats: List[ThreatSignal]
    ) -> ConfrontationMatrix:
        """
        Mathematische confrontatie berekening.
        
        Returns:
            ConfrontationMatrix met scores per strategie
        """
        # Max opportunity confidence
        max_opp = max(
            [o.confidence for o in opportunities if o.confidence],
            default=0.0
        )
        
        # Max threat severity
        max_threat = max(
            [t.severity for t in threats],
            default=0.0
        )
        
        return ConfrontationMatrix(
            maxi_maxi=context.strength * max_opp,
            mini_maxi=(1.0 - context.weakness) * max_opp,
            maxi_mini=context.strength * (1.0 - max_threat),
            mini_mini=(1.0 - context.weakness) * (1.0 - max_threat)
        )
    
    def _decide(self, matrix: ConfrontationMatrix) -> TradePlan:
        """
        Execution beslissing op basis van matrix.
        
        Returns:
            TradePlan met execute=True/False + reasoning
        """
        # Threshold configuratie
        threshold = self.config.get('execution_threshold', 0.6)
        
        # Best strategy score
        best_score = max(
            matrix.maxi_maxi,
            matrix.mini_maxi,
            matrix.maxi_mini,
            matrix.mini_mini
        )
        
        if best_score >= threshold:
            return TradePlan(
                execute=True,
                confidence=best_score,
                reasoning=f"SWOT score {best_score:.2f} > threshold {threshold}"
            )
        else:
            return TradePlan(
                execute=False,
                confidence=best_score,
                reasoning=f"SWOT score {best_score:.2f} < threshold {threshold}"
            )
```

---

## Advanced: Machine Learning Integration

### Future Enhancement: ML-Based Confrontation

Het confrontation framework is geschikt voor ML enhancement:

**Traditional (Current):**
```python
score = strength * confidence - weakness * severity
```

**ML-Enhanced (Future):**
```python
# Train model op historische outcomes
features = [
    context.strength,
    context.weakness,
    opportunity.confidence,
    threat.severity,
    # ... meer features
]

# Model voorspelt success probability
ml_score = trained_model.predict(features)
```

**Voordelen:**
- Leer optimale weight combinaties
- Non-lineaire relaties tussen quadranten
- Adaptieve thresholds per market regime
- Continuous improvement via backtesting

**Implementatie pad:**
1. Log alle SWOT decisions + outcomes
2. Train regression model (success rate predictor)
3. Deploy als `MLConfrontationWorker` naast rule-based
4. A/B test beide benaderingen
5. Graduele migratie naar hybrid systeem

---

## Implementation Checklist

### Phase 1: Foundation DTOs
- [ ] Implement `ContextAssessment` DTO
- [ ] Implement `StrengthFactor` DTO
- [ ] Implement `WeaknessFactor` DTO
- [ ] Unit tests (coverage > 95%)

### Phase 2: Platform Component
- [ ] Implement `ContextAggregator` class
- [ ] Design `AggregationPolicy` interface
- [ ] Implement `ConservativePolicy`
- [ ] Implement `AggressivePolicy`
- [ ] Integration tests met TickCache

### Phase 3: Planning Worker
- [ ] Implement `SWOTConfrontationWorker`
- [ ] Implement `ConfrontationMatrix` DTO
- [ ] Implement decision logic
- [ ] Configuration schema voor thresholds
- [ ] Unit + integration tests

### Phase 4: Integration
- [ ] Wire ContextAggregator in tick lifecycle
- [ ] Update EventAdapter voor aggregator call
- [ ] Update strategy blueprint schema
- [ ] End-to-end integration tests

### Phase 5: Documentation
- [ ] Update worker taxonomie
- [ ] Add examples to strategy blueprints
- [ ] API documentation
- [ ] Architecture diagrams

---

## References

- [OpportunitySignal DTO](../../backend/dtos/strategy/opportunity_signal.py) - Opportunities quadrant
- [ThreatSignal DTO](../../backend/dtos/strategy/threat_signal.py) - Threats quadrant
- [DispositionEnvelope](../../backend/dtos/shared/disposition_envelope.py) - Worker output contract
- [TODO.md](../TODO.md#-swot-decision-framework) - Implementation tracking

---

**Maintained by:** Development Team  
**Review Frequency:** Per milestone  
**Next Review:** After ContextAssessment DTO implementation
