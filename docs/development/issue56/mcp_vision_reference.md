# ST3 Workflow MCP Server: Vision & Architecture Reference

**Document Type:** Vision & Architecture Reference  
**Status:** DEFINITIVE  
**Version:** 1.0  
**Created:** 2026-01-16  
**Purpose:** Comprehensive reference for understanding MCP server vision, architecture, and roadmap  
**Audience:** New agents, developers, maintainers  
**Context:** Created during Issue #56 research to establish foundational understanding

---

## Executive Summary

### What is the ST3 Workflow MCP Server?

The **ST3 Workflow MCP Server** is an intelligent development orchestration platform that acts as an **AI-native development partner** for the SimpleTraderV3 project. It transforms software development from ad-hoc execution to a **structured, enforced, configuration-driven workflow**.

**In One Sentence:**  
*An MCP server that enforces architectural patterns, TDD principles, and quality standards through intelligent tooling and configuration-driven workflows, enabling AI agents to develop software with human-level discipline and consistency.*

### Why Does It Exist?

Traditional development workflows suffer from three fundamental problems:

1. **Knowledge Scatter**: Standards live in documentation but aren't enforced
2. **Manual Ceremony**: Developers repeat boilerplate and workflow steps manually
3. **Inconsistent Quality**: Quality depends on developer discipline, not system constraints

**The ST3 Workflow MCP Server solves these by:**
- **Encoding standards as enforced policies** (not just documentation)
- **Automating ceremony** (scaffolding, validation, transitions)
- **Making quality gates mandatory** (fail-fast on violations)

### Core Value Proposition

| Traditional Development | ST3 Workflow MCP Server |
|------------------------|-------------------------|
| Standards in docs (unenforced) | Standards as executable policies |
| Manual boilerplate | Template-driven scaffolding |
| Quality checks optional | Quality gates mandatory |
| Workflow guidance | Workflow enforcement |
| Static documentation | Dynamic context |
| Developer discipline | System constraints |

---

## The Problem We're Solving

### The Real Problem: Development at Scale

SimpleTraderV3 is a **plugin-driven, event-driven trading platform** with strict architectural principles:

1. **Plugin First**: All strategy logic is plugins
2. **Separation of Concerns**: Workers vs Platform vs Configuration
3. **Configuration-Driven**: Behavior controlled by YAML
4. **Contract-Driven**: Pydantic DTOs everywhere

**Challenge**: How do you maintain these principles when:
- Multiple developers work on the codebase
- AI agents generate code
- Requirements evolve over months/years
- Quality cannot be compromised (trading platform = money at risk)

### The MCP Server's Answer

**Transform implicit knowledge into executable constraints.**

Instead of:
> "Please follow TDD principles and write tests first"

We have:
> `git_add_or_commit(phase='red')` → **Blocks if non-test files are staged**

Instead of:
> "DTOs should be immutable Pydantic models"

We have:
> `scaffold_component(type='dto')` → **Generates validated, frozen BaseModel**

Instead of:
> "Check quality before merging"

We have:
> `transition_phase(to='integration')` → **Blocks if quality gates fail**

---

## Core Architectural Vision

### The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  (Claude Desktop, IDE, CLI Tools)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ JSON-RPC (stdio)
┌──────────────────────▼──────────────────────────────────────┐
│                    MCP SERVER CORE                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Router     │  │     Auth     │  │  Config Manager │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              BUSINESS LOGIC LAYER                           │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ GitManager  │ │ QAManager    │ │ ScaffoldManager  │    │
│  │ GHManager   │ │ DocManager   │ │ PolicyEngine     │    │
│  │ PhaseState  │ │ ProjectMgr   │ │ DirectoryResolver│    │
│  └─────────────┘ └──────────────┘ └──────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 ADAPTER LAYER                               │
│  ┌────────────┐ ┌──────────────┐ ┌────────────────┐       │
│  │    Git     │ │   GitHub     │ │   FileSystem   │       │
│  │ (GitPython)│ │  (PyGithub)  │ │  (pathlib)     │       │
│  └────────────┘ └──────────────┘ └────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

