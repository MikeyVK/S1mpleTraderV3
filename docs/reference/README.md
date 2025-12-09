# Reference Documentation

## Overview

This directory contains **templates, examples, and reference implementations** for S1mpleTrader V3 components. Use these as copy-paste starting points for new DTOs, tests, and platform services.

## Quick Links

📋 **Templates:**
- [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md) - DTO boilerplate
- [DTO_TEST_TEMPLATE.md](testing/DTO_TEST_TEMPLATE.md) - Test boilerplate
- [Document Templates](templates/README.md) - ⭐ BASE/ARCHITECTURE/DESIGN/REFERENCE templates

🔧 **Maintenance:**
- [MAINTENANCE_SCRIPTS.md](MAINTENANCE_SCRIPTS.md) - PowerShell maintenance scripts
- [AI_DOC_PROMPTS.md](templates/AI_DOC_PROMPTS.md) - AI-assisted documentation prompts
- [MCP_TOOLS.md](../mcp/MCP_TOOLS.md) - ⭐ MCP server tools reference

📚 **Examples:**
- [signal.md](dtos/signal.md) - Signal DTO with causality
- [strategy_cache.md](platform/strategy_cache.md) - StrategyCache service

## Directory Structure

```
reference/
├── README.md                           # This file
├── MAINTENANCE_SCRIPTS.md              # ⭐ PowerShell maintenance scripts
├── dtos/
│   ├── STRATEGY_DTO_TEMPLATE.md       # Copy-paste DTO template
│   └── signal.md                       # Reference DTO implementation
├── testing/
│   └── DTO_TEST_TEMPLATE.md           # Copy-paste test template
├── platform/
│   └── strategy_cache.md              # Reference service implementation
└── templates/                          # ⭐ Document templates
    ├── README.md                       # Template usage guide
    ├── BASE_TEMPLATE.md
    ├── ARCHITECTURE_TEMPLATE.md
    ├── DESIGN_TEMPLATE.md
    ├── REFERENCE_TEMPLATE.md
    └── AI_DOC_PROMPTS.md               # AI-assisted doc prompts
```

## Templates

### 1. [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md)

**Purpose:** Copy-paste template for new Strategy DTOs

**Contents:**
- Complete file header template
- Import organization (3 groups)
- Field ordering rules (causality → ID → timestamp → core → optional)
- Common validators (ID, timestamp, UPPER_SNAKE_CASE)
- model_config with json_schema_extra
- Causality decision tree
- Frozen vs mutable guidelines
- Complete checklist

**When to use:**
- Creating new Signal, Risk DTOs
- Creating any Strategy DTO (signals, plans, directives)
- Need structure for DTO with causality tracking

**Related:**
- [signal.md](dtos/signal.md) - Filled-in example
- [CODE_STYLE.md](../coding_standards/CODE_STYLE.md) - Style guide
- [POINT_IN_TIME_MODEL.md](../architecture/POINT_IN_TIME_MODEL.md) - Architecture

### 2. [DTO_TEST_TEMPLATE.md](testing/DTO_TEST_TEMPLATE.md)

**Purpose:** Copy-paste template for comprehensive DTO tests

**Contents:**
- Test file header with pyright suppressions
- Test class organization (Creation, Validation, Immutability, etc.)
- 7 standard test suites (20-30 tests typical)
- Common validation patterns (string length, regex, Decimal ranges, Literal)
- getattr() workaround for Pydantic FieldInfo warnings
- TDD workflow integration (RED → GREEN → REFACTOR)
- Quality checklist

**When to use:**
- Writing tests FIRST (RED phase of TDD)
- Creating comprehensive test coverage
- Need structure for validator tests

**Related:**
- [TDD_WORKFLOW.md](../coding_standards/TDD_WORKFLOW.md) - TDD cycle
- [QUALITY_GATES.md](../coding_standards/QUALITY_GATES.md) - Quality gates

## Examples

### 1. [signal.md](dtos/signal.md)

**Type:** Strategy DTO with Causality

**Purpose:** Reference implementation for signal detection DTOs

**Highlights:**
- Exemplary file header
- Perfect field organization
- Military datetime ID validation
- Canonical UTC timestamp validator
- Advanced UPPER_SNAKE_CASE validation
- Best-practice json_schema_extra (3 examples)
- 22 comprehensive tests

**Quality:** 10/10 all gates, 100% test coverage

**Use as reference when:**
- Creating new Signal, Risk DTOs
- Need example of causality integration
- Implementing custom validators
- Writing json_schema_extra examples
- Organizing test suites

**Related:**
- [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md) - Template this fills
- Source: `backend/dtos/strategy/signal.py`
- Tests: `tests/unit/dtos/strategy/test_signal.py`

### 2. [strategy_cache.md](platform/strategy_cache.md)

**Type:** Platform Service (Singleton)

**Purpose:** Reference implementation for core services

**Highlights:**
- Singleton pattern (module-level)
- IStrategyCache protocol implementation
- Complete API reference (6 methods)
- Usage patterns (Worker access, Flow orchestration, PlanningWorker)
- Custom exception handling
- 20 comprehensive tests
- Design decisions documented

**Quality:** 10/10 all gates, 100% test coverage

