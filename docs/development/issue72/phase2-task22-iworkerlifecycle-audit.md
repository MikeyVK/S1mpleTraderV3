# Task 2.2: IWorkerLifecycle Pattern Audit - Comprehensive Report

**Status:** COMPLETE  
**Phase:** Phase 2 - Blocker Resolution  
**Date:** 2026-01-27  
**Author:** AI Agent  
**Related:** Issue #72 Template Library Management

---

## Executive Summary

**Finding:** IWorkerLifecycle protocol is well-designed but **critically underutilized**. Only **1 of 3 backend workers** implements the pattern (FlowInitiator). Worker template generates **simple `__init__`** without lifecycle methods, teaching agents the **wrong pattern**.

**Core Impact on Agentic Development:**
The MCP server's mission is to "enable human and AI to work in harmony on creative content, while software handles workflow orchestration, project structure, and quality assurance." Templates are **NOT just scaffolding tools** - they are **how agents learn architectural patterns**. When templates generate incorrect patterns, agents perpetuate technical debt.

**Recommendation:** **MANDATORY with Opt-Out**
- Default: All workers implement IWorkerLifecycle (template generates `initialize()` + `shutdown()`)
- Opt-out: Explicit `lifecycle_enabled: false` flag (discouraged, requires justification)
- Rationale: Aligns with all 4 core principles, provides structural consistency while preserving creative freedom on business logic

**Strategic Value:** This is not just about one protocol - it's about establishing template-driven development as the foundation for scalable, consistent agentic codebases.

---

## 1. Protocol Definition Analysis

### Contract Overview

**Location:** `backend/core/interfaces/worker.py`  
**Protocols:** `IWorker` (name property) + `IWorkerLifecycle` (lifecycle management)  
**Design Document:** `docs/development/#Archief/IWORKERLIFECYCLE_DESIGN.md`

### Two-Phase Initialization Pattern

```python
@runtime_checkable
class IWorkerLifecycle(Protocol):
    """
    Protocol for worker lifecycle management (two-phase initialization).
    
    Workers follow two-phase initialization pattern:
    1. Construction (__init__): Receive BuildSpec, store manifest data
    2. Runtime initialization (initialize): Inject runtime dependencies
    """
    
    def initialize(
        self,
        strategy_cache: "IStrategyCache | None" = None,
        **capabilities
    ) -> None:
        """
        Initialize worker with runtime dependencies.
        
        Args:
            strategy_cache: Platform singleton for strategy state management
                - Required for Strategy Workers (per-strategy instances)
                - Required for Platform-within-Strategy Workers (routing)
                - None for Platform Workers (no strategy context)
            **capabilities: Optional runtime capabilities
                - persistence: IPersistenceService
                - strategy_ledger: IStrategyLedger
                - aggregated_ledger: IAggregatedLedger
        """
        ...
    
    def shutdown(self) -> None:
        """
        Graceful worker shutdown and resource cleanup.
        
        Critical Requirements:
        - MUST NOT raise exceptions (catch and log internally)
        - MUST be idempotent (safe to call multiple times)
        - SHOULD complete within reasonable time (<5s typical)
        """
        ...
```

### Worker Scopes

| Scope Type | strategy_cache | Examples | Use Case |
|------------|----------------|----------|----------|
| **Platform Workers** | `None` | DataProvider | Singleton, no strategy context |
| **Strategy Workers** | Required | SignalDetector, RiskMonitor | Per-strategy instance |
| **Platform-within-Strategy** | Required | FlowInitiator | Singleton but strategy-aware |

### Lifecycle Phases

```
Phase 1: Construction
  └─ Worker(build_spec) → worker instance (not yet functional)

Phase 2: Initialization  
  └─ worker.initialize(strategy_cache, **capabilities) → functional worker

Phase 3: Active Processing
  └─ EventAdapter calls worker methods, worker uses StrategyCache

Phase 4: Shutdown
  └─ worker.shutdown() → clean resource release
```

### Rationale: Solving V2 Circular Dependencies

**V2 Problem:**
```python
# V2 Pattern (PROBLEMATIC)
class V2Worker:
    def __init__(
        self,
        config: WorkerConfig,
        event_bus: EventBus,           # ❌ Circular dependency
        persistor: DatabasePersistor,  # ❌ Requires DB connection
        logger: Logger                 # ❌ Requires full setup
    ):
        # Must construct EventBus before ANY worker
        # EventBus needs workers, workers need EventBus
```

**V3 Solution:**
```python
# V3 Pattern (CLEAN)
class V3Worker:
    def __init__(self, build_spec: BuildSpec):
        """Phase 1: Construction - config only."""
        self._manifest = build_spec.manifest
        self._cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        """Phase 2: Runtime dependency injection."""
        self._cache = strategy_cache
    
    def shutdown(self) -> None:
        """Phase 3: Deterministic cleanup."""
        self._cache = None
```

**Benefits:**
1. **No Circular Dependencies**: Workers constructed first, dependencies injected later
2. **Flexible Bootstrap**: Can construct workers in any order
3. **Standardized Lifecycle**: All workers follow same init/shutdown pattern
4. **Easy Testing**: Mock just StrategyCache, not EventBus

---

## 2. Backend Implementation Inventory

### Actual Worker Implementations