#### Decision 1: Python (Not TypeScript)

**Context**: MCP SDK supports both Python and TypeScript

**Decision**: 100% Python

**Rationale**:
- SimpleTraderV3 is 100% Python
- Direct import of `backend.*` validators
- Shared tooling (pytest, pylint, mypy)
- Shared configuration (pyproject.toml)
- Zero context switching
- Maximum code reuse

**Consequence**: Can directly use Pydantic models from backend in MCP tools

#### Decision 2: Configuration-Driven Everything

**Context**: Traditional MCP servers hardcode workflow logic

**Decision**: All behavior controlled by YAML configs

**Rationale**:
- Mirrors SimpleTraderV3's "Configuration-Driven" principle
- Workflows customizable without code changes
- Policies enforceable at config level
- Extensible without modifying Python code

**Consequence**: 8 YAML files control all server behavior

#### Decision 3: Strict Separation of Tooling vs Enforcement

**Context**: Quality gates and enforcement were tangled

**Decision**: Epic #76 provides tools, Epic #18 provides enforcement

**Rationale**:
- **Single Responsibility Principle** (SRP)
- Tools are generic executors (QAManager runs any gate)
- Enforcement decides when/where tools are required
- Decouples "what is possible" from "what is required"

**Consequence**: Clear boundaries, easier testing, simpler maintenance

---

## Domain Separation: The Three Realms

The MCP Server operates across three distinct domains with **fundamentally different enforcement models**:

### 1. Code Enforcement (Backend) - HARD CONSTRAINTS

**Purpose**: Ensure backend code follows architectural patterns

**Philosophy**: Code structure is **non-negotiable**, enforced at creation time

**Why Hard Enforcement?**
- **Code executes** → wrong structure = runtime errors
- **Dependencies matter** → import graph must be valid
- **Architectural contracts** → base classes must be implemented correctly
- **Type safety** → Pydantic validation, mypy checking
- **No flexibility** → DTOs are frozen, Workers implement IWorkerLifecycle

**Mechanisms**:
- `scaffold_component` generates compliant code
- `validate_architecture` checks DTO/Worker structure
- Quality gates enforce style/typing
- PolicyEngine **BLOCKS** non-scaffolded creation in backend/

**Example Enforcement**:
```yaml
# policies.yaml
operations:
  create_file:
    blocked_patterns:
      - "backend/**"  # Must use scaffold_component
```

**Result**: Code that doesn't follow patterns **CANNOT BE CREATED**

### 2. Document Organization (Docs) - SOFT GUIDANCE

**Purpose**: Maintain consistent, navigable documentation

**Philosophy**: Documents follow **templates**, but content is **flexible and creative**

**Why Soft Guidance?**
- **Documents don't execute** → no runtime graph
- **No dependencies** → markdown is markdown
- **Human consumption** → flexibility in expression matters
- **Context-dependent** → different docs need different structures
- **Evolutionary** → docs evolve with understanding

**Mechanisms**:
- `scaffold_document` generates from templates
- `validate_document_structure` checks sections/format (**warnings**, not errors)
- Template hierarchy (BASE → Architecture/Design/Reference)
- Status lifecycle (DRAFT → PRELIMINARY → APPROVED → DEFINITIVE)

**Example Organization**:
```
docs/
├── architecture/        # System design (numbered sections, Mermaid)
├── development/         # Pre-implementation design
├── reference/          # API docs, usage guides
├── implementation/     # Progress tracking (LIVING DOCUMENT)
└── mcp_server/         # MCP server docs (this file!)
```

**Result**: Docs that deviate from templates generate **WARNINGS**, not failures

### 3. Configuration Management (.st3/) - SCHEMA VALIDATION

