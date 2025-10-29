# Config → BuildSpec Translation Design

**Status:** OPEN DESIGN QUESTION  
**Phase:** Bootstrap Architecture (Pre-Phase 2)  
**Created:** 2025-10-29  
**Priority:** HIGH - Architectural Foundation

## Design Question

**Context:** We willen volledige ontkoppeling tussen YAML configuratie (user-facing) en BuildSpecs (factory machine instructions).

**Question:** Verliezen we door te 'ontkoppelen' van YAML en de structuur die deze heeft (logisch voor user → doel configuratie) en over te stappen op BuildSpecs (logisch voor Factories/Singletons/Etc. → doel bouwen), typing of andere voordelen die Pydantic ons biedt in de gelezen config structuur?

**Impact:** Dit bepaalt fundamenteel hoe we configuration validation, type safety, en developer experience balanceren.

---

## Current Understanding: The Translation Pipeline

```
YAML Files → ConfigLoader → Pydantic Models → ConfigValidator → ConfigTranslator → BuildSpecs → Factories
```

### Step-by-Step Breakdown

**Step 1: YAML → Pydantic Models (ConfigLoader)**
```python
# config/strategy/ema_crossover.yaml
strategy:
  name: "EMA Crossover"
  workers:
    - type: "ema_context"
      params:
        fast_period: 12
        slow_period: 26

# Loaded into Pydantic model
class StrategyConfig(BaseModel):
    name: str
    workers: list[WorkerConfigEntry]

class WorkerConfigEntry(BaseModel):
    type: str
    params: dict[str, Any]  # Untyped dict!
```

**Step 2: Pydantic Validation (ConfigValidator)**
```python
# Validates structure, NOT worker-specific params
config = StrategyConfig.model_validate(yaml_data)
# ✅ Validates: strategy.name is str
# ✅ Validates: workers is list
# ❌ Does NOT validate: fast_period is int (params is just dict!)
```

**Step 3: Translation to BuildSpecs (ConfigTranslator)**
```python
# ConfigTranslator converts to factory instructions
class WorkerBuildSpec(BaseModel):
    worker_class: type  # Actual class reference
    config_params: dict[str, Any]  # Still untyped dict!
    capabilities: WorkerCapabilities
    manifest: WorkerManifest

# Translation
def translate_worker_config(entry: WorkerConfigEntry) -> WorkerBuildSpec:
    # Load worker manifest to get schema
    manifest = load_manifest(entry.type)
    
    # Validate params against manifest schema
    validate_params(entry.params, manifest.schema)
    
    return WorkerBuildSpec(
        worker_class=get_worker_class(entry.type),
        config_params=entry.params,  # Pass through as dict
        capabilities=parse_capabilities(manifest),
        manifest=manifest
    )
```

**Step 4: Factory Construction**
```python
# WorkerFactory builds from BuildSpec
class WorkerFactory:
    def build_worker(self, spec: WorkerBuildSpec) -> IWorker:
        # BuildSpec.config_params is still dict[str, Any]
        worker = spec.worker_class(config_params=spec.config_params)
        return worker
```

---

## The Core Problem: Type Safety Gap

### Where Pydantic Typing Gets Lost

**Current Flow:**
```python
# 1. YAML (untyped text)
fast_period: 12

# 2. ConfigLoader → Generic Pydantic model
class WorkerConfigEntry(BaseModel):
    params: dict[str, Any]  # ❌ Lost specificity!

# 3. ConfigTranslator → BuildSpec
class WorkerBuildSpec(BaseModel):
    config_params: dict[str, Any]  # ❌ Still untyped!

# 4. Factory → Worker Constructor
worker = EMAWorker(config_params={'fast_period': 12})  # ❌ No type checking!
```

**The Gap:**
- **YAML structure** is user-friendly: `workers[].params.fast_period`
- **Pydantic ConfigLoader** is generic: `dict[str, Any]` (no worker-specific typing)
- **BuildSpec** is factory-focused: `dict[str, Any]` (params pass-through)
- **Worker Constructor** expects typed params but has no compile-time validation

---

## Proposed Solutions

### Option 1: Plugin Schema Validation (Current Implicit Approach)

**Strategy:** Each worker plugin defines its own `schema.py` with Pydantic model for params validation

**Plugin Structure:**
```
plugins/ema_context/
├── manifest.yaml           # Plugin metadata + capabilities
├── worker.py               # Business logic (EMAWorker class)
├── schema.py               # ✅ WORKER DEFINES ITS OWN PARAM SCHEMA!
└── test/
    └── test_worker.py      # Unit tests
```

