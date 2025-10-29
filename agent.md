# S1mpleTrader V3 - AI Assistant Instructions

## Your Role

Je bent een AI-assistent voor **S1mpleTrader V3** development. Je helpt met:
- Implementatie van nieuwe components (DTOs, Workers, Platform components)
- Code quality verbetering (TDD, refactoring, testing)
- Architectuur adherence (review designs tegen principes)

## Critical Reading Order (VERPLICHT!)

**Voordat je IETS implementeert:**

1. ⭐ **START**: [Architecture - Core Principles](docs/architecture/CORE_PRINCIPLES.md)
2. ⭐ **CRITICAL**: [Architecture - Architectural Shifts](docs/architecture/ARCHITECTURAL_SHIFTS.md)
3. ⭐ **DATA MODEL**: [Architecture - Point-in-Time Model](docs/architecture/POINT_IN_TIME_MODEL.md)
4. 📋 **WORKFLOW**: [Coding Standards - TDD Workflow](docs/coding_standards/TDD_WORKFLOW.md)
5. 📊 **STATUS**: [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md)

**Voor specifieke taken:**
- **Workers?** → [Architecture - Worker Taxonomy](docs/architecture/WORKER_TAXONOMY.md)
- **DTOs?** → [Reference - DTO Template](docs/reference/dtos/STRATEGY_DTO_TEMPLATE.md)
- **Quality?** → [Coding Standards - Quality Gates](docs/coding_standards/QUALITY_GATES.md)
- **Git?** → [Coding Standards - Git Workflow](docs/coding_standards/GIT_WORKFLOW.md)

## Quick Navigation

### Documentation Structure
```
docs/
├── architecture/          # System design, patterns, principles
│   ├── README.md         # Architecture index (start here!)
│   ├── CORE_PRINCIPLES.md
│   ├── ARCHITECTURAL_SHIFTS.md    # CRITICAL!
│   └── POINT_IN_TIME_MODEL.md     # CRITICAL!
│
├── coding_standards/      # TDD, quality gates, code style
│   ├── TDD_WORKFLOW.md
│   ├── QUALITY_GATES.md
│   ├── CODE_STYLE.md
│   └── GIT_WORKFLOW.md
│
├── implementation/        # Status tracking, quality metrics
│   └── IMPLEMENTATION_STATUS.md
│
├── reference/             # Templates + examples
│   ├── README.md         # Reference index
│   ├── dtos/             # DTO templates + examples
│   ├── workers/          # Worker templates + examples
│   ├── platform/         # Platform component references
│   └── testing/          # Test templates
│
└── TODO.md               # Project roadmap
```

### Keeping Documentation Organized

**Read this!** [Documentation Maintenance Guide](docs/DOCUMENTATION_MAINTENANCE.md)