**Purpose**: Centralize all workflow/policy configuration

**Philosophy**: Configuration is **code**, versioned and validated

**Why Schema Validation?**
- **Configs control behavior** → invalid config = broken server
- **Cross-references** → workflows.yaml references must exist
- **Type safety** → Pydantic models validate structure
- **Fail-fast** → startup errors, not runtime surprises

**Mechanisms**:
- 8 YAML files define all behavior
- Pydantic models validate at load time
- Cross-validation ensures consistency
- Singleton pattern for config access

**Configuration Files**:
```yaml
.st3/
├── workflows.yaml      # 6 workflows (feature, bug, hotfix, etc.)
├── validation.yaml     # Template validation rules
├── components.yaml     # 9 component types (DTO, Worker, Tool, etc.)
├── policies.yaml       # Operation policies (scaffold/create_file/commit)
├── project_structure.yaml  # 15 directory definitions
├── git.yaml           # Git conventions (branches, commits, TDD)
├── documents.yaml     # Document templates (Issue #56 - planned)
└── constants.yaml     # Magic numbers (planned)
```

**Result**: Invalid configs **FAIL AT STARTUP**, zero runtime errors

### The Critical Architectural Distinction

| Aspect | CODE (backend/) | DOCUMENTS (docs/) | CONFIG (.st3/) |
|--------|----------------|-------------------|----------------|
| **Enforcement** | HARD (blocks) | SOFT (warns) | SCHEMA (validates) |
| **Flexibility** | Low | High | Medium |
| **Validation** | AST, types, gates | Structure, format | Pydantic models |
| **Purpose** | Runtime artifacts | Human consumption | Behavior definition |
| **Dependencies** | Yes (imports) | No (standalone) | Yes (cross-refs) |
| **Error Impact** | Runtime crash | Hard to find | Server won't start |
| **Change Cost** | High (review, tests) | Low (edit, validate) | Medium (reload) |

**Key Insight for Issue #56**:

`documents.yaml` is **NOT** like `project_structure.yaml` (which enforces WHERE code goes).

`documents.yaml` is **ORGANIZATIONAL METADATA** for:
- Template selection
- Scope categorization
- Status workflows
- Search/filtering

**DirectoryPolicyResolver pattern does NOT apply** because documents have no enforcement policies!

---

## The Configuration Revolution (Epic #49)

### Vision: Transform Hardcoded Rules into Declarative YAML

**Progress**: 4/8 issues complete (50%)

### Completed Transformations ✅

#### Issue #50: Workflows

**Before** (Hardcoded):
```python
if workflow_type == "feature":
    return ["research", "planning", "design", "tdd", "integration", "documentation"]
```

**After** (Config):
```yaml
# workflows.yaml
workflows:
  feature:
    phases:
      - research
      - planning
      - design
      - tdd
      - integration
      - documentation
```

**Impact**: Add new workflow = edit YAML, zero code changes

#### Issue #52: Template Validation

**Before** (Hardcoded):
```python
RULES = {
    "BASE": {"required_sections": ["Purpose", "Scope"], "line_limit": 300}
}
```

**After** (Config + Template Metadata):
```yaml
# Template YAML frontmatter
{# TEMPLATE_METADATA
validates:
  strict:
    - rule: frontmatter_presence
    - rule: section_presence
#}
```

**Impact**: Validation rules in templates, no Python changes

#### Issue #54: Config Foundation

**Before** (Hardcoded):
```python
SCAFFOLDERS = {"dto": DTOScaffolder(), "worker": WorkerScaffolder()}
```

**After** (Config):
```yaml
# components.yaml
component_types:
  dto:
    scaffolder_module: "mcp_server.scaffolders.dto_scaffolder"
    base_path: "backend/dtos"
```

**Impact**: Component registry is data

#### Issue #55: Git Conventions

**Before** (Hardcoded):
```python
VALID_BRANCHES = ["feature", "fix", "refactor"]
TDD_PHASES = ["red", "green", "refactor"]
```