**Worker Schema Definition:**
```python
# plugins/ema_context/schema.py
from pydantic import BaseModel, Field

class EMAContextParams(BaseModel):
    """
    Parameter schema for EMA Context Worker.
    
    This schema is OWNED by the plugin and defines:
    - Parameter types
    - Validation constraints
    - Default values
    - Custom validators
    """
    fast_period: int = Field(gt=0, le=200, description="Fast EMA period")
    slow_period: int = Field(gt=0, le=200, description="Slow EMA period")
    
    @model_validator(mode='after')
    def validate_period_order(self) -> 'EMAContextParams':
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be < slow_period")
        return self
```

**Manifest References Schema:**
```yaml
# plugins/ema_context/manifest.yaml
identification:
  name: "ema_context"
  type: "context_worker"
  version: "1.0.0"

schema:
  path: "schema.py"  # ✅ Manifest points to worker's schema
  class: "EMAContextParams"

capabilities:
  requires_persistence: false
  requires_strategy_ledger: false
```

**ConfigTranslator Uses Worker Schema:**
```python
# ConfigTranslator validates using WORKER'S schema
def translate_worker_config(entry: WorkerConfigEntry) -> WorkerBuildSpec:
    # 1. Load manifest
    manifest = load_manifest(entry.type)  # "ema_context"
    
    # 2. Load WORKER'S schema class (defined by plugin!)
    schema_path = manifest.schema.path  # "schema.py"
    schema_class = load_schema_class(
        plugin_dir=f"plugins/{entry.type}",
        schema_path=schema_path,
        class_name=manifest.schema.class_name  # "EMAContextParams"
    )
    
    # 3. ✅ Validate params using WORKER'S Pydantic schema
    validated_params = schema_class.model_validate(entry.params)
    
    # 4. Create BuildSpec with validated dict
    return WorkerBuildSpec(
        worker_class=get_worker_class(entry.type),
        config_params=validated_params.model_dump(),  # Validated dict
        capabilities=parse_capabilities(manifest),
        manifest=manifest
    )
```

**Pros:**
- ✅ Full Pydantic validation (types, constraints, custom validators)
- ✅ **Worker OWNS its parameter schema** - plugin defines validation rules
- ✅ ConfigTranslator validates at translation time (fail-fast)
- ✅ BuildSpec remains factory-agnostic (just validated dict)
- ✅ Separation of concerns: plugin controls its contract
- ✅ UI can generate forms from worker's schema.py (dynamic configuration)

**Cons:**
- ⚠️ Validation happens at runtime (translation time), not compile time
- ⚠️ Worker constructor still receives `dict[str, Any]` (no type hints in constructor signature)
- ⚠️ Plugin schema must be loaded dynamically from manifest reference

**Example Flow:**
```python
# 1. YAML (user configuration)
# config/strategies/my_strategy.yaml
workforce:
  - plugin_name: "ema_context"
    instance_id: "ema_1"
    params:
      fast_period: 12
      slow_period: 26

# 2. ConfigLoader (generic Pydantic - structure validation only)
class WorkerConfigEntry(BaseModel):
    plugin_name: str
    instance_id: str
    params: dict[str, Any]  # Generic dict, NOT worker-specific!

entry = WorkerConfigEntry.model_validate(yaml_data)
# ✅ Validates: plugin_name is str, params exists
# ❌ Does NOT validate: fast_period type/constraints

# 3. ConfigTranslator (WORKER schema validation)
manifest = load_manifest("ema_context")
# manifest.schema.path = "schema.py"
# manifest.schema.class_name = "EMAContextParams"

schema_class = load_schema_class(
    plugin_dir="plugins/ema_context",
    schema_path=manifest.schema.path,
    class_name=manifest.schema.class_name
)
# schema_class = EMAContextParams (worker's Pydantic model)

validated_params = schema_class.model_validate(entry.params)
# ✅ WORKER's schema validates: fast_period is int, 0 < fast_period <= 200
# ✅ WORKER's custom validator: fast_period < slow_period

validated_dict = validated_params.model_dump()
# {'fast_period': 12, 'slow_period': 26}

# 4. BuildSpec (validated dict - factory-agnostic)
WorkerBuildSpec(
    worker_class=EMAWorker,
    config_params=validated_dict,  # Pre-validated by worker's schema
    manifest=manifest
)

# 5. Factory → Worker
worker = EMAWorker(spec=spec)
# Worker constructor receives pre-validated dict
```

