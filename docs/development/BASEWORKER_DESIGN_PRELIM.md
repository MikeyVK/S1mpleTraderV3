# BaseWorker Design - PRELIMINARY (Work in Progress)

**Status:** 🚧 PRELIMINARY - Design-in-Progress  
**Created:** 2025-10-29  
**Context:** Phase 1.3 preparation - Platform not yet complete, iterative design approach

---

## Design Philosophy

BaseWorker serves as the **platform-worker bridge** - providing standard boilerplate that:
1. ✅ Workers remain bus-agnostic (no EventBus coupling)
2. ✅ CausalityChain propagation is automatic (plugin developers unaware)
3. ✅ IWorkerLifecycle implementation is standardized
4. ✅ Input/Output DTO types are enforced per worker category

**Key Insight:** Since platform components (EventAdapter, WorkerFactory, etc.) are still being designed, we take an **incremental approach** - starting with the parts we know are stable (causality, lifecycle, I/O contracts).

---

## Critical Design Question: Causality Chain Boilerplate

### Current Understanding

Every worker output DTO contains a `causality: CausalityChain` field that must be:
1. **Extracted** from input DTO
2. **Extended** with worker's output ID via `model_copy(update={...})`
3. **Propagated** to output DTO

**Example from docs:**
```python
# OpportunityWorker produces OpportunitySignal
signal = OpportunitySignal(
    causality=CausalityChain(tick_id="TCK_20251026_100000_a1b2c3d4"),
    opportunity_id="OPP_20251026_100001_def5e6f7"
)

# StrategyPlanner extends chain
directive_causality = signal.causality.model_copy(update={
    "opportunity_signal_ids": ["OPP_20251026_100001_def5e6f7"],
    "strategy_directive_id": "STR_20251026_100002_abc1d2e3"
})
```

### Design Options

#### Option 1: BaseWorker Auto-Propagation (PREFERRED - archived design)

**Pros:**
- ✅ Plugin developers remain causality-unaware
- ✅ No boilerplate in concrete workers
- ✅ Consistent chain propagation guaranteed
- ✅ SRP: BaseWorker handles cross-cutting concern

**Implementation:**
```python
class BaseWorker(ABC):
    """Abstract base with automatic causality propagation."""
    
    @abstractmethod
    def process(self, input_dto: WorkerInput) -> WorkerOutput:
        """Worker-specific logic (NO causality management)."""
        ...
    
    def _process_with_causality(self, input_dto: WorkerInput) -> WorkerOutput:
        """Framework method - handles causality automatically."""
        # 1. Extract causality from input
        causality = input_dto.causality
        
        # 2. Call worker-specific logic
        output_dto = self.process(input_dto)
        
        # 3. Extend causality with output ID
        extended_causality = self._extend_causality(causality, output_dto)
        
        # 4. Propagate to output
        output_dto.causality = extended_causality
        
        return output_dto
    
    @abstractmethod
    def _extend_causality(
        self, 
        causality: CausalityChain, 
        output_dto: WorkerOutput
    ) -> CausalityChain:
        """Category-specific causality extension (e.g., opportunity_signal_ids)."""
        ...
```

**Concrete Example:**
```python
class BaseOpportunityWorker(BaseWorker):
    """Opportunity detection workers."""
    
    def _extend_causality(
        self, 
        causality: CausalityChain, 
        output_dto: OpportunitySignal
    ) -> CausalityChain:
        """Add opportunity_signal_id to chain."""
        # Note: opportunity_signal_ids is a LIST (confluence support)
        existing_ids = causality.opportunity_signal_ids or []
        return causality.model_copy(update={
            "opportunity_signal_ids": existing_ids + [output_dto.opportunity_id]
        })
```

**Plugin Developer Code (causality-free):**
```python
class FVGOpportunityWorker(BaseOpportunityWorker):
    def process(self, assessment: AggregatedContextAssessment) -> OpportunitySignal:
        # NO causality management - BaseWorker handles it!
        return OpportunitySignal(
            opportunity_id=generate_opportunity_id(),
            timestamp=datetime.now(UTC),
            asset="BTC/USDT",
            direction="long",
            signal_type="FVG_ENTRY",
            confidence=0.85
            # causality NOT set here - framework adds it!
        )
```

#### Option 2: IWorker Protocol Extension

**Alternative:** Add causality methods to IWorker protocol itself

```python
@runtime_checkable
class IWorker(Protocol):
    @property
    def name(self) -> str: ...
    
    def get_causality_field_name(self) -> str:
        """Return causality field name for this worker type."""
        ...
```

**Analysis:**
- ❌ Too invasive - couples protocol to causality concept
- ❌ Workers still need to implement boilerplate
- ❌ Violates protocol minimalism (IWorker should stay lean)

**Verdict:** NOT RECOMMENDED

#### Option 3: Explicit Manual Extension (NO ABSTRACTION)

**Workers handle causality manually:**
```python
class MyOpportunityWorker:
    def process(self, assessment: AggregatedContextAssessment) -> OpportunitySignal:
        # Manual causality extension
        signal_id = generate_opportunity_id()
        extended_causality = assessment.causality.model_copy(update={
            "opportunity_signal_ids": [signal_id]
        })
        
        return OpportunitySignal(
            causality=extended_causality,
            opportunity_id=signal_id,
            # ...
        )
```

