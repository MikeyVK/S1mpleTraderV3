# Layered Architecture

**Status:** Architecture Foundation  
**Last Updated:** 2025-10-29

---

## Overview

S1mpleTraderV3 follows a **strict layered architecture** with unidirectional dependency flow. Each layer has distinct responsibilities and communicates through well-defined interfaces.

**Key Principles:**
- **Unidirectional Dependencies**: Frontend → Service → Backend (never upward)
- **Separation of Concerns**: Clear boundaries between presentation, orchestration, and engine
- **BuildSpec-Driven Bootstrap**: Configuration translated to BuildSpecs before component assembly
- **Fail-Fast Validation**: All validation during bootstrap, not runtime

---

## The Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND LAYER                                              │
│  (Presentation & User Interaction)                           │
│  - CLI, Web API, Web UI                                      │
│  - User commands, visualization, monitoring                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│  SERVICE LAYER                                               │
│  (Orchestration & Business Workflows)                        │
│  - OperationService (lifecycle manager)                      │
│  - OptimizationService, ParallelRunService                   │
│  - ConfigLoader, ConfigValidator, ConfigTranslator           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│  BACKEND LAYER                                               │
│  (Engine & Core Logic)                                       │
│  - Factories (BuildSpec → Components)                        │
│  - Workers, Singletons, EventBus                             │
│  - Platform components (StrategyCache, EventBus, etc.)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. Frontend Layer

**Purpose:** User interaction and visualization

**Components:**
- **CLI** - Command-line interface for operations
- **Web API** - REST/GraphQL endpoints for external integrations
- **Web UI** - Browser-based dashboard and configuration

**Responsibilities:**
- Accept user commands
- Display strategy performance
- Provide configuration interfaces
- Monitor system health

**Communication:**
- **Downward:** Calls OperationService methods
- **Upward:** Receives events from EventBus (read-only subscriptions)

**Key Principle:** Frontend NEVER accesses Backend directly

---

### 2. Service Layer

**Purpose:** Orchestration and business workflows

**Components:**

#### OperationService (Lifecycle Manager)
- **Role:** Manages strategy lifecycle (start, stop, restart)
- **Responsibilities:**
  - Load and validate configurations (3-layer hierarchy)
  - Trigger ConfigTranslator for BuildSpec generation
  - Coordinate Factory chain execution
  - Register strategy instances
  - Handle shutdown and cleanup

#### ConfigLoader
- **Role:** Load configuration files from disk/database
- **Responsibilities:**
  - Load PlatformConfig (once at startup)
  - Load OperationConfig (per operation)
  - Load StrategyConfig (per strategy, just-in-time)
  - Merge configurations respecting hierarchy

#### ConfigValidator
- **Role:** Validate configurations against schemas
- **Responsibilities:**
  - Schema validation (Pydantic models)
  - Cross-layer dependency validation
  - Plugin manifest validation
  - Fail-fast on invalid configuration

#### ConfigTranslator
- **Role:** Translate YAML → BuildSpecs
- **Responsibilities:**
  - Generate `connector_spec` from connector YAML
  - Generate `environment_spec` from environment YAML
  - Generate `workforce_spec` from workforce YAML
  - Generate `wiring_spec` from wiring YAML
  - **KEY:** ConfigTranslator is the ONLY "thinker" - Factories are pure builders

**Communication:**
- **Downward:** Calls Factories to build components
- **Upward:** Exposes API to Frontend
- **Horizontal:** Orchestrates multiple strategies in parallel

---

### 3. Backend Layer

**Purpose:** Trading engine and core logic

**Components:**

#### Factories (BuildSpec → Components)
- **ConnectorFactory** - Builds data connectors (CEX, DEX, Backtest)
- **DataSourceFactory** - Builds data sources (OHLCV providers)
- **EnvironmentFactory** - Builds execution environments
- **WorkerFactory** - Builds workers from plugins
- **EventWiringFactory** - Wires EventAdapters to EventBus

**Key Principle:** Factories are PURE BUILDERS - no decision logic, only assembly

#### Platform Components (Singletons)
- **StrategyCache** - Point-in-time DTO container (per strategy)
- **EventBus** - N-to-N event broadcast
- **TickCacheManager** - Tick flow initiator
- **PluginRegistry** - Plugin enrollment and metadata

#### Workers (Plugin Logic)
- Context, Opportunity, Threat, Planning, StrategyPlanner workers
- Loaded from plugins via WorkerFactory
- Bus-agnostic (communicate via EventAdapters)

**Communication:**
- **Upward:** Publishes events to EventBus (Service subscribes)
- **Horizontal:** Workers communicate via TickCache and EventBus

---

## Bootstrap Workflow (BuildSpec-Driven)