---

### Option 2: BuildSpec Generics (Type-Safe BuildSpecs)

**Strategy:** Make BuildSpec generic over param schema class

```python
from typing import Generic, TypeVar

TParams = TypeVar('TParams', bound=BaseModel)

class WorkerBuildSpec(BaseModel, Generic[TParams]):
    worker_class: type
    config_params: TParams  # ✅ Typed! Not dict[str, Any]
    capabilities: WorkerCapabilities
    manifest: WorkerManifest

# ConfigTranslator creates typed BuildSpecs
def translate_worker_config(entry: WorkerConfigEntry) -> WorkerBuildSpec:
    manifest = load_manifest(entry.type)
    schema_class = load_schema_class(manifest.schema_path)
    
    # Validate and create typed params
    validated_params = schema_class.model_validate(entry.params)
    
    return WorkerBuildSpec[schema_class](  # Generic type!
        worker_class=get_worker_class(entry.type),
        config_params=validated_params,  # Pydantic model instance
        capabilities=parse_capabilities(manifest),
        manifest=manifest
    )

# Factory receives typed BuildSpec
def build_worker(spec: WorkerBuildSpec[EMAContextParams]) -> EMAWorker:
    # spec.config_params is EMAContextParams instance (typed!)
    worker = EMAWorker(
        fast_period=spec.config_params.fast_period,  # ✅ Type-safe access
        slow_period=spec.config_params.slow_period
    )
    return worker
```

**Pros:**
- ✅ Full type safety from ConfigTranslator → Factory → Worker
- ✅ IDE autocomplete on `spec.config_params.fast_period`
- ✅ Pydantic validation happens once (at translation)
- ✅ Worker constructor can be strongly typed

**Cons:**
- ⚠️ BuildSpec is no longer uniform (different generic types per worker)
- ⚠️ Factory must handle heterogeneous BuildSpec types
- ⚠️ More complex type signatures (Generic[TParams])
- ⚠️ WorkerFactory.build_worker() loses uniform signature

**Challenge:**
```python
# Problem: How does WorkerFactory handle different BuildSpec types?
class WorkerFactory:
    def build_worker(
        self,
        spec: WorkerBuildSpec[???]  # ❌ What type? Each worker differs!
    ) -> IWorker:
        ...

# Possible solution: Type erasure via Protocol
class WorkerFactory:
    def build_worker(self, spec: WorkerBuildSpec[Any]) -> IWorker:
        # Dispatch to worker-specific builder
        builder = self._get_builder(spec.worker_class)
        return builder.build(spec)
```

---

### Option 3: Hybrid - Validated Dict with Schema Reference

**Strategy:** BuildSpec stores validated dict + schema class reference for re-validation

```python
class WorkerBuildSpec(BaseModel):
    worker_class: type
    config_params: dict[str, Any]  # Validated dict
    param_schema: type[BaseModel]  # Schema class reference
    capabilities: WorkerCapabilities
    manifest: WorkerManifest
    
    def get_typed_params(self) -> BaseModel:
        """Re-instantiate typed params from validated dict."""
        return self.param_schema.model_validate(self.config_params)

# ConfigTranslator validates + stores schema
def translate_worker_config(entry: WorkerConfigEntry) -> WorkerBuildSpec:
    manifest = load_manifest(entry.type)
    schema_class = load_schema_class(manifest.schema_path)
    
    validated_params = schema_class.model_validate(entry.params)
    
    return WorkerBuildSpec(
        worker_class=get_worker_class(entry.type),
        config_params=validated_params.model_dump(),
        param_schema=schema_class,  # Store for re-validation
        capabilities=parse_capabilities(manifest),
        manifest=manifest
    )

# Factory can re-instantiate typed params
def build_worker(spec: WorkerBuildSpec) -> IWorker:
    typed_params = spec.get_typed_params()  # Pydantic model instance
    
    # Worker-specific builder knows param schema
    if spec.worker_class == EMAWorker:
        return EMAWorker(
            fast_period=typed_params.fast_period,
            slow_period=typed_params.slow_period
        )
```

**Pros:**
- ✅ BuildSpec remains uniform (no generics)
- ✅ Validation happens once (at translation)
- ✅ Factory can re-instantiate typed params if needed
- ✅ Flexibility: use dict or typed params depending on context

**Cons:**
- ⚠️ Double validation possible (translation + factory re-instantiation)
- ⚠️ Factory still needs type casting / dispatch logic
- ⚠️ No compile-time type safety in factory signatures