**After** (Config):
```yaml
# git.yaml
branch_types: [feature, fix, refactor]
tdd_phases:
  red: test
  green: feat
  refactor: refactor
```

**Impact**: Git workflow customizable per project

### Planned Transformations ⏳

#### Issue #56: Document Templates (THIS ISSUE)

**Target**: Remove hardcoded `TEMPLATES` and `SCOPE_DIRS` dicts from DocManager

**Vision**:
```yaml
# documents.yaml
template_types:
  architecture:
    jinja_template: documents/architecture.md.jinja2
    default_scope: architecture
    allowed_statuses: [DRAFT, PRELIMINARY, APPROVED, DEFINITIVE]

scope_directories:
  architecture:
    path: architecture
    description: "System architecture and design principles"
```

**Purpose**: **ORGANIZATIONAL METADATA**, not enforcement policies

#### Issue #57: Constants

**Target**: Externalize 40+ magic numbers and regex patterns

#### Issue #105: Dynamic Loading

**Target**: Load scaffolders dynamically from components.yaml

---

## Epic Roadmap & Critical Path

### Epic Dependency Graph

```
Epic #49: Platform Configurability (50% complete)
  ├─> Issue #50: Workflows ✅
  ├─> Issue #52: Template Validation ✅
  ├─> Issue #54: Config Foundation ✅
  ├─> Issue #55: Git Conventions ✅
  ├─> Issue #56: Document Templates ⏳ CURRENT
  ├─> Issue #57: Constants ⏳
  └─> Issue #105: Dynamic Loading ⏳

Epic #18: TDD & Policy Enforcement (30% complete)
  ├─> Issue #42: 8-Phase Model (BLOCKED) 🔴
  └─> Quality Gate Enforcement (BLOCKED by Epic #76)

Epic #76: Quality Gates Tooling (80% complete)
  ├─> QAManager ✅
  ├─> quality.yaml ✅
  └─> Gate catalog ✅
```

### Blocker Chain

**Critical Path**:
1. Issue #42 (8-phase model) **BLOCKED** → contradicts TDD principles
2. Epic #18 enforcement **BLOCKED** → needs Issue #42 foundation
3. Quality Gate Enforcement **BLOCKED** → needs Epic #76 tools

**Issue #56 is UNBLOCKED** - can proceed independently

---

## Key Learnings from Completed Work

### Learning 1: Configuration-Driven Architecture Scales

**Evidence**:
- Issue #50: 6 workflows in 80 lines YAML
- Issue #55: 11 conventions in 60 lines YAML
- Config load time: 17.91ms (well under 100ms target)

**Implication**: Continue Epic #49

### Learning 2: Separation of Concerns is Non-Negotiable

**Context**: Epic #76 (Quality Gates) vs Epic #18 (Enforcement)

**Benefit**:
- Adding new gate: Edit quality.yaml (5 min)
- Adding gate requirement: Edit policy.yaml (5 min)
- No code changes, no circular dependencies

### Learning 3: Singleton Pattern for Configs is Essential

**Pattern**:
```python
class WorkflowConfig:
    _instance: ClassVar["WorkflowConfig | None"] = None
    
    @classmethod
    def load(cls) -> "WorkflowConfig":
        if cls._instance is None:
            cls._instance = cls._load_from_yaml()
        return cls._instance
```

**Benefits**: Single load, cross-validation, fail-fast, thread-safe

### Learning 4: MCP SDK Limitations Exist

**Discovery**: Claude Desktop caches MCP tool schemas
- Changed git.yaml → server reloaded correctly
- Claude Desktop showed old schema
- **Required VS Code restart**

**Limitation**: MCP protocol doesn't have "schema changed" notification

**Implication**: Config changes require client restart

---

## Design Patterns

### 1. Singleton Config Pattern

**Usage**: All config classes