**Analysis:**
- ❌ Boilerplate in every concrete worker
- ❌ Error-prone (easy to forget)
- ❌ Violates DRY principle
- ❌ Plugin developers must understand causality internals

**Verdict:** NOT RECOMMENDED

---

## Recommended Approach: Option 1 with Clarifications

### Causality Field Mapping Per Worker Category

Each worker category extends the causality chain with its specific field:

| Worker Category | Input DTO | Output DTO | Causality Field Extended |
|----------------|-----------|------------|-------------------------|
| **ContextWorker** | TradingContext | ContextFactor | `context_factor_ids` (list) |
| **OpportunityWorker** | AggregatedContextAssessment | OpportunitySignal | `opportunity_signal_ids` (list) |
| **ThreatWorker** | AggregatedContextAssessment | ThreatSignal | `threat_ids` (list) |
| **StrategyPlannerWorker** | Assessment + Signals | StrategyDirective | `strategy_directive_id` (single) |
| **ExecutionTranslatorWorker** | StrategyDirective | ExecutionDirective | `execution_directive_id` (single) |

**Note:** Lists support confluence (multiple signals), single IDs for unique planning decisions.

### Implementation Strategy

```python
# backend/core/workers/base_worker.py (NEW MODULE)

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from backend.dtos.causality import CausalityChain
from backend.core.interfaces.worker import IWorkerLifecycle


WorkerInput = TypeVar('WorkerInput')
WorkerOutput = TypeVar('WorkerOutput')


class BaseWorker(Generic[WorkerInput, WorkerOutput], IWorkerLifecycle, ABC):
    """
    Abstract base worker with automatic causality propagation.
    
    Responsibilities:
    - IWorkerLifecycle implementation (initialize/shutdown)
    - Automatic causality chain extension
    - Input/Output DTO type enforcement
    - Error handling patterns
    
    Plugin developers extend category-specific ABCs:
    - BaseOpportunityWorker
    - BaseThreatWorker
    - BaseStrategyPlannerWorker
    - etc.
    """
    
    def __init__(self, spec: 'WorkerBuildSpec'):
        """Construct worker with BuildSpec (NOT WorkerConfig YAML)."""
        self._spec = spec
        self._cache: IStrategyCache | None = None
        self._persistence: IPersistence | None = None
        self._strategy_ledger: IStrategyLedger | None = None
        # Additional capabilities...
    
    # === IWorkerLifecycle Implementation ===
    
    def initialize(
        self,
        strategy_cache: IStrategyCache,
        **capabilities
    ) -> None:
        """Initialize worker with runtime dependencies."""
        if strategy_cache is None:
            raise WorkerInitializationError(
                f"{self.name}: strategy_cache cannot be None"
            )
        
        self._cache = strategy_cache
        
        # Extract capabilities from manifest
        if self._spec.requires_persistence:
            self._persistence = capabilities.get('persistence')
            if self._persistence is None:
                raise WorkerInitializationError(
                    f"{self.name}: requires persistence capability"
                )
        
        # Additional capability validation...
    
    def shutdown(self) -> None:
        """Graceful shutdown - release all references."""
        self._cache = None
        self._persistence = None
        self._strategy_ledger = None
        # Never raises exceptions!
    
    @property
    def name(self) -> str:
        """Worker name from BuildSpec."""
        return self._spec.name
    
    # === Causality Management (Template Method Pattern) ===
    
    def execute(self, input_dto: WorkerInput) -> WorkerOutput:
        """
        Execute worker with automatic causality propagation.
        
        Framework method - DO NOT OVERRIDE.
        Plugin developers implement process() instead.
        """
        # 1. Extract causality from input
        causality = self._extract_causality(input_dto)
        
        # 2. Call worker-specific logic
        output_dto = self.process(input_dto)
        
        # 3. Extend causality with output ID
        extended_causality = self._extend_causality(causality, output_dto)
        
        # 4. Propagate to output
        output_dto.causality = extended_causality
        
        return output_dto
    
    @abstractmethod
    def process(self, input_dto: WorkerInput) -> WorkerOutput:
        """
        Worker-specific business logic.
        
        Plugin developers implement this.
        NO causality management - framework handles it!
        """
        ...
    
    def _extract_causality(self, input_dto: WorkerInput) -> CausalityChain:
        """Extract causality from input DTO."""
        if not hasattr(input_dto, 'causality'):
            raise ValueError(
                f"{self.name}: Input DTO {type(input_dto).__name__} "
                f"missing causality field"
            )
        return input_dto.causality
    
    @abstractmethod
    def _extend_causality(
        self,
        causality: CausalityChain,
        output_dto: WorkerOutput
    ) -> CausalityChain:
        """
        Extend causality chain with worker output ID.
        
        Category-specific - each BaseXWorker implements this.
        """
        ...
```

---

## Open Questions (Deferred to Platform Design)

### 1. WorkerBuildSpec Structure