---

## Recommendation: Option 1 + Worker Constructor Enhancement

**Why Option 1:**
- ✅ Simplest implementation (no generics complexity)
- ✅ **Worker OWNS parameter validation** - plugin defines its contract via schema.py
- ✅ ConfigTranslator enforces validation using worker's schema (fail-fast)
- ✅ BuildSpec stays uniform (factory-friendly)
- ✅ Validation happens once (fail-fast at translation)
- ✅ **Matches V2 architecture**: Workers define schema.py, manifest references it

**Enhancement: Worker Constructor Pattern**

Instead of losing typing at worker constructor, enforce this pattern:

```python
# Worker constructor takes BuildSpec + uses its own schema internally
class EMAWorker:
    def __init__(self, spec: WorkerBuildSpec):
        # Worker validates params using ITS OWN schema (defense in depth)
        from .schema import EMAContextParams
        
        self._params = EMAContextParams.model_validate(spec.config_params)
        self._fast_period = self._params.fast_period  # ✅ Typed access
        self._slow_period = self._params.slow_period  # ✅ Typed access
    
    # Alternative: @classmethod builder pattern
    @classmethod
    def from_spec(cls, spec: WorkerBuildSpec) -> 'EMAWorker':
        """Factory method using worker's schema."""
        from .schema import EMAContextParams
        params = EMAContextParams.model_validate(spec.config_params)
        return cls._create(params)
    
    @classmethod
    def _create(cls, params: EMAContextParams) -> 'EMAWorker':
        """Internal typed constructor."""
        instance = cls.__new__(cls)
        instance._fast_period = params.fast_period  # ✅ Typed!
        instance._slow_period = params.slow_period  # ✅ Typed!
        return instance
```

**Complete Validation Flow:**

```
User YAML
  ↓
ConfigLoader (structure validation: plugin_name, instance_id exist)
  ↓
ConfigTranslator loads WORKER's schema.py via manifest reference
  ↓
ConfigTranslator validates params using WORKER's Pydantic schema (fail-fast)
  ↓
BuildSpec (validated dict[str, Any])
  ↓
WorkerFactory creates worker from BuildSpec
  ↓
Worker constructor re-validates using ITS OWN schema.py (defense in depth)
  ↓
Worker internals fully typed (self._params.fast_period)
```

**Benefits:**
- ✅ **Worker owns its validation contract** via schema.py (separation of concerns)
- ✅ ConfigTranslator validates once using worker's schema (fail-fast bootstrap)
- ✅ Worker constructor validates again using same schema (defense in depth)
- ✅ Worker internal code is fully typed (self._params.fast_period)
- ✅ BuildSpec remains simple dict[str, Any] (factory-agnostic)
- ✅ No generics complexity
- ✅ **UI can auto-generate forms from worker's schema.py** (dynamic configuration)
- ✅ Matches V2 architecture pattern (workers define schema, manifest references it)

**Trade-off:**
- ⚠️ Double validation (translation + constructor)
- ✅ BUT: Second validation is free (Pydantic caches on identical input)
- ✅ AND: Defense in depth prevents factory bypassing validation
- ✅ AND: Worker controls its own contract (plugin autonomy)

---

## V2 Architecture Pattern: Worker-Owned Schemas

**Key Principle:** Workers define and own their parameter validation contract via `schema.py`

### V2 Plugin Structure

```
plugins/ema_context/
├── manifest.yaml           # References schema.py
├── worker.py               # Business logic
├── schema.py               # ✅ WORKER OWNS VALIDATION!
├── context_schema.py       # (optional) UI visualization schema
└── test/
    └── test_worker.py
```

### V2 Manifest Format

```yaml
# plugins/ema_context/manifest.yaml
identification:
  name: "ema_context"
  type: "context_worker"
  version: "1.0.0"

schema:
  path: "schema.py"           # ✅ Path to schema file
  class: "EMAContextParams"   # ✅ Pydantic class name
```

### V2 Validation Flow

```
1. User creates strategy in UI
   ↓
2. UI loads worker's schema.py → generates form
   ↓
3. User fills form → params validated client-side (Pydantic)
   ↓
4. Strategy saved to YAML with validated params
   ↓
5. ConfigTranslator loads worker's schema via manifest
   ↓
6. ConfigTranslator re-validates params (server-side)
   ↓
7. BuildSpec created with validated dict
   ↓
8. Worker constructor re-validates (defense in depth)
```

