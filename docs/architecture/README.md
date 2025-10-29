# Architecture Documentation - Navigation

**S1mpleTrader V3** - Plugin-First, Event-Driven Trading Platform

## Quick Start

**New to the project?** Read in this order:
1. [Core Principles](CORE_PRINCIPLES.md) - Vision + 4 fundamental principles
2. [Architectural Shifts](ARCHITECTURAL_SHIFTS.md) - **CRITICAL**: 3 major changes from V2
3. [Point-in-Time Model](POINT_IN_TIME_MODEL.md) - DTO-Centric data flow
4. [Worker Taxonomy](WORKER_TAXONOMY.md) - 5 worker categories

**Implementing a feature?** Jump to:
- **Workers**: [Worker Taxonomy](WORKER_TAXONOMY.md) → [Plugin Anatomy](PLUGIN_ANATOMY.md)
- **Platform**: [Platform Components](PLATFORM_COMPONENTS.md)
- **Configuration**: [Configuration Layers](CONFIGURATION_LAYERS.md)

## Architecture Overview

### Foundation Concepts

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [Core Principles](CORE_PRINCIPLES.md) | Vision + Design Philosophy | Plugin First, Separation of Concerns, Config-Driven, Contract-Driven |
| [Architectural Shifts](ARCHITECTURAL_SHIFTS.md) | **CRITICAL READING** | Platgeslagen Orkestratie, Point-in-Time Model, BuildSpec Bootstrap |
| [Layered Architecture](LAYERED_ARCHITECTURE.md) | System Layers | Frontend → Service → Backend, Dependency flow |

### Configuration & Bootstrap

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [Configuration Layers](CONFIGURATION_LAYERS.md) | 3-Layer Config System | PlatformConfig, OperationConfig, StrategyConfig |
| [Layered Architecture](LAYERED_ARCHITECTURE.md#bootstrap-workflow) | Bootstrap Process | ConfigLoader → Validator → Translator → Factories |

### Data Model & Communication

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [Point-in-Time Model](POINT_IN_TIME_MODEL.md) | **CORE DATA MODEL** | TickCache, IStrategyCache, RunAnchor, DTO flow |
| [Data Flow](DATA_FLOW.md) | Worker Communication | DispositionEnvelope, CONTINUE/PUBLISH/STOP |
| [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md) | Event Architecture | EventBus, EventAdapter, wiring_map.yaml |

### Workers & Plugins

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [Worker Taxonomy](WORKER_TAXONOMY.md) | 5 Worker Categories | Context, Opportunity, Threat, Planning, StrategyPlanner |
| [Plugin Anatomy](PLUGIN_ANATOMY.md) | Plugin Structure | manifest.yaml, worker.py, schema.py, DTOs |

### Platform Infrastructure

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [Platform Components](PLATFORM_COMPONENTS.md) | Core Singletons | StrategyCache, EventBus, TickCacheManager, PluginRegistry |

## Critical Path for New Developers

### Phase 1: Understanding the Model
1. ✅ Read [Architectural Shifts](ARCHITECTURAL_SHIFTS.md) - **NON-NEGOTIABLE**
2. ✅ Read [Point-in-Time Model](POINT_IN_TIME_MODEL.md)
3. ✅ Skim [Worker Taxonomy](WORKER_TAXONOMY.md)

### Phase 2: Implementation Patterns
1. ✅ Study [Plugin Anatomy](PLUGIN_ANATOMY.md)
2. ✅ Review [Data Flow](DATA_FLOW.md)
3. ✅ Check [Platform Components](PLATFORM_COMPONENTS.md)

### Phase 3: Deep Dive (as needed)
- Configuration complex? → [Configuration Layers](CONFIGURATION_LAYERS.md)
- Event wiring issues? → [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md)
- Bootstrap debugging? → [Layered Architecture](LAYERED_ARCHITECTURE.md#bootstrap-workflow)

## Architecture Decisions

**Key Design Choices:**
- **No Operators**: Workers bedraad via EventAdapters (zie [Architectural Shifts](ARCHITECTURAL_SHIFTS.md#verschuiving-1))
- **No Growing DataFrames**: Point-in-Time DTOs only (zie [Point-in-Time Model](POINT_IN_TIME_MODEL.md))
- **Fail-Fast Bootstrap**: Validation during assembly, not runtime (zie [Layered Architecture](LAYERED_ARCHITECTURE.md#bootstrap-workflow))

## Quick Reference

### Data Flow Paths
- **Sync Flow** (worker → worker): TickCache via `IStrategyCache.set_result_dto()`
- **Async Signals** (worker → platform): EventBus via `DispositionEnvelope(PUBLISH)`

### Worker Output Types
- **CONTINUE**: Trigger next worker(s) in chain
- **PUBLISH**: Publish custom event + payload to EventBus
- **STOP**: End flow, trigger cleanup

### Configuration Hierarchy
```
PlatformConfig (global, static)
    ↓
OperationConfig (per workspace/campaign)
    ↓
StrategyConfig (per strategy, JIT loaded)
```

## Related Documentation

- **Implementation Status**: [../implementation/IMPLEMENTATION_STATUS.md](../implementation/IMPLEMENTATION_STATUS.md)
- **Coding Standards**: [../coding_standards/](../coding_standards/)
- **Reference Examples**: [../reference/](../reference/)
- **Project Roadmap**: [../TODO.md](../TODO.md)

---

**Last Updated:** 2025-10-29
**Maintained By:** Development Team
**For Questions:** See relevant detailed document or TODO.md for current work