**Use as reference when:**
- Implementing protocol-based services
- Creating singleton services
- Need example of state management
- Writing service documentation
- Understanding StrategyCache usage

**Related:**
- [POINT_IN_TIME_MODEL.md](../architecture/POINT_IN_TIME_MODEL.md) - IStrategyCache protocol
- Source: `backend/core/strategy_cache.py`
- Tests: `tests/unit/core/test_strategy_cache.py`

## Reference Status Matrix

Track which components have reference documentation:

| Component | Template | Example | Tests | Status |
|-----------|----------|---------|-------|--------|
| **Strategy DTOs** |
| Signal | ✅ [DTO Template](dtos/STRATEGY_DTO_TEMPLATE.md) | ✅ [Example](dtos/signal.md) | ✅ [Test Template](testing/DTO_TEST_TEMPLATE.md) | Complete |
| Risk | ✅ [DTO Template](dtos/STRATEGY_DTO_TEMPLATE.md) | 🚧 Pending | ✅ [Test Template](testing/DTO_TEST_TEMPLATE.md) | Partial |
| StrategyDirective | ✅ [DTO Template](dtos/STRATEGY_DTO_TEMPLATE.md) | 🚧 Pending | ✅ [Test Template](testing/DTO_TEST_TEMPLATE.md) | Partial |
| EntryPlan | ✅ [DTO Template](dtos/STRATEGY_DTO_TEMPLATE.md) | 🚧 Pending | ✅ [Test Template](testing/DTO_TEST_TEMPLATE.md) | Partial |
| SizePlan | ✅ [DTO Template](dtos/STRATEGY_DTO_TEMPLATE.md) | 🚧 Pending | ✅ [Test Template](testing/DTO_TEST_TEMPLATE.md) | Partial |
| ExitPlan | ✅ [DTO Template](dtos/STRATEGY_DTO_TEMPLATE.md) | 🚧 Pending | ✅ [Test Template](testing/DTO_TEST_TEMPLATE.md) | Partial |
| **Platform Services** |
| StrategyCache | N/A | ✅ [Example](platform/strategy_cache.md) | N/A | Complete |
| EventBus | ❌ Missing | 🚧 Future | ❌ Missing | Not Started |
| TickCacheManager | ❌ Missing | 🚧 Future | ❌ Missing | Not Started |
| **Workers** |
| BaseWorker | ❌ Missing | 🚧 Future | ❌ Missing | Not Started |
| SignalDetector | ❌ Missing | 🚧 Future | ❌ Missing | Not Started |

**Legend:**
- ✅ Complete - Template/example available
- 🚧 Pending - Implementation exists, documentation needed
- ❌ Missing - Template/example not yet created

## Common Workflows

### Creating a New Strategy DTO

1. **Read template:** [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md)
2. **Check example:** [signal.md](dtos/signal.md)
3. **RED Phase:** Copy [DTO_TEST_TEMPLATE.md](testing/DTO_TEST_TEMPLATE.md), write failing tests
4. **GREEN Phase:** Copy [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md), implement DTO
5. **REFACTOR Phase:** Compare with [signal.md](dtos/signal.md) for quality
6. **Verify:** Run quality gates (see [QUALITY_GATES.md](../coding_standards/QUALITY_GATES.md))

### Understanding Platform Services

1. **Read example:** [strategy_cache.md](platform/strategy_cache.md)
2. **Check architecture:** [POINT_IN_TIME_MODEL.md](../architecture/POINT_IN_TIME_MODEL.md)
3. **Study patterns:** Usage patterns section in example
4. **Review tests:** Check test coverage strategy
5. **Apply patterns:** Use same structure for new services

### Writing Comprehensive Tests

1. **Copy template:** [DTO_TEST_TEMPLATE.md](testing/DTO_TEST_TEMPLATE.md)
2. **Check example:** [signal.md](dtos/signal.md) → Test Structure section
3. **Use patterns:** Common validation patterns in template
4. **Apply workarounds:** getattr() for Pydantic FieldInfo
5. **Verify coverage:** 20-30 tests typical for DTOs

## Update Guidelines

**When to add new template:**
- New component type not covered (e.g., Worker template)
- Repeating pattern across multiple files (DRY principle)
- Complex boilerplate that's error-prone

**When to add new example:**
- Implementation has unique patterns worth documenting
- Component is critical to architecture (like StrategyCache)
- Multiple developers will need to understand it

**When to update existing:**
- Better patterns discovered
- Quality improvements made
- Templates missing critical sections
- Examples outdated after refactoring

## Related Documentation

- **Architecture:** [../architecture/README.md](../architecture/README.md) - System design
- **Coding Standards:** [../coding_standards/README.md](../coding_standards/README.md) - Style and quality
- **Implementation:** [../implementation/IMPLEMENTATION_STATUS.md](../implementation/IMPLEMENTATION_STATUS.md) - Current progress

## Support

**Need help with templates?**
- Check example implementations first
- Look for similar patterns in existing code
- Consult coding standards for specific rules
- Update template if clarification needed

**Found template improvements?**
- Create `docs/update-reference` branch
- Update template/example
- Add entry to status matrix if new component
- Submit with `docs:` commit prefix