**Benefits of V2 Pattern:**
- ✅ Worker autonomy: plugin controls its contract
- ✅ UI auto-generation: forms from schema.py
- ✅ Client + server validation: fail-fast at multiple levels
- ✅ Type safety: Pydantic throughout entire pipeline
- ✅ Separation of concerns: config structure ≠ worker params

**V3 Preserves This Pattern:**
We maintain the V2 worker-owned schema approach because it:
- Enables plugin autonomy (workers define contracts)
- Supports dynamic UI generation (schema.py → forms)
- Provides multi-level validation (UI → ConfigTranslator → Worker)
- Decouples YAML structure from worker implementation

---

## Open Questions

1. **Should BuildSpec store schema class reference?**
   - Pro: Enables re-validation without hardcoding
   - Con: Adds complexity to BuildSpec
   - Decision: DEFER - start simple (Option 1), add if needed

2. **Should workers receive BuildSpec or config_params dict?**
   - Option A: `worker.__init__(spec: WorkerBuildSpec)` - worker extracts params
   - Option B: `worker.__init__(config_params: dict)` - factory extracts params
   - Recommendation: **Option A** - worker owns schema validation

3. **How to handle plugin schema loading?**
   - Dynamic import from manifest.schema reference (path + class_name)?
   - Pre-register schemas in PluginRegistry at startup?
   - **V2 Pattern**: Manifest contains `schema.path` and `schema.class`, ConfigTranslator loads dynamically
   - Decision: DEFER to Plugin Architecture design phase, but likely **dynamic loading** (matches V2)

4. **Should ConfigTranslator validate ALL params or trust plugins?**
   - Trust plugins: Faster bootstrap, plugins own validation
   - Validate all: Slower bootstrap, fail-fast guarantee
   - Recommendation: **Validate all** - bootstrap is one-time cost

---

## Implementation Phases

### Phase 1: Basic Pipeline (Now)
1. ConfigLoader → Generic Pydantic models (`dict[str, Any]` params)
2. ConfigTranslator → Load plugin schema, validate, create BuildSpec
3. WorkerFactory → Pass BuildSpec to worker constructor
4. Worker constructor → Validate params internally using schema

### Phase 2: Schema Registry (Later)
1. PluginRegistry pre-loads all schemas at startup
2. ConfigTranslator uses registry instead of dynamic imports
3. Faster translation (no repeated imports)

### Phase 3: Type-Safe BuildSpecs (If Needed)
1. Evaluate if Option 2 (Generics) provides sufficient value
2. Migrate if type safety at factory level is critical
3. Requires refactor of WorkerFactory dispatch logic

---

## Related Design Decisions

- **Plugin Manifest Schema:** Must include `schema.path` and `schema.class` fields (V2 pattern)
- **Worker Schema Ownership:** Each worker plugin MUST define schema.py with Pydantic model
- **Worker Constructor Contract:** Must accept `WorkerBuildSpec` and re-validate using own schema
- **ConfigTranslator Responsibility:** Validate ALL params using worker schemas before BuildSpec creation
- **Factory Responsibility:** Trust BuildSpec params are pre-validated (no re-validation at factory level)
- **UI Form Generation:** Can dynamically generate configuration forms from worker's schema.py

---

## Next Steps

1. **Document in PLUGIN_ANATOMY.md**: Worker schema.py requirements + manifest reference format
2. **Design PluginRegistry**: Schema loading from manifest.schema reference (path + class)
3. **Update ConfigTranslator design**: Validation flow with worker-owned schemas
4. **Test with example plugin**: EMA worker with EMAContextParams schema (V2 pattern)
5. **UI Schema Integration**: Document how UI generates forms from worker's schema.py

---

## Related Documentation

- **IWorkerLifecycle Design:** [IWORKERLIFECYCLE_DESIGN.md](IWORKERLIFECYCLE_DESIGN.md) - Worker initialization
- **Architectural Shifts:** [ARCHITECTURAL_SHIFTS.md](../architecture/ARCHITECTURAL_SHIFTS.md) - BuildSpec rationale
- **Configuration Layers:** Future doc on 3-layer config system
- **Plugin Anatomy:** Future doc on worker plugin structure

---

**Last Updated:** 2025-10-29  
**Status:** OPEN QUESTION - Awaiting decision on Option 1 vs Option 2 vs Option 3  
**Recommendation:** Start with Option 1 + Worker Constructor Enhancement (simplest, proven pattern)
