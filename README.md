# S1mpleTrader V3

**Contract-First, Event-Driven Trading Platform**

## Architecture Principles

1. **Plugin First** - All strategy logic encapsulated in standalone, testable plugins
2. **Separation of Concerns** - Strict layering: DTOs, Core, Assembly, Services
3. **Configuration-Driven** - Behavior controlled via YAML, code is execution engine
4. **Contract-Driven** - All data exchange validated through Pydantic schemas

## Fundamental Architectural Shifts

### 1. Flattened Orchestration (No Operators)
- Workers directly wired via explicit `wiring_map.yaml`
- EventAdapter per component for event-driven communication
- UI generates `strategy_wiring_map.yaml` from templates

### 2. Point-in-Time Data Model
- DTO-Centric with TickCache for single-tick data
- `ITradingContextProvider` for explicit data requests
- Two communication paths: TickCache (sync flow) + EventBus (async signals)

### 3. BuildSpec-Driven Bootstrap
- ConfigTranslator: YAML → BuildSpecs → Factories build components
- OperationService as pure lifecycle manager
- Fail-fast validation during bootstrap

## Project Structure

```
backend/
├── dtos/              # Data Transfer Objects (runtime data)
│   ├── shared/        # Foundation (DispositionEnvelope, BaseContext)
│   ├── strategy/      # Strategy Pipeline (Signals, Plans, Events)
│   ├── state/         # State Management (TickCache, Ledger)
│   └── build_specs/   # ConfigTranslator output
├── config/            # Configuration Schemas (YAML validation)
├── core/              # Core Components (Workers, Adapters, Interfaces)
├── assembly/          # Bootstrap & Factories
└── py.typed           # Type hints marker

tests/
├── unit/              # Unit tests (TDD approach)
└── integration/       # Integration tests

config/                # Configuration templates
docs/                  # Documentation
```

## Development Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy backend

# Linting
ruff check backend
```

## Testing Philosophy

**Test-Driven Development (TDD)**:
1. 🔴 **Red** - Write failing test
2. 🟢 **Green** - Minimal code to pass
3. 🔄 **Refactor** - Clean up with tests passing

## Key Concepts

### DispositionEnvelope
Workers return this to communicate intent to EventAdapter:
- `CONTINUE` - Flow continues, data in TickCache
- `PUBLISH` - Publish event with System DTO payload
- `STOP` - Terminate flow branch

### DTO vs Schema
- **DTO** - Runtime data containers (Pydantic BaseModel instances)
- **Schema** - Configuration validation (YAML parsers)

### Provider Interfaces
Platform "toolbox" injected into workers:
- `ITradingContextProvider` - TickCache access
- `ICandlestickProvider` - OHLCV data
- `IStateProvider` - Persistence
- `IJournalWriter` - Logging

## Documentation

See `docs/architecture.md` for complete architectural overview.

## License

[Add License Information]