| Worker | Location | Implements IWorkerLifecycle? | Worker Scope | Notes |
|--------|----------|------------------------------|--------------|-------|
| **FlowInitiator** | `backend/core/flow_initiator.py` | ✅ **YES** | Platform-within-Strategy | **EXEMPLAR** - validates cache, stores dto_types capability |
| **EventProcessorWorker** | `backend/workers/event_processor_worker.py` | ❌ **NO** | Unknown (scaffolded test) | Simple `__init__`, no lifecycle methods |
| **DataProcessorWorker** | `backend/workers/data_processor_worker.py` | ❌ **NO** | Unknown (scaffolded test) | Simple `__init__`, no lifecycle methods |

**Implementation Rate:** **1 out of 3 (33%)**

### FlowInitiator Analysis (Exemplar Implementation)

```python
class FlowInitiator(IWorker, IWorkerLifecycle):
    """Platform-within-Strategy worker - EXEMPLAR IMPLEMENTATION."""
    
    def __init__(self, name: str) -> None:
        """Phase 1: Construction - name only."""
        self._name = name
        self._cache: IStrategyCache | None = None
        self._dto_types: dict[str, type[BaseModel]] = {}
    
    def initialize(
        self,
        strategy_cache: IStrategyCache | None = None,
        **capabilities: Any
    ) -> None:
        """Phase 2: Runtime initialization."""
        # Validate strategy_cache (Platform-within-Strategy requirement)
        if strategy_cache is None:
            raise WorkerInitializationError(
                f"{self._name}: strategy_cache required for FlowInitiator"
            )
        
        # Validate dto_types capability
        if "dto_types" not in capabilities:
            raise WorkerInitializationError(
                f"{self._name}: 'dto_types' capability required"
            )
        
        self._cache = strategy_cache
        self._dto_types = capabilities["dto_types"]
    
    def shutdown(self) -> None:
        """Phase 3: Graceful shutdown (no resources to cleanup)."""
        # Idempotent - no persistent resources
        ...
```

**Key Observations:**
- ✅ Validates required dependencies (fails fast if None)
- ✅ Extracts capabilities from kwargs
- ✅ Stores references for runtime use
- ✅ Idempotent shutdown (safe to call multiple times)
- ✅ Type annotations (strategy_cache can be None for type flexibility)

### Test Workers Analysis

**EventProcessorWorker (scaffolded):**
```python
class EventProcessorWorker:
    """Test worker for string dependencies format."""
    
    def __init__(self, eventbus: EventBus, logger: Logger):
        """Initialize EventProcessorWorker."""
        self.eventbus = eventbus
        self.logger = logger
    
    async def execute(self) -> None:
        """Execute worker logic."""
        pass
```

**Gap Analysis:**
- ❌ No `IWorkerLifecycle` implementation
- ❌ No `initialize()` method
- ❌ No `shutdown()` method
- ❌ Constructor takes dependencies directly (V2 pattern!)
- ❌ No BuildSpec-based construction
- ❌ No capability injection

**Conclusion:** Template-generated workers **DO NOT follow IWorkerLifecycle pattern**.

---

## 3. Template Analysis

### Current Worker Template Output

**Template:** `mcp_server/scaffolding/templates/concrete/worker.py.jinja2`

**Recent Fix (2026-01-27):** Template now accepts both dependency formats:
- String format: `["EventBus", "Logger"]` → `eventbus: EventBus, logger: Logger`
- Dict format: `[{"name": "event_bus", "type": "EventBus"}]` → `event_bus: EventBus`

**Current Generation:**
```python
class {{ name }}:
    """{{ description }}."""
    
    def __init__(self{% for dep in dependencies %}, {{ dep.name if dep is mapping else (dep | lower | replace(' ', '_')) }}: {{ dep.type if dep is mapping else dep }}{% endfor %}):
        """Initialize {{ name }}."""
{% for dep in dependencies %}
        self.{{ dep.name if dep is mapping else (dep | lower | replace(' ', '_')) }} = {{ dep.name if dep is mapping else (dep | lower | replace(' ', '_')) }}
{% endfor %}
    
    async def execute(self) -> None:
        """Execute {{ name }} logic."""
        pass
```

**Generated Code Example:**
```python
class DataProcessorWorker:
    """Processes data with dict deps."""
    
    def __init__(self, event_bus: EventBus, logger: Logger):
        """Initialize DataProcessorWorker."""
        self.event_bus = event_bus
        self.logger = logger
    
    async def execute(self) -> None:
        """Execute DataProcessorWorker logic."""
        pass
```

### Template Gap Analysis

| Feature | IWorkerLifecycle Requires | Template Generates | Status |
|---------|---------------------------|-------------------|--------|
| **Construction** | `__init__(build_spec: BuildSpec)` | `__init__(self, dep1: Type1, ...)` | ❌ GAP |
| **Lifecycle** | `initialize(strategy_cache, **capabilities)` | Not generated | ❌ GAP |
| **Cleanup** | `shutdown()` | Not generated | ❌ GAP |
| **Protocol** | `implements IWorkerLifecycle` | Not declared | ❌ GAP |
| **Dependencies** | Injected via `initialize()` | Constructor parameters | ❌ GAP |
| **Testability** | Mock StrategyCache only | Must mock all dependencies | ⚠️ WORSE |

**Critical Finding:** Template teaches agents **V2 anti-pattern** (constructor injection), not **V3 pattern** (two-phase initialization).

### Issue #52 Research Evidence

From `docs/development/issue52/research.md`:

