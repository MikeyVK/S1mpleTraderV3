# Backend Component Designs

Design documents for backend components organized by responsibility.

## Directory Structure

```
backend/
├── core/              # Core platform components
├── assembly/          # Bootstrap, factories, config translation
├── services/          # Domain services
├── dtos/              # DTO designs
└── utils/             # Utility components
```

## Core Components

### Platform Components
- [FlowInitiator Design](./core/flow_initiator_design.md) - Flow lifecycle initialization and cache management

### Planned
- FlowTerminator Design - Flow completion and cleanup
- StrategyCache Lifecycle - Cache management patterns

## Assembly Layer

Design documents for bootstrap, factory, and configuration translation components.

### Planned
- ConfigTranslator Design - YAML to BuildSpec translation
- WorkerFactory Design - Worker instantiation patterns
- EventWiringFactory Design - EventAdapter creation

## Domain Services

Design documents for domain services (Command/Query pattern).

### Planned
- FlowInitiatorConfigService - FlowInitiator configuration management

## Design Standards

All backend design documents should include:

1. **Component Overview**
   - Responsibilities
   - Architecture context
   - Related components

2. **Implementation Details**
   - Class structure
   - Key methods
   - Configuration format

3. **Integration Points**
   - Dependencies
   - Event interactions
   - BuildSpec structure

4. **Testing Strategy**
   - Unit test coverage
   - Integration scenarios
   - Mock strategies