**Structure**:
```python
class GitConfig:
    _instance: ClassVar["GitConfig | None"] = None
    
    @classmethod
    def load(cls) -> "GitConfig":
        if cls._instance is None:
            cls._instance = cls._load_from_yaml()
        return cls._instance
```

### 2. Manager Pattern

**Responsibility**: Business logic, orchestration, validation

**Key Principle**: Managers orchestrate, adapters execute

### 3. Adapter Pattern

**Responsibility**: External system integration, no business logic

**Key Principle**: Adapters are thin wrappers, no decisions

### 4. PolicyEngine Pattern

**Responsibility**: Config-driven policy evaluation

**Key Principle**: Policies are data, engine is logic

---

## Implications for Issue #56

### What Issue #56 IS:

**Organizational Metadata Configuration**

- ✅ Template type definitions (what templates exist)
- ✅ Scope directory mappings (where docs live)
- ✅ Status workflows (document lifecycle)
- ✅ Default values (sensible defaults)
- ✅ Search/filter metadata (categorization)

**Purpose**: Enable DocManager to:
- Look up template metadata
- Map scopes to directories
- Validate status transitions
- Support search/filter operations

**Enforcement Level**: **SOFT** (warnings, not blocking)

### What Issue #56 IS NOT:

**Hard Policy Enforcement**

- ❌ DirectoryPolicyResolver pattern (that's for code enforcement)
- ❌ PolicyEngine integration (documents aren't enforced)
- ❌ Blocking operations (docs are flexible)
- ❌ Architectural validation (docs don't have dependencies)
- ❌ Phase restrictions (docs can be created anytime)

**Anti-Pattern**: Treating `documents.yaml` like `project_structure.yaml`

### The Correct Mental Model

**Code (components.yaml + project_structure.yaml + policies.yaml)**:
- "What can be scaffolded?"
- "Where can it be created?"
- "When is it allowed?"
- **Result**: Enforcement - blocks invalid operations

**Documents (documents.yaml)**:
- "What template types exist?"
- "What scopes are available?"
- "What statuses are valid?"
- **Result**: Metadata - supports lookup/categorization

**Configuration (all .yaml files)**:
- "What structure is required?"
- "What cross-references are valid?"
- "What values are allowed?"
- **Result**: Validation - fails at startup if invalid

---

## Next Steps for Issue #56

### Research Phase Completion

1. **Restore original research content** (section 1-5 from first commit)
2. **Add architectural context** from this vision document
3. **Focus on findings**, NOT design
4. **No code examples** in research (save for planning)

### Key Questions to Answer in Research

1. **What hardcoded values exist?** (TEMPLATES, SCOPE_DIRS)
2. **Where are they used?** (DocManager, tools, resources)
3. **What's the scope?** (5 templates, 5 scopes)
4. **What patterns apply?** (Singleton, cross-validation)
5. **What's the impact?** (7 files, ~480 lines)
6. **What are the risks?** (MCP caching, breaking changes)

### What NOT to Include in Research

- ❌ Full Pydantic model designs (planning phase)
- ❌ Integration code examples (planning phase)
- ❌ Implementation details (TDD phase)
- ❌ DirectoryPolicyResolver patterns (wrong domain)
- ❌ Enforcement logic (not applicable)

---

## Conclusion

The ST3 Workflow MCP Server is transforming software development by:

1. **Encoding standards as executable constraints**
2. **Automating ceremony through intelligent tooling**
3. **Separating concerns across three domains** (Code/Documents/Config)
4. **Using configuration to drive behavior** (Epic #49)
5. **Enforcing quality where it matters** (Code hard, Docs soft)

**Issue #56 Role**: Complete the configuration transformation by externalizing document metadata, enabling flexible document organization without over-engineering enforcement.

---

**Document Status**: DEFINITIVE  
**Maintenance**: Update when major architectural decisions are made  
**Next Review**: 2026-02-16 (monthly)