> **Template Quality Issues**
> - ⚠️ Worker template uses outdated pattern (single-phase init, should be IWorkerLifecycle)
> 
> **Code Pattern Analysis:**
> ```python
> # Actual backend pattern (backend/core/interfaces/worker.py):
> class IWorkerLifecycle(Protocol):
>     """Two-phase initialization:
>     1. __init__(build_spec) - Construction
>     2. initialize(strategy_cache) - Runtime injection
>     """
> 
> # Current template generates (WRONG):
> def __init__(self, strategy_cache, deps):
>     self._strategy_cache = strategy_cache  # ← Should be None, injected in initialize()
> 
> # Should generate:
> def __init__(self, build_spec: BuildSpec):
>     self._manifest = build_spec.manifest
>     self._strategy_cache: IStrategyCache | None = None
>     
> def initialize(self, strategy_cache: IStrategyCache):
>     self._strategy_cache = strategy_cache
> ```

**Conclusion:** This is a **known issue** identified during Issue #52 research, but **not yet fixed**.

---

## 4. Architectural Rationale

### Alignment with Core Principles

From `docs/architecture/CORE_PRINCIPLES.md`:

#### 1. Plugin First
**Principle:** "Alle strategische logica is ingekapseld in zelfstandige, onafhankelijk testbare plugins."

**IWorkerLifecycle Enables:**
- ✅ Workers constructed with BuildSpec (config-decoupled)
- ✅ Workers testable in isolation (mock just StrategyCache)
- ✅ No platform dependencies during construction
- ✅ Plugins remain pure logic, platform handles wiring

**Example:**
```python
# Testing becomes trivial
def test_worker_logic():
    worker = MyWorker(build_spec)  # Construction phase
    mock_cache = Mock(spec=IStrategyCache)
    
    worker.initialize(strategy_cache=mock_cache)  # Inject mock
    
    result = worker.process()  # Test business logic
    assert result.disposition == "PUBLISH"
```

#### 2. Separation of Concerns
**Principle:** "Strikte scheiding tussen wat, waar, hoe en waarmee."

**IWorkerLifecycle Enables:**
- ✅ Workers (the "what") don't know about EventBus (the "waarmee")
- ✅ Workers don't construct own dependencies (Factory handles "hoe")
- ✅ Workers receive StrategyCache (data access layer), not platform internals
- ✅ Clean boundary: Worker business logic ↔ Platform orchestration

**Anti-Pattern (Without Lifecycle):**
```python
# ❌ VIOLATION - Worker knows about platform assembly
class BadWorker:
    def __init__(self, event_bus: EventBus, logger: Logger, ...):
        # Worker now coupled to platform infrastructure
        self.event_bus = event_bus  # Should NOT know about EventBus!
```

#### 3. Configuratie-Gedreven
**Principle:** "Gedrag wordt volledig bestuurd door YAML-bestanden."

**IWorkerLifecycle Enables:**
- ✅ Worker capabilities declared in manifest.yaml
- ✅ Platform reads manifest, injects capabilities via `initialize()`
- ✅ Workers don't read YAML directly (BuildSpec translation)

**Example:**
```yaml
# manifest.yaml
capabilities:
  requires_persistence: true
  requires_strategy_ledger: true
```

```python
# Platform orchestrator
capabilities = {}
if manifest.requires_persistence:
    capabilities['persistence'] = persistence_service

worker.initialize(strategy_cache=cache, **capabilities)
```

#### 4. Contract-Gedreven
**Principle:** "Alle data-uitwisseling wordt gevalideerd door strikte Pydantic-schema's."

**IWorkerLifecycle Enables:**
- ✅ StrategyCache stores/retrieves Pydantic DTOs
- ✅ Workers produce DispositionEnvelope (typed contract)
- ✅ BuildSpec is validated before worker construction
- ✅ Type safety via Protocol (runtime_checkable)

### V2 → V3 Evolution

| Aspect | V2 (Constructor Injection) | V3 (IWorkerLifecycle) |
|--------|----------------------------|----------------------|
| **Circular Deps** | ❌ EventBus ↔ Workers deadlock | ✅ Construct first, inject later |
| **Bootstrap Order** | ❌ Forced ordering (infrastructure → workers) | ✅ Flexible (any order) |
| **Testing** | ❌ Mock 5+ dependencies | ✅ Mock StrategyCache only |
| **Cleanup** | ❌ No standard pattern | ✅ shutdown() contract |
| **Flexibility** | ❌ All deps in constructor | ✅ Optional capabilities via kwargs |

---

## 5. Template-Driven Development: The Meta-Pattern

### Templates as Single Source of Truth

From `docs/development/issue52/research.md`:

> **The Solution:**
> Use templates as Single Source of Truth (SSOT) with layered enforcement:
> - Templates become authoritative source for scaffolding AND validation
> - Template change → validation follows
> - Agent guidance embedded (templates teach what content belongs where)

### The Grammar Metaphor

**Templates are like language grammar:**
- **Grammar defines structure** (subject-verb-object)
- **You have creative freedom in content** (what you say)
- **Without grammar, communication breaks down**
- **Without templates, codebase consistency breaks down**

**Applied to Workers:**
- **Template defines structure** (lifecycle: `__init__` → `initialize` → `shutdown`)
- **Agent has creative freedom** (business logic in `process()` method)
- **Structure = Template, Content = Agent**

### How Agents Learn Patterns

From `docs/development/issue56/architectural_insights.md`:

