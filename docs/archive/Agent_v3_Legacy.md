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
3. ⭐ **QUANT LEAP**: [Architecture - Objective Data Philosophy](docs/architecture/OBJECTIVE_DATA_PHILOSOPHY.md)
4. ⭐ **DATA MODEL**: [Architecture - Point-in-Time Model](docs/architecture/POINT_IN_TIME_MODEL.md)
5. 📋 **WORKFLOW**: [Coding Standards - TDD Workflow](docs/coding_standards/TDD_WORKFLOW.md)
6. 📊 **STATUS**: [Implementation Status](docs/implementation/IMPLEMENTATION_STATUS.md)

**Voor specifieke taken:**
- **Workers?** → [Architecture - Worker Taxonomy](docs/architecture/WORKER_TAXONOMY.md)
- **DTOs?** → [Reference - DTO Template](docs/reference/dtos/STRATEGY_DTO_TEMPLATE.md)
- **Quality?** → [Coding Standards - Quality Gates](docs/coding_standards/QUALITY_GATES.md)
- **Git?** → [Coding Standards - Git Workflow](docs/coding_standards/GIT_WORKFLOW.md)
- **New docs?** → [Document Templates](docs/reference/templates/README.md)
- **Doc gaps?** → [Documentation TODO](docs/TODO_DOCUMENTATION.md)

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
│   ├── templates/        # ⭐ Document templates
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

## The 5 Core Principles (Never Violate!)

1. **Plugin First** - All strategy logic in plugins, not platform
2. **Separation of Concerns** - Workers/Environment/Factories/EventBus strictly separated
3. **Config-Driven** - Behavior controlled by YAML, not hardcoded
4. **Contract-Driven** - All data exchange via Pydantic DTOs
5. **Objective Data** - ContextWorkers produce facts, consumers interpret

**Details:** [Core Principles](docs/architecture/CORE_PRINCIPLES.md) + [Objective Data Philosophy](docs/architecture/OBJECTIVE_DATA_PHILOSOPHY.md)

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
5. ⚠️ MANDATORY: Update IMPLEMENTATION_STATUS.md (test counts, Recent Updates)
6. ⚠️ MANDATORY: Update TODO.md (mark issues RESOLVED with commit hash)
7. Merge: git checkout main && git merge feature/my-component
```

**Details:** [TDD Workflow](docs/coding_standards/TDD_WORKFLOW.md)

### ⚠️ NEVER SKIP: Status Updates (Dit wordt vaak vergeten!)

**Na ELKE implementatie, refactor, of fix:**

```powershell
# 1. Get current test count
pytest tests/ --collect-only -q | Select-String "^\d+ tests"

# 2. Update IMPLEMENTATION_STATUS.md
# - Update test counts in tables
# - Add entry to "Recent Updates" section
# - Update "Last Updated" date

# 3. Update TODO.md
# - Mark completed items with [x]
# - Add commit hash and RESOLVED status
# - Update Summary table percentages

# 4. Commit the doc updates
git add docs/TODO.md docs/implementation/IMPLEMENTATION_STATUS.md
git commit -m "docs: update status for <feature> completion"
```

**WHY:** Zonder status updates is voltooid werk onzichtbaar voor toekomstige sessies.

### Phase 2: Quality Gates (Verplicht!)

All 5 gates must pass with 10.00/10 + 100% tests passing.

**See:** [Quality Gates](docs/coding_standards/QUALITY_GATES.md) for commands and details.

## Key Anti-Patterns (DON'T!)

❌ **NO Operators** - Use EventAdapters + wiring_map
❌ **NO enriched_df** - Use IStrategyCache + DTOs
❌ **NO runtime YAML** - Use BuildSpecs
❌ **NO hardcoded dependencies** - Use dependency injection
❌ **NO dict-based data** - Use Pydantic DTOs
❌ **NO trailing whitespace** - Auto-fix: `(Get-Content <file>) | ForEach-Object { $_.TrimEnd() } | Set-Content <file>`
❌ **NO imports in functions** - Always top-level
❌ **NO code without tests** - TDD is mandatory
❌ **NO subjective ContextWorkers** - ContextWorkers produce objective facts only (no "bullish", "strong", etc.)
❌ **NO implementation without status updates** - Update TODO.md + IMPLEMENTATION_STATUS.md after EVERY feature

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
- **System DTOs**: Platform-defined (Signal, Risk, etc.), on EventBus

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
- [ ] Gelezen: OBJECTIVE_DATA_PHILOSOPHY.md (ContextWorkers = facts, consumers = interpretation?)
- [ ] Gelezen: POINT_IN_TIME_MODEL.md (IStrategyCache begrip?)
- [ ] Gelezen: Relevante worker/DTO/platform doc
- [ ] Ontwerp gemaakt (architecturale positie, verantwoordelijkheden)
- [ ] Template gevonden (docs/reference/)
- [ ] Feature branch aangemaakt
- [ ] TDD workflow klaar (RED → GREEN → REFACTOR)

**Als één van deze "nee" is, STOP en lees eerst de docs.**

---

## Interaction Guidelines

### Language Policy

| Context | Language | Rationale |
|---------|----------|-----------|
| **Documentation** (all `.md` files) | English | Broader accessibility, industry standard |
| **Code comments & docstrings** | English | Consistency with documentation |
| **Conversation with AI assistant** | Dutch | Native language for precision and nuance |
| **Commit messages** | English | Git log readability |

**Rule:** All written artifacts (documentation, code, commits) are in English. Verbal/chat interaction with the AI assistant is in Dutch.

---

**Documentation maintained by:** Development Team  
**Last major update:** 2025-11-27  
**Version:** V3.1  
**For detailed docs:** See `docs/` folders above