- 📏 Max 300 lines per document (prevents bloat)
- 🔗 Single source of truth (link, don't duplicate)
- 📋 Index-driven navigation (every directory needs README)
- 🤖 AI-assisted workflows (iterative documentation)
- 🗓️ Maintenance schedules (weekly/monthly/quarterly)

## The 4 Core Principles (Never Violate!)

1. **Plugin First** - All strategy logic in plugins, not platform
2. **Separation of Concerns** - Workers/Environment/Factories/EventBus strictly separated
3. **Config-Driven** - Behavior controlled by YAML, not hardcoded
4. **Contract-Driven** - All data exchange via Pydantic DTOs

**Details:** [Core Principles](docs/architecture/CORE_PRINCIPLES.md)

## The 3 Critical Shifts (Must Understand!)

1. **No Operators** - Workers bedraad via EventAdapters + wiring_map.yaml
2. **No Growing DataFrames** - Point-in-Time DTOs via IStrategyCache
3. **No Runtime YAML** - BuildSpec-driven bootstrap with fail-fast validation

**Details:** [Architectural Shifts](docs/architecture/ARCHITECTURAL_SHIFTS.md)

## Standard Implementation Workflow

### Phase 0: Design (VERPLICHT!)
```
1. Read relevant architecture docs
2. Design component (architecturale positie, verantwoordelijkheden)
3. Create/update design doc if complex (docs/development/)
4. Get user approval BEFORE coding
```

### Phase 1: TDD Cycle
```
1. Feature branch: git checkout -b feature/my-component
2. RED: Write failing tests (20+ for DTOs)
3. GREEN: Minimal implementation
4. REFACTOR: Quality gates (Pylint 10/10, tests 100%)
5. Update: IMPLEMENTATION_STATUS.md
6. Merge: git checkout main && git merge feature/my-component
```

**Details:** [TDD Workflow](docs/coding_standards/TDD_WORKFLOW.md)

### Phase 2: Quality Gates (Verplicht!)
```powershell
# Trailing whitespace
python -m pylint <file> --disable=all --enable=trailing-whitespace,superfluous-parens

# Imports top-level
python -m pylint <file> --disable=all --enable=import-outside-toplevel

# Line length (<100 chars)
python -m pylint <file> --disable=all --enable=line-too-long --max-line-length=100

# Tests passing
pytest <test_file> -v

# All gates must be 10.00/10 + 100% tests passing
```

**Details:** [Quality Gates](docs/coding_standards/QUALITY_GATES.md)

## Key Anti-Patterns (DON'T!)

❌ **NO Operators** - Use EventAdapters + wiring_map
❌ **NO enriched_df** - Use IStrategyCache + DTOs
❌ **NO runtime YAML** - Use BuildSpecs
❌ **NO hardcoded dependencies** - Use dependency injection
❌ **NO dict-based data** - Use Pydantic DTOs
❌ **NO trailing whitespace** - Auto-fix: `(Get-Content <file>) | ForEach-Object { $_.TrimEnd() } | Set-Content <file>`
❌ **NO imports in functions** - Always top-level
❌ **NO code without tests** - TDD is mandatory

## Quick Reference Card

### Data Flow Paths
- **Sync (worker→worker)**: TickCache via `IStrategyCache.set_result_dto()`
- **Async (worker→platform)**: EventBus via `DispositionEnvelope(PUBLISH)`

### Worker Output Types
- **CONTINUE**: Trigger next worker(s), data in TickCache
- **PUBLISH**: Publish event to EventBus, custom payload
- **STOP**: End flow, trigger cleanup

### DTO Types
- **Plugin DTOs**: Worker-specific, shared via dto_reg/, in TickCache
- **System DTOs**: Platform-defined (OpportunitySignal, ThreatSignal, etc.), on EventBus

### Configuration Hierarchy
```
PlatformConfig (global, static)
    ↓
OperationConfig (per workspace)
    ↓
StrategyConfig (per strategy, JIT)
```

## Implementation Checklists

### New DTO
```
1. Read: docs/reference/dtos/STRATEGY_DTO_TEMPLATE.md
2. Copy boilerplate
3. TDD: 20+ tests (creation, validation, edge cases)
4. Quality gates: All 10/10
5. Update: IMPLEMENTATION_STATUS.md
```

### New Worker
```
1. Read: docs/architecture/WORKER_TAXONOMY.md
2. Read: docs/reference/workers/<TYPE>_WORKER_TEMPLATE.md
3. Create manifest.yaml (declare dependencies)
4. TDD: Implementation + tests
5. Quality gates: All 10/10
6. Update: IMPLEMENTATION_STATUS.md
```

### New Platform Component
```
1. Read: docs/architecture/PLATFORM_COMPONENTS.md
2. Design: Interface protocol first
3. TDD: Protocol tests, then implementation
4. Quality gates: All 10/10
5. Update: IMPLEMENTATION_STATUS.md
6. Document: docs/reference/platform/<component>.md
```

## Git Workflow (Altijd!)

```powershell
# 1. Feature branch
git checkout -b feature/my-feature

# 2. TDD commits
git commit -m "test: add failing tests for MyFeature (RED)"
git commit -m "feat: implement MyFeature (GREEN)"
git commit -m "refactor: improve code quality (REFACTOR)"

# 3. Quality verification
git commit -m "docs: update IMPLEMENTATION_STATUS.md"

# 4. Merge
git checkout main
git merge feature/my-feature
git push origin main
git branch -d feature/my-feature
```

**Details:** [Git Workflow](docs/coding_standards/GIT_WORKFLOW.md)

## When You're Stuck

1. **Architecture unclear?** → Read [Architecture README](docs/architecture/README.md)
2. **Don't know where to start?** → Check [TODO.md](docs/TODO.md)
3. **Need example?** → Browse [Reference](docs/reference/README.md)
4. **Quality gates failing?** → Follow [Quality Gates](docs/coding_standards/QUALITY_GATES.md)
5. **Tests failing?** → Check [Test Templates](docs/reference/testing/)

## Critical Success Factors

✅ **Read Architectural Shifts FIRST** - Non-negotiable
✅ **Follow TDD** - RED → GREEN → REFACTOR
✅ **All quality gates 10/10** - No exceptions
✅ **Feature branches** - Never commit directly to main
✅ **Update status docs** - IMPLEMENTATION_STATUS.md na elke feature

## Commit Message Conventions

- `feat:` - New feature
- `fix:` - Bug fix
- `test:` - Tests only (RED phase)
- `refactor:` - Code improvements (REFACTOR phase)
- `docs:` - Documentation
- `chore:` - Build/tooling

**Details:** [Git Workflow](docs/coding_standards/GIT_WORKFLOW.md)

## Your Checklist Before ANY Implementation

- [ ] Gelezen: CORE_PRINCIPLES.md
- [ ] Gelezen: ARCHITECTURAL_SHIFTS.md (3 shifts duidelijk?)
- [ ] Gelezen: POINT_IN_TIME_MODEL.md (IStrategyCache begrip?)
- [ ] Gelezen: Relevante worker/DTO/platform doc
- [ ] Ontwerp gemaakt (architecturale positie, verantwoordelijkheden)
- [ ] Template gevonden (docs/reference/)
- [ ] Feature branch aangemaakt
- [ ] TDD workflow klaar (RED → GREEN → REFACTOR)

**Als één van deze "nee" is, STOP en lees eerst de docs.**

---

**Documentation maintained by:** Development Team
**Last major update:** 2025-10-28
**Version:** V3
**For detailed docs:** See `docs/` folders above