**Question:** What does `WorkerBuildSpec` contain?

**Context:** Workers are constructed with BuildSpec (config-decoupled), not YAML directly.

**Deferred Because:** WorkerFactory design is pending (Phase 2+)

**Placeholder:**
```python
@dataclass
class WorkerBuildSpec:
    name: str
    worker_class: Type[BaseWorker]
    params: dict[str, Any]  # Plugin-specific config
    requires_persistence: bool
    requires_strategy_ledger: bool
    requires_aggregated_ledger: bool
```

### 2. ContextFactor Causality Field

**Question:** CausalityChain has `context_assessment_id` but no `context_factor_ids` (list)

**Current State:**
```python
class CausalityChain(BaseModel):
    # ...
    context_assessment_id: str | None  # AggregatedContextAssessment
    # MISSING: context_factor_ids: list[str] ???
```

**Issue:** ContextWorkers produce ContextFactor DTOs, but causality chain doesn't track individual factors.

**Potential Solutions:**
1. Add `context_factor_ids: list[str]` to CausalityChain
2. ContextWorkers DON'T extend chain (AggregatedContextAssessment does)
3. ContextFactor has NO causality field (sub-component pattern like Plans)

**Decision Required:** Need to review ContextFactor DTO design and worker flow.

### 3. DispositionEnvelope Integration

**Question:** When/how do workers return DispositionEnvelope vs raw DTOs?

**Context:** DispositionEnvelope wraps worker output for EventAdapter routing.

**Deferred Because:** EventAdapter design is pending (Phase 3)

**Current Understanding:**
```python
# Option A: BaseWorker wraps output automatically?
def execute(self, input_dto) -> DispositionEnvelope:
    output_dto = self.process(input_dto)
    return DispositionEnvelope(
        disposition="PUBLISH",
        event_payload=output_dto
    )

# Option B: Workers return DTOs, EventAdapter wraps?
# Option C: Workers return DispositionEnvelope directly?
```

**Needs Clarification:** Wait for EventAdapter design.

### 4. Error Handling Strategy

**Question:** How do workers signal processing errors?

**Options:**
1. Raise exceptions (try/catch in platform)
2. Return DispositionEnvelope(disposition="STOP", error_info=...)
3. Log to journal + return sentinel value

**Deferred Because:** Error handling architecture not yet defined.

---

## Next Steps

### Immediate (Phase 1.3)

1. **Validate ContextFactor Causality** (CRITICAL)
   - Review ContextFactor DTO structure
   - Determine if causality field needed
   - Update CausalityChain if necessary

2. **Prototype BaseOpportunityWorker** (LOW RISK)
   - Small, focused ABC
   - Clear I/O contract (AggregatedContextAssessment → OpportunitySignal)
   - Test automatic causality propagation

3. **Document Deferred Decisions** (TRACK DEBT)
   - Keep list of platform-dependent decisions
   - Update as platform components are designed

### Later (Phase 2+)

4. **WorkerFactory Integration**
   - Finalize BuildSpec structure
   - Implement worker construction pattern
   - Test with concrete workers

5. **EventAdapter Integration**
   - Clarify DispositionEnvelope wrapping
   - Define event routing patterns
   - Implement worker↔bus decoupling

6. **Complete BaseWorker Categories**
   - BaseThreatWorker
   - BaseStrategyPlannerWorker
   - BaseExecutionTranslatorWorker
   - BaseContextWorker (pending causality decision)

---

## Design Rationale: Why Preliminary?

This design document is intentionally **incomplete** because:

1. **Platform Evolution:** Core platform components (EventAdapter, WorkerFactory) are still being designed. Finalizing worker architecture now would create brittle dependencies.

2. **Iterative Discovery:** As we implement platform services, we'll discover constraints and patterns that inform BaseWorker design.

3. **Avoid Over-Engineering:** Better to have working, focused ABCs that solve known problems (causality, lifecycle) than comprehensive architecture that assumes future requirements.

4. **Fast Feedback:** Prototype → Test → Learn → Iterate is faster than Big Design Up Front.

**Principle:** Design what we know is stable (causality propagation, lifecycle), defer what depends on platform architecture (event routing, error handling).

---

## References

- [IWorkerLifecycle Design](IWORKERLIFECYCLE_DESIGN.md) - Two-phase initialization pattern
- [CausalityChain DTO](../../backend/dtos/causality.py) - Causality tracking structure
- [Archived Causality Design](#Archief/design_causality_chain.md) - Original model_copy pattern
- [Platform Components](../architecture/PLATFORM_COMPONENTS.md) - EventBus, StrategyCache docs

---

**Status Summary:**
- ✅ Causality propagation pattern DEFINED (Option 1 - BaseWorker auto-propagation)
- ⚠️ ContextFactor causality NEEDS VALIDATION
- 🚧 WorkerBuildSpec DEFERRED (pending WorkerFactory)
- 🚧 DispositionEnvelope wrapping DEFERRED (pending EventAdapter)
- 🚧 Error handling DEFERRED (pending platform design)

**Recommendation:** Proceed with BaseOpportunityWorker prototype to validate causality pattern before expanding to other categories.
