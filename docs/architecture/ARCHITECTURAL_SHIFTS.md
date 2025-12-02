# Architectural Shifts - Critical V2 → V3 Changes

**⚠️ VERPLICHTE LEZING** - Deze drie verschuivingen zijn fundamenteel voor correct begrip van V3.

## Overview

De V3 architectuur heeft **drie fundamentele verschuivingen** ondergaan die het DNA van het systeem veranderen:

1. **Platgeslagen Orkestratie** - Geen Operators meer
2. **Point-in-Time Data Model** - Geen groeiende DataFrames meer  
3. **BuildSpec-Gedreven Bootstrap** - Geen runtime YAML parsing meer

## Verschuiving 1: Platgeslagen Orkestratie

### Was (V2 - ACHTERHAALD)
```
ExecutionEnvironment → Operator → Workers → Output
```

**Operators** (ContextOperator, SignalOperator) orkestreerden workers:
- ContextOperator verzamelde ContextWorker outputs
- SignalOperator aggregeerde SignalDetector outputs
- Operator-laag bevatte orchestratie-logica

### Nu (V3 - ACTUEEL)
```
ExecutionEnvironment → EventBus → EventAdapters → Workers → DispositionEnvelope → EventBus
```

**OPERATORS BESTAAN NIET MEER!**

**Impact:**
- ✅ EventAdapter is het **enige** orkestratieconcept
- ✅ Eén EventAdapter per component (worker of singleton)
- ✅ Workers bedraad via expliciete `strategy_wiring_map.yaml`
- ✅ UI genereert wiring op basis van `base_wiring.yaml` templates

**Waarom deze shift?**
- ❌ Operators waren een extra abstractielaag zonder toegevoegde waarde
- ❌ Operator-logica was moeilijk te testen (tight coupling)
- ✅ EventAdapter + wiring_map is flexibeler (runtime configureerbaar)
- ✅ Workers blijven bus-agnostic (retourneren DispositionEnvelope)

**Migratiepad:**
```python
# V2 - Operator aggregeerde outputs
class ContextOperator:
    def aggregate_context(self, worker_outputs):
        # Orchestration logic
        return aggregated_context

# V3 - Platform component doet aggregatie, workers blijven pure
class ContextAggregator:  # Platform component
    def aggregate(self, dtos):
        return AggregatedContextAssessment(...)

class ContextWorker:  # Pure businesslogic
    def process(self):
        self.strategy_cache.set_result_dto(self, MyDTO(...))
        return DispositionEnvelope(disposition="CONTINUE")
```

## Verschuiving 2: Point-in-Time Data Model

### Was (V2 - ACHTERHAALD)
```python
# enriched_df groeide tijdens worker chain
df = pd.DataFrame(ohlcv_data)
df = ema_worker.process(df)      # df['ema_20'] added
df = rsi_worker.process(df)      # df['rsi'] added
df = signal_worker.process(df)   # df['signal'] added
```

**Problemen:**
- ❌ Muterende state (moeilijk te debuggen)
- ❌ Geen duidelijke contracts (wat zit er in df?)
- ❌ Memory bloat (DataFrame groeit onbeperkt)
- ❌ Concurrency nightmare (workers muteren gedeelde state)

### Nu (V3 - ACTUEEL)
```python
# DTOs via IStrategyCache voor één tick/moment
class ContextWorker:
    def process(self):
        # 1. Get timestamp anchor
        anchor = self.strategy_cache.get_run_anchor()
        
        # 2. Get required input DTOs
        dtos = self.strategy_cache.get_required_dtos(self)
        
        # 3. Produce output DTO
        self.strategy_cache.set_result_dto(self, EMAOutputDTO(ema_20=...))
        
        return DispositionEnvelope(disposition="CONTINUE")
```

**Voordelen:**
- ✅ **Immutable**: Elke tick = nieuwe StrategyCache snapshot
- ✅ **Type-safe**: DTOs via Pydantic contracts
- ✅ **Explicit dependencies**: manifest.requires_dtos
- ✅ **Memory efficient**: StrategyCache cleared na run
- ✅ **Testable**: Mock IStrategyCache, inject DTOs

**Kernconcepten:**
- **RunAnchor**: Frozen timestamp voor point-in-time validation
- **StrategyCache**: `Dict[Type[BaseModel], BaseModel]` - één DTO per type
- **IStrategyCache**: Protocol voor DTO access/storage
- **StrategyCache**: Singleton, reconfigured per run

**Twee Communicatiepaden:**

1. **StrategyCache (Sync, Flow-Data)**
   - Via `IStrategyCache.set_result_dto()`
   - Voor worker-to-worker data
   - Plugin-specifieke DTOs
   - Levensduur: één tick/run

