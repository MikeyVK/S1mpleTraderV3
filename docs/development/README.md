# Development Documentation

This directory contains detailed design documents for S1mpleTraderV3 components organized by architectural layer.

## Directory Structure

```
development/
├── backend/           # Backend component designs
│   ├── core/         # Core platform components
│   ├── assembly/     # Bootstrap, factories, config translation
│   ├── services/     # Domain services
│   └── dtos/         # DTO designs
│
├── frontend/         # Frontend component designs
│   └── strategy_builder/  # Strategy Builder UI
│
├── plugins/          # Plugin designs
│   ├── workers/      # Plugin worker designs
│   └── strategies/   # Strategy plugin designs
│
├── integration/      # Cross-layer designs
│
└── #Archief/        # Archived design documents (V2)
```

## Document Types

### Component Designs
Individual component specifications with:
- Problem statement
- Architecture overview
- Implementation details
- Configuration examples
- Testing strategy

### Integration Designs
Cross-component interactions:
- Event flows
- Config translation flows
- End-to-end scenarios

## Active Design Documents

### Backend - Core
- [FlowInitiator Design](./backend/core/flow_initiator_design.md) - Flow lifecycle initialization

### Archived (V2)
See [#Archief/](./development/#Archief/) for V2 design documents.

## Design Principles

All design documents follow these principles:

1. **Problem First** - Start with problem statement
2. **Architecture Overview** - High-level design before details
3. **Code Examples** - Concrete implementation examples
4. **Testing Strategy** - Unit + integration test approach
5. **Related Docs** - Links to architecture and reference docs

## Contributing

When creating new design documents:

1. Choose correct layer directory (backend/frontend/plugins)
2. Use descriptive filename: `{component}_design.md`
3. Follow template structure (see existing docs)
4. Update this README with new document link
5. Link from architecture docs where relevant