> **MCP Server Purpose:**
> "Enable human and AI to work in harmony on creative content, while software handles workflow orchestration, project structure, and quality assurance."
> 
> "All workflow mechanics must be enforced through tooling, not documentation."

**Critical Insight:** Agents do NOT learn from reading documentation. They learn by:

1. **Generating code** (scaffolding with templates)
2. **Seeing examples** (generated code IS the example)
3. **Validation feedback** (template-driven validation catches violations)

**Current Problem:**
```
Agent: "Create a worker for me"
↓
Template: Generates simple __init__ with dependencies (V2 pattern)
↓
Agent: "This is how workers work!" (INCORRECT LEARNING)
↓
Agent: Uses same pattern for next worker (perpetuates technical debt)
↓
Codebase: Inconsistent workers, some with lifecycle, some without
```

**Correct Flow:**
```
Agent: "Create a worker for me"
↓
Template: Generates __init__(build_spec) + initialize() + shutdown()
↓
Agent: "This is how workers work!" (CORRECT LEARNING)
↓
Agent: Uses IWorkerLifecycle pattern for all workers (consistent codebase)
↓
Codebase: All workers testable, all workers cleanupable, all workers follow architecture
```

### Why Template-Driven Development Matters for Agentic Codebases

**Traditional Development:**
- Developer reads docs → understands pattern → writes code
- Code review catches violations
- Experience teaches patterns over time

**Agentic Development:**
- Agent generates code → sees pattern in output → infers pattern
- Validation catches violations (if templates correct)
- **Templates ARE the experience**

**Implications:**
1. **Templates must generate correct patterns** (not just "working code")
2. **Templates embed architectural knowledge** (lifecycle, DI, cleanup)
3. **Template changes propagate learning** (all future workers use new pattern)
4. **Consistency at scale** (100 workers, all follow same pattern)

### Content vs Structure: The Balance

**What Agents Control (Creative Freedom):**
- Business logic (what worker does)
- DTO field names and types
- Algorithm choices
- Domain-specific logic

**What Templates Control (Structural Consistency):**
- Lifecycle pattern (two-phase init)
- Dependency injection (BuildSpec + capabilities)
- Cleanup pattern (shutdown)
- Import structure
- Docstring format

**Example:**
```python
# STRUCTURE (Template-controlled)
class {{ name }}(IWorker, IWorkerLifecycle):
    def __init__(self, build_spec: BuildSpec):
        self._manifest = build_spec.manifest
        self._cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache, **capabilities):
        self._cache = strategy_cache
    
    # CONTENT (Agent-controlled)
    async def process(self) -> DispositionEnvelope:
        # Agent decides WHAT to do here
        {% if agent_context.algorithm == "EMA" %}
        ema_value = self._calculate_ema(period={{ agent_context.period }})
        {% elif agent_context.algorithm == "RSI" %}
        rsi_value = self._calculate_rsi(period={{ agent_context.period }})
        {% endif %}
        return DispositionEnvelope(...)
    
    # STRUCTURE (Template-controlled)
    def shutdown(self):
        self._cache = None
```

**Agent Focus:** "I need to calculate EMA" (content)  
**Template Focus:** "Here's how workers are structured" (architecture)

### Evolvability: Pattern Changes Propagate

**Scenario:** V4 requires workers to implement `async def health_check()`