2. **EventBus (Async, Signals)**
   - Via `DispositionEnvelope(PUBLISH, event_payload=...)`
   - Voor platform signals
   - Systeem DTOs (Signal, Risk)
   - Persisteren via EventBus subscribers

**Zie:** [POINT_IN_TIME_MODEL.md](POINT_IN_TIME_MODEL.md) voor details.

## Verschuiving 3: BuildSpec-Gedreven Bootstrap

### Was (V2 - ACHTERHAALD)
```python
# ComponentBuilder las YAML en assembleerde direct
class ComponentBuilder:
    def build(self, yaml_config):
        worker = WorkerClass(yaml_config['params'])  # Runtime YAML parsing
        return worker
```

**Problemen:**
- ❌ Runtime YAML parsing (slow, error-prone)
- ❌ Validatie verspreid over codebase
- ❌ OperationService deed te veel (lifecycle + assembly)

### Nu (V3 - ACTUEEL)
```
YAML → ConfigTranslator → BuildSpecs → Factories → Components
```

**Workflow:**
1. **ConfigLoader**: Laadt YAML (PlatformConfig, OperationConfig, StrategyConfig)
2. **ConfigValidator**: Valideert alle drie lagen (fail-fast!)
3. **ConfigTranslator**: Vertaalt naar BuildSpecs (machine-instructies)
4. **Factories**: Bouwen components uit BuildSpecs
5. **OperationService**: Pure lifecycle manager

**BuildSpecs (Machine-Instructies):**
- `ConnectorSpec`
- `DataSourceSpec`
- `EnvironmentSpec`
- `WorkforceSpec`
- `WiringSpec` (vervangt operator_spec!)
- `PersistorSpec`

**Voordelen:**
- ✅ **Fail-fast**: Validatie tijdens bootstrap, niet runtime
- ✅ **Single Responsibility**: ConfigTranslator denkt, Factories bouwen, OperationService managed lifecycle
- ✅ **Testable**: Mock BuildSpecs voor factory tests
- ✅ **Performance**: Eenmalige validatie, geen runtime checks

**DependencyValidator:**
```python
# Bootstrap-time DTO dependency check
validator = DependencyValidator()
validator.validate_dto_dependencies(workforce_spec)
# Raises error if SignalDetector requires ContextDTO but no ContextWorker produces it
```

**EventChainValidator:**
```python
# Bootstrap-time event topology check
validator = EventChainValidator()
validator.validate_wiring(wiring_spec)
# Raises error if circular dependencies or missing event handlers
```

## Impact op Development Workflow

### V2 Workflow (ACHTERHAALD)
1. Write worker
2. Add to operator configuration
3. Hope wiring is correct (runtime discovery)
4. Debug runtime errors

### V3 Workflow (ACTUEEL)
1. Write worker + manifest.yaml (declares dependencies)
2. DependencyValidator checks at bootstrap
3. Wiring explicitly defined in strategy_wiring_map.yaml
4. EventChainValidator verifies topology
5. **Fail-fast**: Errors before runtime execution

## Migration Checklist

Als je V2 code ziet:

- [ ] **Operator-logica?** → Extract naar platform component (aggregator/coordinator)
- [ ] **enriched_df muteren?** → Replace met IStrategyCache + DTOs
- [ ] **Runtime YAML parsing?** → Move naar ConfigTranslator → BuildSpecs
- [ ] **Runtime validatie?** → Move naar bootstrap validators

## Anti-Patterns (V2 Leftovers)

❌ **DON'T:**
```python
# V2 pattern - Operator orchestratie
class MyOperator:
    def aggregate_workers(self, workers):
        ...

# V2 pattern - DataFrame mutatie
def process(self, df):
    df['my_col'] = calculate()
    return df

# V2 pattern - Runtime YAML
def process(self, config_path):
    config = yaml.load(open(config_path))
```

✅ **DO:**
```python
# V3 pattern - Platform component (no operator)
class MyAggregator:  # Singleton
    def aggregate(self, dtos):
        return AggregatedDTO(...)

# V3 pattern - DTO-based
def process(self):
    self.strategy_cache.set_result_dto(self, MyDTO(...))
    return DispositionEnvelope(disposition="CONTINUE")

# V3 pattern - BuildSpec-driven
factory.build_from_spec(workforce_spec)  # No YAML at runtime
```

## Zie Ook

- [Point-in-Time Model](POINT_IN_TIME_MODEL.md) - Verschuiving 2 in detail
- [Platform Components](PLATFORM_COMPONENTS.md) - StrategyCache, EventBus
- [Configuration Layers](CONFIGURATION_LAYERS.md) - Verschuiving 3 in detail
- [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md) - Verschuiving 1 in detail