### Complete Bootstrap Sequence

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER START COMMAND                                        │
│    $ python -m simpletrader start --operation my_operation   │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 2. OperationService.start_all_strategies()                   │
│    For each strategy_link in operation.yaml:                 │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 3. ConfigLoader                                              │
│    a. Load PlatformConfig (platform.yaml)                    │
│    b. Load OperationConfig (operation.yaml + refs)           │
│    c. Load StrategyConfig (strategy_blueprint.yaml)          │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 4. ConfigValidator                                           │
│    a. Validate PlatformConfig schema                         │
│    b. Validate OperationConfig schema                        │
│    c. Validate StrategyConfig schema                         │
│    d. Validate cross-layer dependencies                      │
│    e. FAIL-FAST if any errors                                │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 5. ConfigTranslator (THE "THINKER")                          │
│    Translate YAML → BuildSpecs:                              │
│    a. connector_spec      (data connectors)                  │
│    b. data_source_spec    (OHLCV providers)                  │
│    c. environment_spec    (execution environment)            │
│    d. workforce_spec      (worker instances)                 │
│    e. wiring_spec         (EventAdapter wiring)              │
│    f. persistor_spec      (state persistence)                │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 6. FACTORY CHAIN (IN ORDER)                                  │
│    a. ConnectorFactory.build_from_spec(connector_spec)       │
│    b. DataSourceFactory.build_from_spec(data_source_spec)    │
│    c. EnvironmentFactory.build_from_spec(environment_spec)   │
│    d. PersistorFactory.build_from_spec(persistor_spec)       │
│    e. WorkerFactory.build_from_spec(workforce_spec)          │
│    f. EventWiringFactory.wire_all_from_spec(wiring_spec) ←!  │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 7. Environment.start()                                       │
│    - Initialize data feeds                                   │
│    - Start tick flow                                         │
│    - Begin event processing                                  │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌──────────────────────────┴──────────────────────────────────┐
│ 8. OperationService.register_strategy_instance()             │
│    - Track running strategy                                  │
│    - Enable monitoring/control                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Bootstrap Concepts

#### ConfigTranslator is the "Thinker"

**Responsibility:** All decision logic for component construction

**What it does:**
- Interprets configuration intent
- Resolves dependencies
- Generates complete BuildSpecs
- Determines component wiring

**What it does NOT do:**
- Instantiate components (Factories do this)
- Validate configuration (ConfigValidator does this)
- Manage lifecycle (OperationService does this)

#### Factories are "Pure Builders"

**Responsibility:** Assemble components from BuildSpecs

**What they do:**
- Instantiate classes with provided parameters
- Inject dependencies as specified
- Return ready-to-use components

**What they do NOT do:**
- Make decisions about configuration
- Validate BuildSpec content
- Interpret user intent

---

## Architectural Evolution: Flattened Orchestration

### Old Architecture (V2 - Deprecated)

```
ExecutionEnvironment
    ↓
Operator (ContextOperator, OpportunityOperator, etc.)
    ↓
Workers (grouped by operator)
    ↓
Output
```

**Problem:** Operators created unnecessary abstraction layer, hardcoded groupings

---

### New Architecture (V3 - Current)

```
ExecutionEnvironment
    ↓
EventBus (N-to-N broadcast)
    ↓
EventAdapters (1 per component)
    ↓
Workers (bus-agnostic)
    ↓
DispositionEnvelope
    ↓
EventAdapters (publish to EventBus)
    ↓
EventBus
```

**Improvements:**
- **No Operators**: Direct wiring via EventAdapters
- **Flexibility**: Workers wired via `wiring_map.yaml` (not hardcoded)
- **Bus-Agnostic Workers**: Workers don't know about EventBus
- **One Adapter per Component**: Clear ownership and isolation

**Key Component:** EventWiringFactory creates and wires all EventAdapters during bootstrap

---

## Configuration Layers (Quick Reference)

See [Configuration Layers](CONFIGURATION_LAYERS.md) for details.

### 1. PlatformConfig
- **Scope:** Global, static
- **Loaded:** Once at OperationService start
- **Contains:** Logging, paths, locale
- **Does NOT contain:** Connectors, environments, schedules

### 2. OperationConfig
- **Scope:** Per workspace/campaign
- **Loaded:** Per operation
- **Contains:** Connectors, data sources, environments, schedule, strategy links
- **File:** `operation.yaml` + referenced files

### 3. StrategyConfig
- **Scope:** Per strategy
- **Loaded:** Just-in-time per strategy_link
- **Contains:** Workforce (workers), strategy-specific wiring
- **File:** `strategy_blueprint.yaml`

---

## Related Documentation

- **[Configuration Layers](CONFIGURATION_LAYERS.md)** - Detailed 3-layer config system
- **[Architectural Shifts](ARCHITECTURAL_SHIFTS.md)** - Critical V2 → V3 changes
- **[Event-Driven Wiring](EVENT_DRIVEN_WIRING.md)** - EventAdapter and wiring_map.yaml
- **[Platform Components](PLATFORM_COMPONENTS.md)** - Core singletons

---

**Last Updated:** 2025-10-29