**Without Templates (Manual Update):**
- Update 100 workers manually
- Some developers miss the pattern
- Code review catches some violations
- Codebase drift (some workers have health_check, some don't)

**With Templates (Propagation):**
- Update worker template (add health_check method)
- Regenerate workers or scaffold new ones
- **All new workers automatically have health_check**
- Validation enforces pattern
- Consistent codebase at scale

---

## 6. Impact Analysis: Mandatory vs Optional

### Scenario A: IWorkerLifecycle is MANDATORY

**All workers MUST implement `initialize()` + `shutdown()`**

#### Voordelen:
1. **Guaranteed Consistent Lifecycle**
   - All workers follow same pattern
   - Bootstrap code is simple (no conditionals)
   - Platform can rely on `shutdown()` for cleanup
   
2. **Single Testable Pattern**
   - All workers tested same way (mock StrategyCache)
   - Test helpers can be reused across workers
   - Onboarding: Learn one pattern, applies to all
   
3. **Template as SSOT**
   - Template always generates lifecycle methods
   - Agents learn correct pattern from day one
   - No "legacy workers" with old pattern
   
4. **Architectural Integrity**
   - Aligns with Plugin First (testable isolation)
   - Aligns with Separation of Concerns (DI pattern)
   - Aligns with Contract-Gedreven (Protocol enforcement)

#### Nadelen:
1. **More Boilerplate for Simple Workers**
   - Even trivial workers need `initialize()` + `shutdown()`
   - Example: Simple calculator worker (no resources, no state)
   
2. **Learning Curve**
   - New plugin developers must understand two-phase init
   - More concepts to grasp initially
   
3. **Breaking Change**
   - Existing workers (if any) must be migrated
   - **Current Impact:** Only 2 test workers affected (low)
   
4. **Template Complexity**
   - Template must generate lifecycle blocks
   - More Jinja2 logic (conditionals, blocks)

#### Implementation:
```python
# Template always generates
class {{ name }}(IWorker, IWorkerLifecycle):
    def __init__(self, build_spec: BuildSpec):
        self._manifest = build_spec.manifest
        self._cache: IStrategyCache | None = None
        {% for cap in capabilities %}
        self._{{ cap }} = None
        {% endfor %}
    
    def initialize(self, strategy_cache, **capabilities):
        if strategy_cache is None:
            raise WorkerInitializationError("cache required")
        self._cache = strategy_cache
        {% for cap in capabilities %}
        self._{{ cap }} = capabilities.get('{{ cap }}')
        {% endfor %}
    
    async def process(self):
        # Agent provides business logic
        {{ agent_business_logic }}
    
    def shutdown(self):
        self._cache = None
        {% for cap in capabilities %}
        self._{{ cap }} = None
        {% endfor %}
```

---

### Scenario B: IWorkerLifecycle is OPTIONAL

**Workers CAN implement lifecycle, but not required**

#### Voordelen:
1. **Simpler Workers Possible**
   - Trivial workers don't need boilerplate
   - Gradual adoption (add lifecycle when needed)
   
2. **Backwards Compatible**
   - Existing workers don't break
   - Legacy code can coexist with new pattern
   
3. **Lower Initial Barrier**
   - New developers start with simple pattern
   - Learn lifecycle when complexity demands it

#### Nadelen:
1. **Inconsistent Codebase**
   - Some workers have lifecycle, some don't
   - Developers must know which pattern applies when
   - Hard to navigate: "Which workers can I shutdown?"
   
2. **Platform Complexity**
   - Bootstrap code needs conditionals:
     ```python
     for worker in workers:
         if isinstance(worker, IWorkerLifecycle):
             worker.initialize(cache)
         # else what? Just use directly?
     ```
   
3. **No Guaranteed Cleanup**
   - Workers without `shutdown()` can't be cleaned up
   - Memory leaks if worker holds resources
   
4. **Testing Inconsistency**
   - Some workers tested with mocks, some with real deps
   - Test helpers can't be universally reused
   
5. **Template Confusion**
   - Template needs flag: `lifecycle_enabled: bool`
   - Agents must decide when to use lifecycle (how?)
   - Default matters (opt-in vs opt-out)

#### Implementation:
```python
# Template conditionally generates
{% if lifecycle_enabled %}
class {{ name }}(IWorker, IWorkerLifecycle):
    def __init__(self, build_spec: BuildSpec):
        ...
    def initialize(self, strategy_cache, **capabilities):
        ...
    def shutdown(self):
        ...
{% else %}
class {{ name }}:
    def __init__(self{% for dep in dependencies %}, {{ dep }}{% endfor %}):
        ...
{% endif %}
```

**Problem:** When should agent set `lifecycle_enabled=true`? Without guidance, agents default to `false` (less boilerplate).

---

### Scenario C: MANDATORY with Explicit Opt-Out

**Default: All workers have lifecycle. Opt-out: `lifecycle_enabled=false` (discouraged)**

#### Voordelen:
1. **Default Consistency**
   - Agents generate lifecycle by default
   - Codebase is consistent unless explicitly overridden
   
2. **Flexibility When Needed**
   - Simple workers CAN opt-out (with justification)
   - Special cases handled without breaking pattern
   
3. **Clear Opt-Out Signal**
   - `lifecycle_enabled=false` is explicit decision
   - Code review can ask: "Why opt-out?"
   - Audit: "Which workers opted out and why?"
   
4. **Template Educates**
   - Default template teaches correct pattern
   - Opt-out requires understanding pattern first
   - Agents learn lifecycle is "normal", opt-out is "exception"

#### Nadelen:
1. **Requires Opt-Out Decision**
   - Simple workers still need `lifecycle_enabled=false`
   - Decision fatigue: "Do I need to opt-out?"
   
2. **Slightly More Template Complexity**
   - Conditional Jinja2 blocks
   - But complexity is justified (flexibility vs consistency)

#### Implementation:
```python
# Template generates lifecycle BY DEFAULT
# Context: lifecycle_enabled defaults to true
{% if lifecycle_enabled %}  # Default: true
class {{ name }}(IWorker, IWorkerLifecycle):
    # ... lifecycle methods ...
{% else %}  # Explicit opt-out
class {{ name }}:
    # ... simple pattern ...
{% endif %}
```

**Usage:**
```python
# Default (lifecycle generated)
scaffold_artifact(type="worker", name="SignalDetector")

# Explicit opt-out (must justify)
scaffold_artifact(
    type="worker", 
    name="TrivialCalculator",
    context={"lifecycle_enabled": false, "opt_out_reason": "Pure function, no resources"}
)
```

---

## 7. Recommendations

### Primary Recommendation: **MANDATORY with Opt-Out**

**All workers MUST implement IWorkerLifecycle BY DEFAULT. Opt-out requires explicit `lifecycle_enabled=false` flag with justification.**

### Rationale

#### 1. Aligns with All 4 Core Principles

| Principle | How Lifecycle Supports |
|-----------|----------------------|
| **Plugin First** | Workers testable in isolation (mock StrategyCache only) |
| **Separation of Concerns** | Workers don't know about EventBus/platform assembly (DI via initialize) |
| **Configuratie-Gedreven** | Capabilities declared in manifest.yaml, injected at runtime |
| **Contract-Gedreven** | IWorkerLifecycle is Protocol (type-safe, runtime checkable) |

#### 2. Template as Authoritative Learning Source

**For Agentic Development:**
- Agents learn by **generating code**, not reading docs
- Template generates **correct pattern by default**
- Agents see IWorkerLifecycle in every scaffolded worker
- **Learning propagates**: All future workers follow pattern

**Counter-Argument:** "But agents can read docs!"
**Response:** Experience shows agents do NOT reliably follow documentation. Tooling must enforce structure. From Issue #56:
> "Referring agents to agent.md text files is insufficient to guarantee structured development of complex projects."

#### 3. Structural Consistency Enables Creative Freedom

**Balance:**
- **Structure (Template-controlled):** Lifecycle pattern, DI, cleanup
- **Content (Agent-controlled):** Business logic, algorithm choices, domain knowledge

**Analogy:**
- Recipe template provides structure (ingredients section, steps section)
- Chef provides content (which ingredients, which steps)
- Without structure, recipe is chaos
- Without content, recipe is empty

**Worker Example:**
- Template provides structure (two-phase init, shutdown)
- Agent provides content (EMA calculation logic)
- Without structure, worker is inconsistent
- Without content, worker does nothing

#### 4. Long-Term Maintainability

**At Scale (100+ workers):**
- **Mandatory:** All workers follow pattern, bootstrap code is simple, cleanup guaranteed
- **Optional:** Mix of patterns, conditionals in platform code, some workers don't cleanup

**Evolution (V4, V5, V6):**
- **Mandatory:** Change template, all new workers adopt pattern automatically
- **Optional:** Must maintain backward compatibility with both patterns forever

**Audit/Debugging:**
- **Mandatory:** "All workers support shutdown" (can inspect resources)
- **Optional:** "Check if worker supports shutdown first" (runtime type checks)

### Implementation Path

#### Step 1: Create Tier 3 Template (4 hours)

**File:** `mcp_server/scaffolding/templates/tier3_base_python_component.jinja2`

**Purpose:** Provide component-level patterns (lifecycle, DI) for Python workers

**Structure:**
```jinja2
{# tier3_base_python_component.jinja2 #}
{# Extends: tier2_base_python.jinja2 #}
{# Purpose: Component patterns - lifecycle, dependency injection, cleanup #}

{% extends "tier2_base_python.jinja2" %}

{% block class_definition %}
class {{ name }}(IWorker, IWorkerLifecycle):
    """{{ description }}."""
{% endblock %}

{% block init_method %}
    def __init__(self, build_spec: BuildSpec) -> None:
        """
        Construct {{ name }} from BuildSpec.
        
        Args:
            build_spec: Worker build specification (config-decoupled)
        """
        self._manifest = build_spec.manifest
        self._cache: IStrategyCache | None = None
        {% if capabilities %}
        {% for cap in capabilities %}
        self._{{ cap }}: Any | None = None
        {% endfor %}
        {% endif %}
{% endblock %}

{% block lifecycle_methods %}
    def initialize(
        self,
        strategy_cache: IStrategyCache | None = None,
        **capabilities: Any
    ) -> None:
        """
        Initialize {{ name }} with runtime dependencies.
        
        Args:
            strategy_cache: Strategy data access layer
            **capabilities: Optional runtime capabilities
        
        Raises:
            WorkerInitializationError: If initialization fails
        """
        {% if worker_scope == "Strategy" or worker_scope == "Platform-within-Strategy" %}
        # {{ worker_scope }} worker requires strategy_cache
        if strategy_cache is None:
            raise WorkerInitializationError(
                f"{self.name}: strategy_cache required for {{ worker_scope }} worker"
            )
        {% endif %}
        
        self._cache = strategy_cache
        
        {% if capabilities %}
        # Extract optional capabilities
        {% for cap in capabilities %}
        self._{{ cap }} = capabilities.get('{{ cap }}')
        {% endfor %}
        {% endif %}
    
    def shutdown(self) -> None:
        """
        Graceful shutdown and resource cleanup.
        
        Implements IWorkerLifecycle requirement.
        """
        self._cache = None
        {% if capabilities %}
        {% for cap in capabilities %}
        self._{{ cap }} = None
        {% endfor %}
        {% endif %}
{% endblock %}

{% block business_methods %}
    # Business logic methods - Agent provides implementation
    {% if async_process %}
    async def process(self) -> DispositionEnvelope:
        """Process worker logic (async)."""
        # TODO: Implement business logic
        raise NotImplementedError("Agent must implement process()")
    {% else %}
    def process(self) -> DispositionEnvelope:
        """Process worker logic (sync)."""
        # TODO: Implement business logic
        raise NotImplementedError("Agent must implement process()")
    {% endif %}
{% endblock %}
```

**Testing:**
```python
# tests/unit/scaffolding/test_tier3_python_component.py

def test_tier3_generates_iworkerlifecycle_pattern():
    """Tier 3 template generates IWorkerLifecycle methods."""
    template = env.get_template("tier3_base_python_component.jinja2")
    
    output = template.render(
        name="TestWorker",
        description="Test worker for lifecycle",
        worker_scope="Strategy",
        capabilities=["persistence", "strategy_ledger"]
    )
    
    # Verify lifecycle methods present
    assert "def __init__(self, build_spec: BuildSpec)" in output
    assert "def initialize(self, strategy_cache" in output
    assert "def shutdown(self)" in output
    
    # Verify capability injection
    assert "self._persistence" in output
    assert "self._strategy_ledger" in output
    
    # Verify validation
    assert "if strategy_cache is None:" in output
    assert "WorkerInitializationError" in output
```

#### Step 2: Update Concrete Worker Template (2 hours)

**File:** `mcp_server/scaffolding/templates/concrete/worker.py.jinja2`

**Changes:**
```jinja2
{# concrete/worker.py.jinja2 #}
{% extends "tier3_base_python_component.jinja2" %}

{# Context variables:
  - lifecycle_enabled: bool (default: true)
  - opt_out_reason: str (required if lifecycle_enabled=false)
#}

{% if not lifecycle_enabled %}
{# OPT-OUT PATH: Simple worker without lifecycle #}
{% extends "tier2_base_python.jinja2" %}

{% block class_definition %}
class {{ name }}:
    """
    {{ description }}.
    
    ⚠️ LIFECYCLE OPT-OUT: {{ opt_out_reason }}
    """
{% endblock %}

{% block init_method %}
    def __init__(self{% for dep in dependencies %}, {{ dep }}{% endfor %}):
        """Initialize {{ name }} (opt-out from IWorkerLifecycle)."""
        {% for dep in dependencies %}
        self.{{ dep.name }} = {{ dep.name }}
        {% endfor %}
{% endblock %}

{% else %}
{# DEFAULT PATH: Full IWorkerLifecycle implementation #}

{% block business_methods %}
    async def process(self) -> DispositionEnvelope:
        """
        Process {{ name }} business logic.
        
        {{ agent_implementation_hint | default("Agent implements worker logic here") }}
        """
        # Agent-provided implementation
        {{ agent_business_logic | default("raise NotImplementedError('Implement worker logic')") }}
{% endblock %}

{% endif %}
```

#### Step 3: Validation Rules (2 hours)

**File:** `mcp_server/validation/template_metadata.py`

**Add Lifecycle Validation:**
```python
# Worker template metadata
WORKER_TEMPLATE_METADATA = {
    "enforcement": "ARCHITECTURAL",
    "rules": {
        "strict": [
            {
                "rule": "must_implement_iworkerlifecycle",
                "pattern": r"class \w+\(.*IWorkerLifecycle.*\)",
                "message": "Workers MUST implement IWorkerLifecycle (unless lifecycle_enabled=false)",
                "severity": "ERROR"
            },
            {
                "rule": "must_have_initialize",
                "pattern": r"def initialize\(self, strategy_cache",
                "message": "Workers MUST have initialize(strategy_cache, **capabilities) method",
                "severity": "ERROR"
            },
            {
                "rule": "must_have_shutdown",
                "pattern": r"def shutdown\(self\)",
                "message": "Workers MUST have shutdown() method for cleanup",
                "severity": "ERROR"
            }
        ],
        "opt_out": {
            "flag": "lifecycle_enabled",
            "requires": ["opt_out_reason"],
            "warning": "Worker opted out of IWorkerLifecycle pattern. Reason: {opt_out_reason}"
        }
    }
}
```

#### Step 4: Regenerate Test Workers (1 hour)

**Delete Current Test Workers:**
- `backend/workers/event_processor_worker.py`
- `backend/workers/data_processor_worker.py`

**Regenerate with Lifecycle:**
```python
scaffold_artifact(
    type="worker",
    name="EventProcessorWorker",
    context={
        "description": "Processes events from event bus",
        "worker_scope": "Strategy",
        "capabilities": ["persistence"],
        "agent_business_logic": "# Process events here"
    }
)

scaffold_artifact(
    type="worker",
    name="DataProcessorWorker",
    context={
        "description": "Processes data with lifecycle",
        "worker_scope": "Strategy",
        "capabilities": ["strategy_ledger"],
        "agent_business_logic": "# Process data here"
    }
)
```

**Expected Output:**
```python
class EventProcessorWorker(IWorker, IWorkerLifecycle):
    """Processes events from event bus."""
    
    def __init__(self, build_spec: BuildSpec) -> None:
        self._manifest = build_spec.manifest
        self._cache: IStrategyCache | None = None
        self._persistence: Any | None = None
    
    def initialize(self, strategy_cache, **capabilities):
        if strategy_cache is None:
            raise WorkerInitializationError("cache required for Strategy worker")
        self._cache = strategy_cache
        self._persistence = capabilities.get('persistence')
    
    async def process(self) -> DispositionEnvelope:
        # Process events here
        raise NotImplementedError("Implement worker logic")
    
    def shutdown(self):
        self._cache = None
        self._persistence = None
```

#### Step 5: Update Documentation (1 hour)

**Files to Update:**
- `docs/development/issue72/planning.md` - Mark Task 2.2 as COMPLETE
- `docs/architecture/CORE_PRINCIPLES.md` - Add IWorkerLifecycle example
- `docs/reference/templates/worker_template.md` - Document lifecycle pattern

### Phase 2 Impact

#### Task 2.1 (Inheritance Introspection)
**Relation:** Tier 3 template uses inheritance (`{% extends %}`)
- Introspection must return variables from Tier 3 + Tier 2 + Tier 1 + Tier 0
- Worker template introspection should return: `build_spec`, `capabilities`, `worker_scope`, `description`, `agent_business_logic`, etc.

#### Task 2.3 (Backend Pattern Inventory)
**Relation:** IWorkerLifecycle is one pattern among many
- Two-phase initialization is component-level pattern (Tier 3)
- Other patterns to inventory: DI, error handling, logging, config
- Patterns assigned to Tier 2 (syntax) or Tier 3 (specialization)

#### Task 2.4 (Agent Hint Format)
**Relation:** Lifecycle pattern needs agent guidance
- Hint: "Use `initialize()` for dependency injection, not `__init__`"
- Hint: "Store dependencies as private attributes (underscore prefix)"
- Hint: "`shutdown()` must be idempotent and never raise exceptions"

---

## 8. Definition of Done

### Acceptance Criteria

- [ ] **Tier 3 Template Created**
  - `tier3_base_python_component.jinja2` exists
  - Extends `tier2_base_python.jinja2`
  - Generates `IWorkerLifecycle` methods (`initialize`, `shutdown`)
  - Validates `strategy_cache` based on `worker_scope`
  - Injects capabilities from `**kwargs`

- [ ] **Worker Template Updated**
  - `concrete/worker.py.jinja2` extends Tier 3
  - Default: `lifecycle_enabled=true` (generates lifecycle)
  - Opt-out: `lifecycle_enabled=false` requires `opt_out_reason`
  - Conditional Jinja2 blocks handle both paths

- [ ] **Validation Rules Added**
  - Worker files validated for `IWorkerLifecycle` implementation
  - `initialize()` method presence checked
  - `shutdown()` method presence checked
  - Opt-out flag validated (requires reason)

- [ ] **Test Workers Regenerated**
  - `EventProcessorWorker` uses IWorkerLifecycle
  - `DataProcessorWorker` uses IWorkerLifecycle
  - Both workers pass validation
  - Both workers have `initialize()` + `shutdown()`

- [ ] **Documentation Updated**
  - planning.md marks Task 2.2 as COMPLETE
  - CORE_PRINCIPLES.md includes IWorkerLifecycle example
  - worker_template.md documents lifecycle pattern

- [ ] **Tests Pass**
  - All 1498 tests still pass
  - New tests for Tier 3 template (15+ tests)
  - Validation tests for lifecycle enforcement (10+ tests)

### Quality Gates

- [ ] **Linting**: 10/10 (Ruff + Pylint)
- [ ] **Type Checking**: mypy passes (no type errors)
- [ ] **Test Coverage**: 100% on new Tier 3 template code
- [ ] **Template Validation**: All workers pass template-driven validation

---

## 9. Next Steps

### Immediate Actions (This Session)

1. ✅ **Complete Audit Report** (THIS DOCUMENT)
   - Comprehensive analysis of IWorkerLifecycle usage
   - Architectural rationale with core principles
   - Template-driven development philosophy
   - Recommendations with implementation path

2. **Commit Audit Report**
   - File: `docs/development/issue72/phase2-task22-iworkerlifecycle-audit.md`
   - Commit message: "docs: Complete Phase 2 Task 2.2 IWorkerLifecycle audit"

### Follow-Up Tasks (Phase 2 Continuation)

**Task 2.2a: Tier 3 Template Creation** (4 hours)
- Create `tier3_base_python_component.jinja2`
- Add lifecycle blocks (`__init__`, `initialize`, `shutdown`)
- Add validation logic (strategy_cache checks)
- Write 15+ unit tests for Tier 3 template

**Task 2.2b: Worker Template Update** (2 hours)
- Update `concrete/worker.py.jinja2` to extend Tier 3
- Add conditional logic (`lifecycle_enabled` flag)
- Default to lifecycle (opt-out requires reason)

**Task 2.2c: Validation Integration** (2 hours)
- Add lifecycle validation rules to metadata
- Integrate with SafeEditTool and ValidatorRegistry
- Test validation enforcement

**Task 2.2d: Worker Regeneration** (1 hour)
- Regenerate `EventProcessorWorker` with lifecycle
- Regenerate `DataProcessorWorker` with lifecycle
- Verify both pass quality gates

**Task 2.2e: Documentation** (1 hour)
- Update planning.md (mark Task 2.2 COMPLETE)
- Update CORE_PRINCIPLES.md (add lifecycle example)
- Create worker_template.md reference doc

**Total Estimate:** 10 hours (original estimate: 6h audit + 4h implementation)

### Dependencies

**Blocks:**
- Task 3.1 (Tier 3 Python Component Template) - SAME TASK
- Task 3.2 (Tier 3 Python Data Model Template) - Uses same tier

**Depends On:**
- None (Task 2.2 has no blockers)

**Parallel:**
- Task 2.3 (Backend Pattern Inventory) - Can run in parallel
- Task 2.4 (Agent Hint Format) - Can run in parallel

---

## 10. Conclusion

IWorkerLifecycle is **architecturally sound** but **critically underutilized**. The protocol solves real V2 problems (circular dependencies, no cleanup contract), aligns perfectly with all 4 core principles, and enables Plugin First testability.

**The Root Cause:** Worker template generates **V2 anti-pattern** (constructor injection), not **V3 pattern** (two-phase initialization). This teaches agents the wrong pattern, perpetuating technical debt.

**The Solution:** Make IWorkerLifecycle **MANDATORY with opt-out**, implement via **Tier 3 template**, and let **template-driven development** propagate the correct pattern to all future workers.

**Strategic Value:** This is not just about one protocol - it's about establishing **templates as the authoritative learning mechanism** for agentic codebases. When templates generate correct patterns, agents learn correct patterns. When templates generate wrong patterns, technical debt scales.

**Meta-Insight:** In agentic development, **tooling is pedagogy**. Templates teach. Validation reinforces. Generation propagates. This is the foundation for consistent, scalable, high-quality codebases built in collaboration with AI agents.

---

**Task 2.2 Status:** ✅ **COMPLETE** (Audit Phase)  
**Next Phase:** Implementation (Tasks 2.2a-2.2e)  
**Total Effort:** 10 hours (audit + implementation)
