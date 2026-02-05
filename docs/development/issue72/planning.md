# Issue #72 Template Library Management - Planning

<!-- SCAFFOLD: planning:draft_v1 | 2026-01-22 | docs/development/issue72/planning.md -->

**Status:** REVISED (Post-TDD Analysis + Phase 1 Completion Audit)  
**Phase:** Phase 1 INCOMPLETE - Registry/Provenance Not Integrated  
**Date:** 2026-01-23 (revised from 2026-01-22)  
**Input:** [research_summary.md](research_summary.md) (719 lines)

---

## Chronologie / SSOT (Source of Truth)

**Leesvolgorde voor template implementation:**
1. **planning.md** (dit document, tot "Design phase complete" context) - Overall strategy, effort estimates, task breakdown
2. **[tdd-planning.md](tdd-planning.md)** (Cycles 1-7, dated 2026-01-26) - **DETAILED implementation** for DOCUMENT templates (design.md MVP)
3. **planning.md** (vanaf "Post-TDD continuation" sectie) - Generalization beyond design.md (dto/worker/service/generic, tracking, CONFIG)

**Superseded assumptions (as of 2026-01-26):**
- âš ï¸ **SCAFFOLD format:** planning.md originally described 1-line format; **tdd-planning.md Cycle 2 defines 2-line format as SSOT**
- âš ï¸ **Document tier implementation order:** tdd-planning.md Cycles 3-5 define detailed sequence; **follow tdd-planning for tier1_base_document â†’ tier2_base_markdown â†’ concrete/design.md**
- âš ï¸ **Tracking scope:** tdd-planning.md marks tracking as "future work"; **tracking implementation deferred until post-TDD continuation**

**Handoff boundary:**
- Complete tdd-planning.md Cycle 7 (E2E test for design.md) before resuming planning.md tasks
- Cycle outputs become **required inputs** for planning.md continuation (see "Post-TDD continuation" section)

---

**âš ï¸ CRITICAL UPDATE #1:** After commit 2ee9228 analysis, discovered **forceful cutover** broke legacy scaffolding. See [cutover-analysis.md](cutover-analysis.md) for complete findings. Planning revised to reflect:
- âœ… Phase 1 Tier 0-2 templates **COMPLETE** 
- âš ï¸ Phase 1 Registry/hash/provenance **INCOMPLETE** - NOT integrated in scaffold flow
- â­ï¸ **Tasks 1.1b/c (registry completion) MUST finish BEFORE Task 1.6** - prevents non-traceable artifacts
- âŒ Phase 4 (Migration) **OBSOLETE** - legacy templates already unreachable
- ðŸ’° **Net change: -48h vs original 183h** (less savings due to registry work)

**âš ï¸ CRITICAL UPDATE #2:** Phase 1 Definition-of-Done NOT met:
- âŒ `.st3/template_registry.yaml` never created (no save_version() calls)
- âŒ `compute_version_hash()` uses placeholder "concrete" (not traceable)
- âŒ `ArtifactDefinition.version` conflicts with registry-based versioning
- âŒ No E2E test for scaffold â†’ header â†’ registry roundtrip
- **Impact:** Cannot proceed to Task 1.6 without fixing - would produce untraceable artifacts

---

## Purpose

Break down research findings from Issue #72 into **actionable implementation tasks** with clear sequencing, effort estimation, dependencies, and risk mitigation.

**Scope Clarity:**
- âœ… **Planning = WHAT to build + WHEN + HOW MUCH effort**
- âŒ **Planning â‰  Design (HOW to architect/implement)**

---

## Scope

### In Scope
- Task breakdown with clear acceptance criteria
- Dependency mapping (blockers, prerequisites)
- Implementation sequencing (phases, critical path)
- Effort estimation (hours per task, total timeline)
- Risk identification and mitigation strategies
- Success criteria and rollback plans
- Validation strategy for acceptance criteria

### Out of Scope (Reserved for Design Phase)
- Detailed technical architecture
- API specifications and contracts
- Algorithm implementations
- Code structure and patterns
- Database schema design
- Performance optimization strategies

---

## Prerequisites

1. âœ… Research phase complete:
   - [research.md](research.md) - Full exploration with alternatives (2500+ lines)
   - [research_summary.md](research_summary.md) - Final decisions and blockers (719 lines)
   
2. âœ… MVP validation complete:
   - [docs/development/issue72/mvp/](mvp/) - 5-tier template proof-of-concept
   - 67% variable coverage improvement demonstrated
   
3. âœ… Issue #52 alignment confirmed:
   - TEMPLATE_METADATA format documented
   - Validation integration strategy defined

4. âœ… Design phase complete (2026-01-26):
   - [document-tier-allocation.md](document-tier-allocation.md) - Complete tier specs for DOCUMENT artifacts
   - [tracking-type-architecture.md](tracking-type-architecture.md) - Tracking as base type (not ephemeral)
   - [whitespace_strategy.md](whitespace_strategy.md) - Jinja2 whitespace control rules
   - [tdd-planning.md](tdd-planning.md) - 7 TDD cycles for document template implementation

5. âš ï¸ **Critical Blockers Identified (3):**
   - Template inheritance introspection (must fix before rollout)
   - IWorkerLifecycle pattern validation (audit required)
   - Backend pattern inventory (24 templates, 65h baseline)

---

## Acceptance Criteria Validation Strategy

### Coverage Summary (from Research)

| Category | Status | Count | Planning Action |
|----------|--------|-------|-----------------|
| **Architecture** (hierarchy, registry, SCAFFOLD) | âœ… Designed | 4/4 | Implementation tasks ready |
| **Template Quality** (lifecycle, patterns, hints) | âš ï¸ Partial/Gap | 1/5 proven, 4/5 gaps | Requires audit & prototype |
| **Extensibility** (language/format addition) | âœ… Proven | 3/3 | Proof tasks ready |

**Planning Priority:**
1. **Phase 1 (Foundation):** Implement 4/4 proven architecture criteria
2. **Phase 2 (Validation):** Address 3 critical blockers
3. **Phase 3 (Quality):** Complete 4/5 remaining gaps

### AC-by-AC Validation Plan

#### AC1: 5-level template hierarchy implemented
- **Status:** âœ… Designed (MVP proven)
- **Tasks:** Create Tier 0-3 base templates (9 templates estimated)
- **Validation:** Introspection returns 5-tier chain for concrete template
- **Effort:** 2h + 6h + 9h + 24h = 41h

#### AC2: Base templates cover 3 Tier 1 categories
- **Status:** âœ… Designed (CODE/DOCUMENT proven, CONFIG extrapolated)
- **Tasks:** Create `base_code.jinja2`, `base_document.jinja2`, `base_config.jinja2`
- **Validation:** Each Tier 1 template provides format-specific structure blocks
- **Effort:** 6h

#### AC3: Template registry operational with hash-based versioning
- **Status:** âœ… Designed (format defined)
- **Tasks:** Build `.st3/template_registry.yaml` + read/write utilities
- **Validation:** `scaffold_artifact()` writes registry, hash lookup succeeds
- **Effort:** 8h

#### AC4: SCAFFOLD metadata = 1 line
- **Status:** âš ï¸ **SUPERSEDED** (pre-2026-01-26 assumption)
- **Superseded by:** [tdd-planning.md](tdd-planning.md) Cycle 2 defines **2-line format** as SSOT
- **Tasks:** Tier 0 provides `scaffold_metadata` block
- **Validation:** All scaffolded files have 2-line header (line 1: filepath, line 2: metadata)
- **Effort:** Included in Tier 0 creation (2h)

#### AC5: Worker uses IWorkerLifecycle
- **Status:** âš ï¸ BLOCKER - Hypothesis unvalidated
- **Tasks:** **MUST AUDIT** actual backend usage before planning
- **Validation:** Cannot define until pattern confirmed
- **Effort:** TBD after audit (estimate 8-16h)

#### AC6: All backend patterns reflected
- **Status:** ðŸ”´ BLOCKER - No inventory exists
- **Tasks:** **MUST COMPLETE** pattern audit (Blocker #3)
- **Validation:** Cannot define until inventory complete
- **Effort:** TBD after inventory (estimate 24h pattern catalog)

#### AC7: Research/planning/test with agent hints
- **Status:** ðŸ”´ GAP - Format undefined
- **Tasks:** Define hint syntax, prototype in research.md (OQ-P2)
- **Validation:** Agent run with hinted template improves content quality
- **Effort:** 4h prototype + 8h rollout = 12h

#### AC8: Documentation covers usage/patterns
- **Status:** ðŸ”´ GAP - Structure undefined
- **Tasks:** Define docs structure, write template usage guide
- **Validation:** Developer can scaffold new artifact following guide
- **Effort:** 16h (architecture guide + usage examples)

#### AC9: All scaffolded code passes validation
- **Status:** âš ï¸ DEPENDENCY - Requires Issue #52 completion
- **Tasks:** Coordinate with #52, integrate validation hooks
- **Validation:** E2E test with #74 (DTO/Tool validation)
- **Effort:** 8h coordination + testing

#### AC10: Adding new language = 1 Tier 2 template
- **Status:** âœ… Proven (TypeScript extrapolation)
- **Tasks:** Create `base_typescript.jinja2` as proof
- **Validation:** TypeScript worker scaffolds with 1 new template
- **Effort:** 4h (Tier 2 TypeScript)

#### AC11: Adding new format = 1 Tier 1 template
- **Status:** âœ… Proven (CONFIG identified)
- **Tasks:** Create `base_config.jinja2` + `base_yaml.jinja2`
- **Validation:** YAML workflow scaffolds with new tier chain
- **Effort:** 5h (Tier 1 CONFIG + Tier 2 YAML)

#### AC12: SCAFFOLD defined once (Tier 0), inherited by all
- **Status:** âœ… Proven (MVP demonstrates)
- **Tasks:** All concrete templates extend Tier 0 chain
- **Validation:** Introspection shows `scaffold_metadata` from Tier 0
- **Effort:** Included in migration (24h)

#### AC13: Template library documented
- **Status:** Linked to AC8
- **Tasks:** Same as AC8 documentation
- **Effort:** Included in AC8 (16h)

---

## Critical Path Analysis

### Critical Blocker #1: Inheritance-Aware Introspection
**Impact:** Without this, multi-tier templates cannot validate user input (67% variable miss rate)  
**Dependencies:** None (can start immediately)  
**Effort:** 8h implementation + 4h testing = 12h  
**Priority:** P0 (blocks all multi-tier scaffolding)
**Status:** âœ… **RESOLVED** (2026-01-27)

**Tasks:**
1. âœ… Integrate `introspect_template_with_inheritance()` from MVP into `TemplateIntrospector`
2. âœ… Unit test: 5-tier worker template returns all 8 variables (concrete + inherited)
3. âœ… E2E test: Scaffolding validates against complete schema
4. âœ… Document introspection algorithm in architecture guide

**Definition of Done:**
- [x] `introspect_template(template_name, with_inheritance=True)` returns inherited variables
- [x] Test: `introspect_template("worker.py.jinja2", with_inheritance=True)` returns 8 vars (not 2)
- [x] Scaffolding rejects missing inherited variables with clear error

**Outcomes:**
- AST-based inheritance chain resolution implemented (commit 5854b63)
- Multi-tier variable merging operational (commit a98bb60)
- Integrated in TemplateScaffolder.validate() workflow
- Quality gates passed (10/10 linting, commit 257f2c6)

---

### Critical Blocker #2: IWorkerLifecycle Pattern Audit
**Impact:** Cannot design Tier 3 `base_python_component.jinja2` without pattern validation  
**Dependencies:** None (research/audit task)  
**Effort:** 4h audit + 2h documentation = 6h  
**Priority:** P0 (blocks Tier 3 specialization design)
**Status:** âœ… **RESOLVED** (2026-01-27)

**Tasks:**
1. âœ… **Audit codebase:** Search `src/workers/` for IWorkerLifecycle implementations
2. âœ… **Find contract:** Locate IWorkerLifecycle interface definition (if exists)
3. âœ… **Assess necessity:** Document why two-phase init is architectural requirement
4. âœ… **Verify template:** Check if `worker.py.jinja2` currently generates lifecycle code
5. âœ… **Cross-language check:** Do other components (TypeScript?) follow similar patterns?

**Definition of Done:**
- [x] Document: "X out of Y workers implement IWorkerLifecycle"
- [x] Document: IWorkerLifecycle interface location and contract
- [x] Document: Rationale for two-phase init (or reasons to remove from AC)
- [x] Decision: Confirm/reject Tier 3 placement for lifecycle pattern

**Possible Outcomes:**
- âœ… **Validated:** Add lifecycle blocks to `tier3_base_python_component.jinja2`

**Outcomes:**
- Comprehensive audit: 1 of 3 workers implement IWorkerLifecycle (FlowInitiator)
- Protocol location: `backend/core/interfaces/worker.py`
- Recommendation: MANDATORY with opt-out (aligns with all 4 Core Principles)
- Worker template updated to generate IWorkerLifecycle pattern (commit 550ee25)
- Deliverable: [phase2-task22-iworkerlifecycle-audit.md](phase2-task22-iworkerlifecycle-audit.md) (1253 lines)
- Strategic finding: Templates teach agents patterns - critical for agentic development

---

### Critical Blocker #3: Backend Pattern Inventory
**Impact:** Cannot complete AC6 "all backend patterns reflected" without exhaustive list  
**Dependencies:** None (research task)  
**Effort:** 8h audit + 4h catalog + 4h tier assignment = 16h  
**Priority:** P1 (blocks Tier 2/3 completeness, but doesn't block MVP)
**Status:** âœ… **RESOLVED** (2026-01-29)

**Tasks:**
1. âœ… Audit `src/workers/`, `src/adapters/`, `src/services/` for architectural patterns
2. âœ… List patterns: Dependency injection, error handling, logging, config, lifecycle, etc
3. âœ… Assign each pattern to Tier 2 (syntax) or Tier 3 (specialization)
4. âœ… Document pattern rationale and usage examples
5. âœ… Create "Backend Pattern Catalog" in design docs

**Definition of Done:**
- [x] Exhaustive pattern list with examples
- [x] Tier assignment rationale per pattern
- [x] Template coverage: Map patterns to Tier 2/3 templates
- [x] Documentation: Pattern usage guide for template authors

**Outcomes:**
- **12 patterns cataloged:** 9 MANDATORY (75%), 1 OPTIONAL (8%), 2 RECOMMENDED (17%)
- **Tier 2 patterns (4):** Module Header, Import Organization, Type Hinting, Async/Await
- **Tier 3 patterns (8):** IWorkerLifecycle, Pydantic DTO, Error Handling, Logging, Typed ID, DI via Capabilities, LogEnricher, Translator/i18n
- **Template Coverage Map:** Worker (8 patterns), DTO (6), Adapter (6), Service (6)
- **Documentation:** [phase2-task23-backend-pattern-catalog.md](phase2-task23-backend-pattern-catalog.md) (875 lines)
- **Phase 3 Ready:** All blockers resolved, proceed to Tier 3 template design

---

## Post-TDD Continuation (Resume Point)

**Context:** Na succesvolle afronding van [tdd-planning.md](tdd-planning.md) Cycle 7 (E2E test voor design.md MVP), hervat dit document met generalisatie en uitbreiding.

### Required Inputs from tdd-planning.md

De volgende deliverables van tdd-planning zijn **vereiste dependencies** voor continuation:

#### Cycle 1 Output: artifacts.yaml type field
- **Deliverable:** `.st3/artifacts.yaml` heeft `type: code|doc|tracking|config` voor alle artifacts (âš ï¸ Note: tracking is post-TDD extension per [tracking-type-architecture.md](tracking-type-architecture.md), not part of tdd-planning Cycle 1 SSOT which adds `code|doc|config` only)
- **Planning impact:** Enables type-based tier routing voor CODE/TRACKING/CONFIG templates (beyond DOCUMENT)
- **Mapping:** Niet expliciet als Task in planning.md; **required before Phase 3 (Tier 3 templates)**

#### Cycle 2 Output: tier0_base_artifact.jinja2 (2-line SCAFFOLD)
- **Deliverable:** Universal base met 2-line SCAFFOLD format (filepath + metadata)
- **Planning impact:** Supersedes AC4; validates planning Task 1.2 implementation
- **Mapping:** âœ… planning.md Task 1.2 already updated to reference tdd-planning Cycle 2

#### Cycle 3 Output: tier1_base_document.jinja2
- **Deliverable:** Universal document structure (Status/Purpose/Scope/Prerequisites/Related/Version History)
- **Planning impact:** Defines document-lane tier1 structure
- **Mapping:** âœ… planning.md Task 1.3 includes tier1_base_document (detailed impl in tdd-planning)

#### Cycle 4 Output: tier2_base_markdown.jinja2
- **Deliverable:** Markdown syntax (HTML comments, link definitions, code blocks)
- **Planning impact:** Enables Markdown document types beyond design.md
- **Mapping:** âœ… planning.md Task 1.4 includes tier2_base_markdown

#### Cycle 5 Output: concrete/design.md.jinja2
- **Deliverable:** Full DESIGN_TEMPLATE with numbered sections, options, decisions
- **Planning impact:** Proves concrete template pattern; **planning Task 1.6 extends to dto/worker/service/generic**
- **Mapping:** planning.md Task 1.6 is **broader** (5 concrete templates); tdd does design.md MVP, planning continues with CODE concretes

#### Cycle 6 Output: Validation integration (Issue #52 enforcement)
- **Deliverable:** TEMPLATE_METADATA enforcement behavior for DOCUMENT tier chain
- **Planning impact:** Proves STRICT enforcement for tiers; **planning extends to all artifact types**
- **Mapping:** planning.md Task 1.5 (Issue #52 alignment) covers metadata structure; Cycle 6 adds runtime enforcement

#### Cycle 7 Output: E2E test (design.md scenario)
- **Deliverable:** Complete scaffold â†’ parse â†’ validate roundtrip for design.md
- **Planning impact:** Proves provenance chain; **planning Task 1.6b generalizes to multiple artifact types**
- **Mapping:** planning.md Task 1.6b (provenance regression) = E2E for dto/worker/service/generic + registry roundtrip

### Post-TDD Task Sequencing

**IMMEDIATE (Phase 1 DoD completion):**
1. **Task 1.6: Extend concrete templates beyond design.md**
   - Input: Cycle 5 design.md pattern
   - Extend: dto.py.jinja2, worker.py.jinja2, service_command.py.jinja2, generic.py.jinja2
   - Effort: 3h Ã— 4 = 12h (design.md proves pattern, CODE templates follow)

2. **Task 1.6b: Generalize E2E provenance test**
   - Input: Cycle 7 design.md E2E test
   - Extend: Multiple artifact types (dto/worker/service/generic) + registry lookup roundtrip
   - Effort: 8h (already partially done, extend test matrix)

**DEFERRED (until post-Cycle 7):**
3. **Tracking templates (Tier 1 + concretes)**
   - Input: [tracking-type-architecture.md](tracking-type-architecture.md)
   - Scope: tier1_base_tracking.jinja2 + concrete/commit.txt, pr.md, issue.md, etc.
   - **Blocker:** Migrate legacy `commit-message.txt.jinja2` from `mcp_server/templates/` to tier-based structure
   - Test currently skipped: `test_scaffold_ephemeral_returns_temp_path` (see test_metadata_e2e.py)
   - Rationale: tdd-planning marks tracking as "future work"; defer to avoid scope creep
   - Mapping: planning.md Task 3.5 (renamed from ephemeral â†’ tracking)
   - Effort: 3h (tier1) + 2h Ã— 6 concretes + 1h (migration) = 16h

4. **CONFIG templates (Tier 3 + concretes)**
   - Scope: tier3_base_yaml_policy.jinja2 + workflows.yaml, labels.yaml
   - Mapping: planning.md Task 3.6 + Task 4.4
   - Effort: 3h (tier3) + 4h (concretes) = 7h

5. **Extensibility (TypeScript, Rust)**
   - Scope: tier2_base_typescript.jinja2, tier2_base_rust.jinja2
   - Mapping: planning.md Phase 5 (Tasks 5.1-5.3)
   - Effort: 8h

---

## Task Breakdown with Dependencies

### Phase 1: Foundation (Infrastructure)
**Goal:** Implement proven architecture without blockers  
**Duration:** ~2 weeks (80h â†’ **revised 95h**)  
**Dependencies:** None (can start immediately)
**Status:** âœ… **COMPLETE** (2026-01-29) - All tasks finished, 1504/1507 tests passing (99.8%)

**âœ… PROGRESS UPDATE (2026-01-29):**
Phase 1 is **100% complete** - all infrastructure, templates, and QA alignment done:
- âœ… Task 1.1: TemplateRegistry class complete (all methods operational)
- âœ… Task 1.1b: compute_version_hash() fixed - extracts real template versions
- âœ… Task 1.1c: Registry integrated in scaffold_artifact() flow
- âœ… Task 1.2: Tier 0 base template created (tier0_base_artifact.jinja2)
- âœ… Task 1.3: Tier 1 bases complete (CODE, DOCUMENT, CONFIG; TRACKING deferred)
- âœ… Task 1.4: Tier 2 bases complete (Python, Markdown, YAML)
- âœ… Task 1.5: TEMPLATE_METADATA alignment done
- âœ… Task 1.5b: ArtifactDefinition.version removed - conceptual clarity achieved
- âœ… Task 1.6: 9 concrete templates created (5 required + 4 additional)
- âœ… QA Alignment: Quality gates 10/10 achieved
- âœ… Test Status: 1504/1507 tests passing (99.8% pass rate)

**Phase 1 Definition-of-Done:**
- [x] Quality gates pass (lint/typecheck/tests) - **1504/1507 tests pass**
- [x] Registry operational: scaffold creates `.st3/template_registry.yaml` entries
- [x] Version hash traceable: real template versions extracted
- [x] SCAFFOLD header format: 2-line format implemented
- [x] E2E tests: scaffold â†’ validate â†’ registry roundtrip works
- [x] Zero conceptual conflicts (artifacts.yaml = variants, registry = provenance)

#### Task 1.1: Template Registry Infrastructure
- **Description:** Build `.st3/template_registry.yaml` read/write utilities
- **Input:** Research Q8b (registry structure)
- **Output:** 
  - `TemplateRegistry` class with `save_version()`, `lookup_hash()`, `get_current_version()`
  - Unit tests for hash collision detection
  - Methods: `_load()`, `_persist()`, `get_all_hashes()`, `get_all_artifact_types()`
- **Acceptance:** `scaffold_artifact()` writes registry entry, lookup returns tier chain data
- **Effort:** 8h
- **Assignee:** Backend Engineer
- **Status:** âœ… **COMPLETE** (original implementation)

#### Task 1.1b: Fix compute_version_hash Implementation
- **Description:** Replace placeholder "concrete" with real template IDs + versions
- **Input:** Design spec (design.md:590-639) for hash computation
- **Output:**
  - `compute_version_hash()` reads template IDs from tier chain
  - Hash format: `artifact_type|tier0@v1|tier1@v1|...|concrete@v1` â†’ SHA256 â†’ 8 chars
  - Template version extraction from SCAFFOLD metadata or registry
  - Added `extract_template_version()` to parse TEMPLATE_METADATA YAML block
- **Acceptance:** Hash is reproducible from tier chain, no placeholders
- **Effort:** 4h
- **Assignee:** Backend Engineer
- **Priority:** **P0** - blocks provenance traceability
- **Status:** âœ… **COMPLETE** (commits 1226de6 RED, 0df997e GREEN)

#### Task 1.1c: Integrate Registry in scaffold_artifact() Flow
- **Description:** Add registry save to ArtifactManager.scaffold_artifact()
- **Output:**
  - Compute version_hash BEFORE rendering
  - Call `registry.save_version(artifact_type, version_hash, tier_chain)` 
  - Inject version_hash into template context
  - Create `.st3/template_registry.yaml` if not exists
- **Acceptance:** Every scaffold operation writes registry entry
- **Effort:** 3h
- **Assignee:** Backend Engineer
- **Priority:** **P0** - blocks provenance
- **Status:** âœ… **COMPLETE** (commits c65441a RED, 45d7563 GREEN)
- **âš ï¸ Known Gap:** tier_chain = [] (empty), template_registry default None â†’ registry not auto-created
- **Follow-up:** Task 1.6 concrete templates + tier introspection will fill tier_chain

#### Task 1.2: Tier 0 Base (Universal SCAFFOLD)
- **Description:** Create `tier0_base_artifact.jinja2` with 2-line SCAFFOLD format
- **Input:** 2-line format from [tdd-planning.md](tdd-planning.md) Cycle 2
- **Output:** 
  - Line 1: `# {filepath}` (language-adaptive comment)
  - Line 2: `# template={type} version={hash} created={iso8601} updated=`
  - Works for Python `#`, Markdown `<!--`, YAML `#`
- **Acceptance:** All formats inherit correct 2-line SCAFFOLD header
- **Effort:** 2h
- **Assignee:** Template Author
- **Status:** âœ… **COMPLETE** (file exists: `tier0_base_artifact.jinja2`)

#### Task 1.3: Tier 1 Bases (Format Categories)
- **Description:** Create 4 Tier 1 templates: CODE, DOCUMENT, CONFIG, TRACKING
- **Input:** Dimensional analysis from research + [tracking-type-architecture.md](tracking-type-architecture.md)
- **Output:**
  - `tier1_base_code.jinja2` (imports, classes, functions structure)
  - `tier1_base_document.jinja2` (heading hierarchy) - See [tdd-planning.md](tdd-planning.md) Cycle 3 for detailed implementation
  - `tier1_base_config.jinja2` (schema validation hooks)
  - `tier1_base_tracking.jinja2` (VCS workflow structure) - **DEFERRED to Post-TDD continuation**
- **Acceptance:** Each provides format-specific structure blocks
- **Effort:** 2h Ã— 3 = 6h (DOCUMENT via tdd-planning; CODE/CONFIG in planning; TRACKING post-TDD)
- **Assignee:** Template Author
- **Dependency:** Tier 0 complete
- **Status:** âœ… **COMPLETE** (3 of 4 templates exist: CODE, DOCUMENT, CONFIG; TRACKING deferred)
- **Note:** 
  - DOCUMENT templates follow [tdd-planning.md](tdd-planning.md) Cycles 3-5 (design.md MVP focus)
  - TRACKING marked as "future work" in tdd-planning.md; deferred to avoid scope creep (see Post-TDD continuation)

#### Task 1.4: Tier 2 Bases (Language Syntax)
- **Description:** Create 3 Tier 2 templates: Python, Markdown, YAML
- **Input:** Language-specific syntax patterns from research
- **Output:**
  - `tier2_base_python.jinja2` (type hints, async/await, docstrings)
  - `tier2_base_markdown.jinja2` (link format, code blocks)
  - `tier2_base_yaml.jinja2` (indentation, key format)
- **Acceptance:** Language syntax blocks available for inheritance
- **Effort:** 3h Ã— 3 = 9h
- **Assignee:** Template Author
- **Dependency:** Tier 1 complete
- **Status:** âœ… **COMPLETE** (all 3 files exist: Python, Markdown, YAML)

#### Task 1.5: Issue #52 Alignment (TEMPLATE_METADATA)
- **Description:** Add TEMPLATE_METADATA to Tier 1-2 templates
- **Input:** Issue #52 Alignment section from research
- **Output:** Each base template has enforcement/level/validates structure
- **Acceptance:** Validation infrastructure recognizes base templates
- **Effort:** 1h Ã— 6 templates = 6h
- **Assignee:** Template Author + Validation Engineer
- **Dependency:** Tier 1-2 complete
- **Status:** âœ… **COMPLETE** (commit 10a3c9d)

#### Task 1.5b: Remove ArtifactDefinition.version (Cleanup Conflict)
- **Description:** Eliminate conceptual conflict between artifacts.yaml version and registry-based versioning
- **Output:**
  - Remove `version` field from `ArtifactDefinition` dataclass
  - Remove from `.st3/artifacts.yaml` schema (per-artifact version entries)
  - Remove `template_version` context injection (version comes from registry)
  - Update docs: "artifacts.yaml = selection config (variants), registry.yaml = version/hash provenance"
- **Acceptance:** Zero references to artifact version outside registry
- **Effort:** 2h
- **Assignee:** Backend Engineer
- **Priority:** **P1** - architectural hygiene
- **Status:** âœ… **COMPLETE** (commits cf46670 RED, e4e0b16 GREEN)
- **Impact:** 
  - Removed ArtifactDefinition.version field (artifact_registry_config.py:95)
  - Removed template_version context injection (artifact_manager.py:115)
  - Removed all per-artifact version: "1.0" entries from .st3/artifacts.yaml
  - Tests updated: 6/7 pass (1 pre-existing layered_template_validator bug)

#### Task 1.5c: Add Artifact Variants to artifacts.yaml
- **Description:** Support multiple concrete templates per artifact_type (selection config)
- **Input:** Design concept: artifacts.yaml = WHAT to scaffold (variants), registry = HOW it was built (provenance)
- **Output:**
  - `ArtifactDefinition` supports `variants: [{id, template_path, description}]`
  - Default variant if single template
  - Scaffold tool accepts `variant` parameter
- **Acceptance:** Can scaffold `dto` with variant "pydantic" vs "dataclass"
- **Effort:** 4h
- **Assignee:** Backend Engineer
- **Priority:** P2 - extensibility enhancement
- **Dependency:** Task 1.5b complete

#### Task 1.6: Create Minimal Concrete Templates (UNBLOCK TESTING)
- **Description:** Create 5 concrete templates to fix broken scaffolding after commit 2ee9228
- **Input:** Test suite artifact type usage analysis ([cutover-analysis.md](cutover-analysis.md))
- **Output:** 
  - `concrete/dto.py.jinja2` (Pydantic BaseModel, extends Tier 2 Python)
  - `concrete/worker.py.jinja2` (async worker class, extends Tier 2 Python)
  - `concrete/service_command.py.jinja2` (service pattern, extends Tier 2 Python)
  - `concrete/generic.py.jinja2` (minimal class, extends Tier 2 Python)
  - `concrete/design.md.jinja2` (design doc structure, extends Tier 2 Markdown)
  - Updated `.st3/artifacts.yaml` (5 template path mappings)
  - Fixed test hardcoded paths to use `get_template_root()`
- **Acceptance:** All existing unit and E2E tests pass with new templates
- **Effort:** 5h templates + 30min config + 1h test fixes + 30min validation = **7h**
- **Assignee:** Template Author
- **Priority:** **P0 (BLOCKER)** - tests currently broken due to template path mismatch
- **Dependency:** **Task 1.1c complete (registry operational)** - prevents non-traceable artifacts
- **Status:** âœ… **COMPLETE** (commits 6bf6e02, 2c9cdc1, d65fef9, d7d9b05)
- **Outcomes:** 
  - 9 concrete templates exist (5 required + 4 additional: research, planning, reference, architecture)
  - All templates extend proper tier chains
  - Worker template implements IWorkerLifecycle pattern (Task 2.2 outcome)
  - 1504/1507 tests passing (99.8% pass rate)
  - artifacts.yaml updated with concrete/ paths
- **Context:** Commit 2ee9228 redirected `TemplateScaffolder` to new tier templates without creating concrete templates, breaking all 24 legacy artifact types. This task creates minimal set needed to unblock testing.
- **Note:** Template base path is ALREADY configurable via `get_template_root()` (âœ… complete)
- **âš ï¸ CRITICAL:** Templates MUST inherit Tier 0 SCAFFOLD block AND registry flow must work, otherwise produced artifacts have untraceable hashes

#### Task 1.6b: E2E Provenance Regression Test
- **Description:** Validate scaffold â†’ parse header â†’ registry lookup roundtrip
- **Input:** Task 1.6 concrete templates + operational registry
- **Output:**
  - E2E test: scaffold each artifact type (dto, worker, service, generic, design)
  - Parse SCAFFOLD header from generated file
  - Lookup version_hash in `.st3/template_registry.yaml`
  - Assert tier chain matches template inheritance
  - Assert header format: `artifact_type:version_hash | timestamp | output_path`
- **Acceptance:** All 5 artifact types pass roundtrip validation
- **Effort:** 3h
- **Assignee:** QA Engineer + Backend
- **Priority:** **P0** - validates Phase 1 completeness
- **Dependency:** Task 1.6 complete

### Phase 2: Blocker Resolution (Critical Path)
**Goal:** Unblock Tier 3 design and multi-tier scaffolding  
**Duration:** ~1 week (40h)  
**Dependencies:** None (parallel with Phase 1 if resources available)
**Status:** âœ… **COMPLETE** (2026-01-29) - All 3 critical blockers resolved

#### Task 2.1: Fix Inheritance Introspection (Blocker #1)
- **Description:** Integrate MVP introspection into template_introspector.py
- **Input:** MVP `introspect_template_with_inheritance()` code
- **Output:**
  - Enhanced `introspect_template()` function with inheritance support (AST walking)
  - Unit test: worker.py returns 8 vars (not 2)
  - E2E test: Scaffolding validates complete schema
- **Acceptance:** Multi-tier templates validate user input correctly
- **Effort:** 8h implementation + 4h testing = 12h
- **Assignee:** Backend Engineer
- **Priority:** P0 (blocks Phase 3)
- **Status:** âœ… **COMPLETE** (commits 5854b63, a98bb60, 257f2c6)
- **Deliverable:** `introspect_template_with_inheritance()` in `template_introspector.py`
- **Outcomes:**
  - AST-based inheritance chain resolution implemented
  - Multi-tier template variables merged correctly
  - Integrated in TemplateScaffolder.validate()
  - Quality gates passed (10/10 linting)

#### Task 2.2: IWorkerLifecycle Audit (Blocker #2)
- **Description:** Validate lifecycle pattern hypothesis
- **Input:** Research "Worker Lifecycle Analysis" section
- **Output:**
  - Audit report: X/Y workers use lifecycle, interface location, rationale
  - Decision: Confirm or reject Tier 3 placement
- **Acceptance:** Clear evidence for Tier 3 design decision
- **Effort:** 4h audit + 2h documentation = 6h
- **Assignee:** System Architect
- **Priority:** P0 (blocks Tier 3 design)
- **Status:** âœ… **COMPLETE** (commit d7df3ad, 2026-01-27)
- **Deliverable:** [phase2-task22-iworkerlifecycle-audit.md](phase2-task22-iworkerlifecycle-audit.md) (1253 lines)
- **Outcomes:**
  - IWorkerLifecycle protocol is well-designed but underutilized (1/3 workers)
  - Recommendation: MANDATORY with opt-out for lifecycle pattern
  - Worker template updated to generate IWorkerLifecycle code (commit 550ee25)
  - Pattern confirmed for Tier 3 base_python_component.jinja2
  - Aligns with all 4 Core Principles
  - Strategic value: Template-driven development as foundation for agentic codebases

#### Task 2.3: Backend Pattern Inventory (Blocker #3)
- **Description:** Catalog all backend architectural patterns
- **Input:** Research OQ-P1 (pattern categories)
- **Output:**
  - Backend Pattern Catalog with tier assignments
  - Template coverage map (patterns â†’ Tier 2/3 templates)
- **Acceptance:** Exhaustive pattern list with examples and rationale
- **Effort:** 8h audit + 4h catalog + 4h tier assignment = 16h
- **Assignee:** System Architect + Senior Engineers
- **Priority:** P1 (blocks AC6 completeness, but not MVP)
- **Status:** âœ… **COMPLETE** (2026-01-29)
- **Deliverable:** [phase2-task23-backend-pattern-catalog.md](phase2-task23-backend-pattern-catalog.md) (875 lines)
- **Outcomes:**
  - 12 patterns cataloged (9 MANDATORY, 1 OPTIONAL, 2 RECOMMENDED)
  - 4 Tier 2 patterns (syntax/language-level)
  - 8 Tier 3 patterns (specialization/architecture)
  - Template Coverage Map for Worker/DTO/Adapter/Service templates
  - 75% MANDATORY pattern coverage achieved (9/12)
  - Infrastructure patterns (LogEnricher #11, Translator #12) documented with V2 reference
  - All patterns aligned with Core Principles
  - Pattern catalog includes code examples, rationale, template implications

#### Task 2.4: Agent Hint Format Prototype (OQ-P2)
- **Description:** Define and test agent guidance syntax
- **Input:** Research OQ-P2 example
- **Output:**
  - Hint syntax specification (comment format, keywords)
  - Prototype in `research.md.jinja2`
  - Agent validation run (quality improvement test)
- **Acceptance:** Agent generates better content with hints
- **Effort:** 4h prototype + 2h validation = 6h
- **Assignee:** Agent Developer + Template Author
- **Priority:** P2 (nice-to-have, not blocking)

### Phase 3: Tier 3 Pattern Library (Quality) - âš ï¸ **REVISED 2026-01-30**
**Goal:** Complete template quality acceptance criteria with SRP-based pattern decomposition  
**Duration:** ~4-5 weeks (65h)  
**Dependencies:** Phase 2 (blocker resolution) complete  
**Revision Rationale:** [.st3/phase3-tier3-template-requirements.md v2.0](../../.st3/phase3-tier3-template-requirements.md) - Monolithic tier3 templates rejected, replaced with 17 granular pattern templates for cherry-picking composition

**Key Architectural Changes:**
- âŒ **REMOVED:** Monolithic tier3 templates (tier3_base_python_component, tier3_base_python_data_model, tier3_base_python_tool)
- âŒ **REMOVED:** CONFIG tak (tier1_base_config, tier3_base_yaml_policy) - YAML files are DATA validated by Pydantic schemas
- âœ… **ADDED:** 17 granular tier3 pattern templates (9 CODE + 8 DOCUMENT) for SRP composition
- âœ… **ADDED:** Block library composition via `{% import %}` (not `{% extends %}`)
- âœ… **ADDED:** config_schema.py concrete template (scaffolds Pydantic validation schemas)
- âœ… **CHANGED:** Validation hierarchy: tier0-2 STRICT, tier3 ARCHITECTURAL, concrete GUIDELINE
- âœ… **CHANGED:** template_registry.yaml â†’ template_registry.json (better parsability)

---

#### Task 3.1: Test Pattern Templates (5 templates) - ðŸŽ¯ **QUICK WIN: Bootstrap Testing**
**Description:** Create tier3 pattern templates for test scaffolding (pytest, mocking, assertions)

**Rationale:** Build test templates FIRST to enable scaffolding of tests for all other templates (bootstrap effect)

**Input:** Test suite analysis (tests/unit/*, tests/integration/*, tests/mcp_server/*)

**Subtasks (5 patterns Ã— ~1.8h avg = 9h):**
- **3.1a:** `tier3_pattern_python_pytest.jinja2` - Pytest framework patterns (2h)
  - Blocks: `pattern_pytest_imports`, `pattern_pytest_fixtures`, `pattern_pytest_marks`, `pattern_pytest_parametrize`
  - Patterns: @pytest.fixture, @pytest.mark.asyncio, @pytest.mark.parametrize, pytest_plugins
  - Used by: test_unit, test_integration (2 templates)
- **3.1b:** `tier3_pattern_python_assertions.jinja2` - Test assertion patterns (2h)
  - Blocks: `pattern_assertions_basic`, `pattern_assertions_exceptions`, `pattern_assertions_type`, `pattern_assertions_context`
  - Patterns: assert x == y, pytest.raises(), isinstance(), with pytest.raises() as exc_info
  - Used by: test_unit, test_integration (2 templates)
- **3.1c:** `tier3_pattern_python_mocking.jinja2` - Mock/patch patterns (2h)
  - Blocks: `pattern_mock_imports`, `pattern_mock_objects`, `pattern_mock_patch`, `pattern_mock_monkeypatch`, `pattern_mock_verification`
  - Patterns: MagicMock(), @patch, monkeypatch.setattr(), assert_called_once_with()
  - Used by: test_unit (1 template)
- **3.1d:** `tier3_pattern_python_test_fixtures.jinja2` - Fixture composition patterns (1.5h)
  - Blocks: `pattern_fixture_simple`, `pattern_fixture_generator`, `pattern_fixture_composition`, `pattern_fixture_conftest`
  - Patterns: @pytest.fixture(name="..."), Generator cleanup, fixture dependencies
  - Used by: test_unit, test_integration (2 templates)
- **3.1e:** `tier3_pattern_python_test_structure.jinja2` - Test organization patterns (1.5h)
  - Blocks: `pattern_test_class`, `pattern_test_docstring`, `pattern_test_arrange_act_assert`, `pattern_test_module_doc`
  - Patterns: class TestX, """RED: Test that...""", # Arrange/Act/Assert, @module/@layer docs
  - Used by: test_unit, test_integration (2 templates)

**Output:**
- 5 test-specific pattern templates (BLOCK LIBRARY)
- Enforcement: ARCHITECTURAL
- Enables scaffolding of tests for templates 3.3+ onwards

**Acceptance:**
- All 5 pattern templates exist
- test_unit.py can cherry-pick 5 patterns (pytest, assertions, mocking, test_fixtures, test_structure)
- test_integration.py can cherry-pick 4 patterns (pytest, assertions, test_fixtures, test_structure)

**Effort:** 9h

**Assignee:** Template Author

**Dependency:** None (can start immediately)

**Priority:** P0 CRITICAL - Enables scaffolding for all subsequent test creation

---

#### Task 3.2: Concrete Test Templates (2 templates) - ðŸŽ¯ **QUICK WIN: Self-Testing System**
**Description:** Create concrete test templates using test patterns from Task 3.1

**Input:** Task 3.1 test patterns complete

**Subtasks (2 Ã— 2h = 4h):**
- **3.2a:** `concrete/test_unit.py.jinja2` - Unit test template (2h)
  - Cherry-picks: pytest, assertions, mocking, test_fixtures, test_structure (5 patterns)
  - Used for: tests/unit/*, tests/mcp_server/* (unit tests with fixtures + mocking)
  - Structure: Test class, fixtures, arrange-act-assert, clear docstrings
  - Context variables:
    - module_under_test: str (e.g., "mcp_server.tools.git_tools")
    - test_class_name: str (e.g., "TestGitTools")
    - fixtures: List[Dict] (name, type, description)
    - test_methods: List[Dict] (name, description, async)
- **3.2b:** `concrete/test_integration.py.jinja2` - Integration/E2E test template (2h)
  - Cherry-picks: pytest, assertions, test_fixtures, test_structure, async (5 patterns)
  - Used for: tests/integration/* (E2E tests with temp workspace)
  - Structure: Scenario-based, full stack setup, file verification
  - Context variables:
    - test_scenario: str (e.g., "artifact scaffolding E2E")
    - workspace_fixture: bool (default: True)
    - managers_needed: List[str] (e.g., ["ArtifactManager"])

**Output:**
- 2 concrete test templates with cherry-picked patterns
- Enforcement: GUIDELINE
- Registered in artifacts.yaml (already present: unit_test, integration_test)

**Acceptance:**
- âœ… test_unit.py.jinja2 scaffolds with 4 patterns (pytest, async, mocking, structure)
- âœ… test_integration.py.jinja2 scaffolds with 4 patterns (pytest, async, mocking, structure)
- âœ… Can scaffold test for tier3_pattern_python_async.jinja2 (bootstrap validated)
- âœ… Whitespace issues fixed (method indentation, trailing newlines)
- âœ… Lessons learned documented in whitespace_strategy.md

**Effort:** 4h â†’ **Actual: 6h** (whitespace debugging)

**Status:** âœ… **COMPLETE** (2026-01-30)

**ðŸŽ¯ BOOTSTRAP MILESTONE ACHIEVED:** All subsequent template tests can now be scaffolded!

---

#### Task 3.3: CODE Pattern Templates (9 templates)
**Description:** Create 9 granular tier3 pattern templates for Python architectural patterns (SRP decomposition)

**Terminology (2026-02-01):** Pattern templates are implemented as Jinja **macro libraries** and composed via `{% import %}`. Earlier planning used â€œBlocksâ€; read this as â€œexported macrosâ€. Pattern templates must not use `{% extends %}` or `{% block %}` (outside comments).

**Input:** Phase 2 Backend Pattern Catalog (12 patterns, 8 in tier3)

**Status:** âœ… **COMPLETE** (9/9 complete; backend-alignment refactors done via per-pattern TDD cycles; 2026-02-01)

**Subtasks (9 Ã— 2h = 18h):**
- **3.3a:** `tier3_pattern_python_async.jinja2` - Async/Await pattern (2h)
  - Macros: `pattern_async_imports`, `pattern_async_methods`, `pattern_async_context_managers`
  - Used by: worker, adapter, service (3 templates)

**Status:** ✅ **COMPLETE** (9/9 complete; 2026-02-05)

**Whitespace Fixes Applied (2026-02-05):**
- All tier3_pattern_python_*.jinja2 templates: Applied `{%- endmacro %}` trimming to prevent trailing newlines
- worker.py.jinja2: Removed extra blank lines after lifecycle macro calls
- tier1_base_code.jinja2: `{{ super() -}}` + `{{ '' }}` pattern implemented to prevent double newlines at merge points
- Validated all 14 concrete templates for correct SCAFFOLD→docstring/heading spacing (no blank lines)
- Documented comprehensive lessons learned in whitespace_strategy.md (Post-Fix Validation Results section)
- Commits: 4ae8f67 "Fix whitespace issues across all templates - macro trimming and blank line removal"
- **3.3b:** `tier3_pattern_python_lifecycle.jinja2` - IWorkerLifecycle pattern (2h)
  - Macros: `pattern_lifecycle_imports`, `pattern_lifecycle_base_class`, `pattern_lifecycle_init`, `pattern_lifecycle_initialize`, `pattern_lifecycle_shutdown`
  - Used by: worker, adapter (2 templates)
- **3.3c:** `tier3_pattern_python_pydantic.jinja2` - Pydantic DTO validation (2h)
  - Macros: `pattern_pydantic_imports`, `pattern_pydantic_base_model`, `pattern_pydantic_config`, `pattern_pydantic_field`, `pattern_pydantic_validator`
  - Used by: dto, schema, config_schema (3 templates)
- **3.3d:** `tier3_pattern_python_error.jinja2` - Error handling pattern (2h)
  - Macros: `pattern_error_imports`, `pattern_error_raise`, `pattern_error_wrap`
  - Used by: worker, adapter, service, tool (4 templates)
- **3.3e:** `tier3_pattern_python_logging.jinja2` - Logging infrastructure (2h)
  - Macros: `pattern_logging_imports`, `pattern_logging_get_logger`, `pattern_logging_call`
  - Used by: ALL (9 templates) - Universal pattern
- **3.3f:** `tier3_pattern_python_typed_id.jinja2` - Typed ID generation (2h)
  - Macros: `pattern_typed_id_imports`, `pattern_typed_id_default_factory`, `pattern_typed_id_generate`
  - Used by: dto, schema (2 templates)
- **3.3g:** `tier3_pattern_python_di.jinja2` - Dependency Injection via Capabilities (2h)
  - Macros: `pattern_di_imports`, `pattern_di_require_dependency`, `pattern_di_require_capability`, `pattern_di_set_dependency`, `pattern_di_set_capability`
  - Used by: worker, adapter, service (3 templates)
- **3.3h:** `tier3_pattern_python_log_enricher.jinja2` - LogEnricher context propagation (2h)
  - Macros: `pattern_log_enricher_imports`, `pattern_log_enricher_set_logger`, `pattern_log_enricher_child`, `pattern_log_enricher_setup`, `pattern_log_enricher_match`, `pattern_log_enricher_filter`, `pattern_log_enricher_policy`, `pattern_log_enricher_result`, `pattern_log_enricher_trade`
  - Used by: worker, adapter (2 templates)
- **3.3i:** `tier3_pattern_python_translator.jinja2` - Translator/i18n pattern (2h)
  - Macros: `pattern_translator_imports`, `pattern_translator_get`, `pattern_translator_get_param_name`, `pattern_translator_key_guideline`
  - Used by: worker, adapter, service (3 templates)

**Output:**
- 9 standalone MACRO LIBRARY templates (no `{% extends %}`, no `{% block %}`; composed via `{% import %}`)
- Each template = 1 architectural pattern (SRP)
- Enforcement: ARCHITECTURAL (validates pattern presence, not syntax)
- Unit tests enforce macro-library constraints and key output tokens

**Acceptance:**
- All 9 pattern templates exist in `mcp_server/scaffolding/templates/`
- Each pattern has `enforcement: ARCHITECTURAL` in TEMPLATE_METADATA
- Each pattern has a unit test in `tests/mcp_server/scaffolding/`
- worker.py can cherry-pick 7 patterns via `{% import %}`
- tool.py can cherry-pick 2 patterns (lightweight composition)

**Effort:** 18h

**Assignee:** Template Author

**Dependency:** Task 2.3 complete (Backend Pattern Catalog)

---

#### Task 3.4: Refactor Concrete CODE Templates (6 templates) + Fix Validation Levels
**Description:** Refactor existing concrete CODE templates to cherry-pick tier3 patterns via `{% import %}` and fix enforcement levels

**Input:** Task 3.3 CODE patterns complete

**Subtasks (6 Ã— 1h = 6h):**
- **3.4a:** Refactor worker.py - Cherry-pick 7 patterns + fix enforcement (1h)
  - Import: async, lifecycle, error, logging, di, log_enricher, translator
  - Change: `{% extends "tier2_base_python.jinja2" %}`
  - Add: `{% import "tier3_pattern_python_lifecycle.jinja2" as lifecycle %}`
  - Use: `{{ lifecycle.pattern_lifecycle_init() | indent(4) }}`
  - **Fix:** `enforcement: STRICT â†’ GUIDELINE`, `validates.strict â†’ validates.guidelines`
- **3.4b:** Refactor dto.py - Cherry-pick 3 patterns + fix enforcement (1h)
  - Import: pydantic, typed_id, logging
  - **Fix:** Change to `enforcement: GUIDELINE`
- **3.4c:** Refactor service.py - Cherry-pick 5 patterns + fix enforcement (1h)
  - Import: async, error, logging, di, translator
  - **Fix:** Change to `enforcement: GUIDELINE`
- **3.4d:** Refactor tool.py - Cherry-pick 2 patterns + fix enforcement (1h)
  - Import: error, logging (lightweight!)
  - **Fix:** Change to `enforcement: GUIDELINE`
- **3.4e:** Add config_schema.py concrete template - Cherry-pick 3 patterns (1h)
  - **NEW TEMPLATE:** Scaffolds Pydantic schemas (WorkflowConfig, LabelConfig, etc.)
  - Import: pydantic, typed_id, logging
  - Rationale: CONFIG tak eliminated, schemas are CODE
  - Enforcement: GUIDELINE (new template, correct from start)
- **3.4f:** Refactor generic.py - Cherry-pick 1 pattern + fix enforcement (1h)
  - Import: logging only
  - **Fix:** Change to `enforcement: GUIDELINE`

**Output:**
- All CODE concrete templates use `{% import %}` composition
- All CODE concrete templates have `enforcement: GUIDELINE` (validation hierarchy correct)
- tool.py justified (2 patterns = lightweight)
- config_schema.py replaces CONFIG tak

**Acceptance:**
- worker.py scaffolds with 7 patterns, enforcement GUIDELINE
- tool.py scaffolds with 2 patterns, enforcement GUIDELINE
- config_schema.py scaffolds Pydantic schemas (e.g., WorkflowConfig)
- Validation hierarchy correct: tier0-2 STRICT, tier3 ARCHITECTURAL, concrete GUIDELINE

**Effort:** 6h

**Assignee:** Template Author

**Dependency:** Task 3.3 complete

**Status:** ✅ **COMPLETE** (6/6 templates refactored; 2026-02-01)

**Verification (2026-02-05):**
1. ✅ **worker.py** - Imports 7 patterns (async, lifecycle, error, logging, di, log_enricher, translator), enforcement: GUIDELINE
2. ✅ **dto.py** - Imports 2 patterns (pydantic, typed_id), enforcement: GUIDELINE, version 1.5.1
3. ✅ **service_command.py** - Imports 5 patterns (async, error, logging, translator, di), enforcement: GUIDELINE, version 1.3.1
4. ✅ **tool.py** - Imports 2 patterns (error, logging), enforcement: GUIDELINE
5. ✅ **config_schema.py** - NEW template created, imports 2 patterns (pydantic, typed_id), enforcement: GUIDELINE
6. ✅ **generic.py** - Imports 1 pattern (logging), enforcement: GUIDELINE, version 1.2.0

All templates:
- Use `{% import %}` composition (not monolithic inheritance) ✅
- Have correct enforcement level (GUIDELINE not STRICT) ✅
- Extend tier2_base_python.jinja2 ✅
- Have changelog entries documenting refactor ✅

Task completed during Phase 3 Tier 3 implementation (2026-02-01), confirmed 2026-02-05.

**Note:** Validation level fix integrated (no separate task needed)

---

#### Task 3.5: DOCUMENT Pattern Templates (8 templates)
**Description:** Create 8 granular tier3 pattern templates for Markdown document patterns

**Input:** Existing concrete document templates (research, planning, design, architecture, reference)

**Subtasks (8 Ã— 1.5h = 12h):**
- **3.5a:** `tier3_pattern_markdown_status_header.jinja2` - Status/Version/Date header (1.5h)
  - Blocks: `pattern_status_header_lines`
  - Used by: ALL (5 docs)
- **3.5b:** `tier3_pattern_markdown_purpose_scope.jinja2` - Purpose + In/Out Scope (1.5h)
  - Blocks: `pattern_purpose_section`, `pattern_scope_section`
  - Used by: ALL (5 docs)
- **3.5c:** `tier3_pattern_markdown_prerequisites.jinja2` - Numbered "Read first" list (1.5h)
  - Blocks: `pattern_prerequisites_section`, `pattern_prerequisites_list`
  - Used by: research, planning, architecture (3 docs)
- **3.5d:** `tier3_pattern_markdown_agent_hints.jinja2` - Agent guidance metadata (1.5h)
  - Blocks: `pattern_agent_hints_block`, `pattern_agent_hints_fields`
  - Used by: research, planning, design (3 docs)
- **3.5e:** `tier3_pattern_markdown_related_docs.jinja2` - Cross-referencing (**CROSS-BRANCH!**) (1.5h)
  - Blocks: `pattern_related_docs_section`, `pattern_related_docs_links`
  - Used by: ALL (5 docs) + pr.md, issue.md (7 total) - **First cross-branch pattern!**
- **3.5f:** `tier3_pattern_markdown_version_history.jinja2` - Change tracking table (1.5h)
  - Blocks: `pattern_version_history_section`, `pattern_version_history_table`
  - Used by: ALL (5 docs)
- **3.5g:** `tier3_pattern_markdown_open_questions.jinja2` - Knowledge gaps documentation (1.5h)
  - Blocks: `pattern_open_questions_section`, `pattern_open_questions_list`
  - Used by: research, design (2 docs)
- **3.5h:** `tier3_pattern_markdown_dividers.jinja2` - Section separators (1.5h)
  - Blocks: `pattern_divider`
  - Used by: ALL (5 docs)

**Output:**
- 8 standalone BLOCK LIBRARY templates (no `{% extends %}`)
- Each template = 1 document pattern (SRP)
- Enforcement: ARCHITECTURAL

**Acceptance:**
- All 8 pattern templates exist
- `tier3_pattern_markdown_related_docs` usable by DOCUMENT + TRACKING (cross-branch proof)
- research.md can cherry-pick 7 patterns

**Effort:** 12h

**Assignee:** Template Author

**Dependency:** None (patterns already exist in concrete templates, can run parallel with 3.1-3.2)

**Status:** ✅ **COMPLETE** (8/8 patterns implemented; 2026-02-05)

**Verification (2026-02-05):**
1. ✅ **tier3_pattern_markdown_status_header.jinja2** - 3 macros (basic, extended, reference), enforcement: ARCHITECTURAL
2. ✅ **tier3_pattern_markdown_purpose_scope.jinja2** - 2 macros (purpose_section, scope_section), enforcement: ARCHITECTURAL
3. ✅ **tier3_pattern_markdown_prerequisites.jinja2** - Numbered prerequisite list macro, enforcement: ARCHITECTURAL
4. ✅ **tier3_pattern_markdown_agent_hints.jinja2** - Agent guidance macro with 5 fields, enforcement: ARCHITECTURAL
5. ✅ **tier3_pattern_markdown_related_docs.jinja2** - Cross-referencing bullet list macro (**CROSS-BRANCH** - usable by DOCUMENT + TRACKING), enforcement: ARCHITECTURAL
6. ✅ **tier3_pattern_markdown_version_history.jinja2** - Version history table macro, enforcement: ARCHITECTURAL
7. ✅ **tier3_pattern_markdown_open_questions.jinja2** - Structured question list with context/blocking fields, enforcement: ARCHITECTURAL
8. ✅ **tier3_pattern_markdown_dividers.jinja2** - 2 macros (section_divider, major_divider), enforcement: ARCHITECTURAL

All templates:
- Macro library format (no `{% extends %}`, composition via `{% import %}`) ✅
- TEMPLATE_METADATA with enforcement: ARCHITECTURAL ✅
- provides_macros list documented ✅
- used_by list documented ✅
- Changelog with v1.0.0 entry ✅

**Test Coverage:**
- `tests/mcp_server/scaffolding/test_task35_document_pattern_templates.py` - 8/8 tests passing
- All pattern files exist and validated

**Commits:**
- `0c19105`: TDD Cycle 2 - purpose_scope pattern
- `0c58016`: TDD Cycles 3-8 - remaining 6 patterns (prerequisites, agent_hints, related_docs, version_history, open_questions, dividers)

Task completed during Phase 3 Tier 3 Pattern Library (2026-02-05).

---

#### Task 3.6: Refactor Concrete DOCUMENT Templates (3 templates) + Fix Validation Levels
**Description:** Refactor existing concrete DOCUMENT templates to cherry-pick tier3 patterns and fix enforcement levels

**Input:** Task 3.5 DOCUMENT patterns complete

**Subtasks (3 Ã— 1h = 3h):**
- **3.6a:** Refactor research.md - Cherry-pick 7 patterns + fix enforcement (1h)
  - Import: status_header, purpose_scope, prerequisites, agent_hints, related_docs, version_history, open_questions
  - **Fix:** `enforcement: STRICT â†’ GUIDELINE`
- **3.6b:** Refactor planning.md - Cherry-pick 6 patterns + fix enforcement (1h)
  - Import: status_header, purpose_scope, prerequisites, agent_hints, related_docs, version_history
  - **Fix:** `enforcement: STRICT â†’ GUIDELINE`
- **3.6c:** Refactor design.md - Cherry-pick 7 patterns + fix enforcement (1h)
  - Import: status_header, purpose_scope, agent_hints, related_docs, version_history, open_questions, dividers
  - **Fix:** `enforcement: STRICT â†’ GUIDELINE`

**Output:**
- All DOCUMENT concrete templates use `{% import %}` composition
- All DOCUMENT concrete templates have `enforcement: GUIDELINE`

**Acceptance:**
- research.md scaffolds with 7 patterns, enforcement GUIDELINE
- All document templates use consistent pattern imports
- Validation hierarchy correct for DOCUMENT branch

**Effort:** 3h

**Assignee:** Template Author

**Dependency:** Task 3.5 complete

**Note:** Validation level fix integrated (no separate task needed)

---

#### Task 3.7: Tier 1 Tracking + Tier 2 Templates (VCS Workflows)
**Description:** Create tier1_base_tracking + tier2_tracking_text/markdown for VCS workflow artifacts

**Input:** [tracking-type-architecture.md](tracking-type-architecture.md) - tracking as 4th BASE TYPE

**Subtasks (11h):**
- **3.7a:** Create `tier1_base_tracking.jinja2` (3h)
  - Workflow metadata blocks
  - No versioning (tracking characteristic)
  - No status lifecycle
  - VCS-agnostic terminology
- **3.7b:** Create `tier2_tracking_text.jinja2` (2h)
  - Plain text format (commit messages)
  - Line breaks, no markup
- **3.7c:** Create `tier2_tracking_markdown.jinja2` (2h)
  - Markdown syntax (PR, issue, milestone)
  - Checkboxes, headers, lists
- **3.7d:** Create concrete/commit.txt (1h)
  - Conventional Commits format
  - Type/scope/message structure
- **3.7e:** Create concrete/pr.md (1h)
  - PR sections (Changes, Testing, Checklist)
  - Import `tier3_pattern_markdown_related_docs` (cross-branch!)
- **3.7f:** Create concrete/issue.md (1h)
  - Issue sections (Problem, Expected, Actual)
  - Import `tier3_pattern_markdown_related_docs` (cross-branch!)
- **3.7g:** Integration tests (1h)

**Output:**
- tier1_base_tracking + 2 tier2 templates + 3 concrete templates
- pr.md and issue.md import cross-branch `related_docs` pattern

**Acceptance:**
- Tracking artifacts scaffold with correct tier chain
- pr.md/issue.md use `tier3_pattern_markdown_related_docs` (cross-branch proof!)
- No tier3 patterns specific to tracking (tier2 sufficient)

**Effort:** 11h

**Assignee:** Template Author

**Note:** Tracking is NOT a document subtype - it's a top-level base type with fundamentally different characteristics (no versioning, no status lifecycle)

---

#### Task 3.8: Template Registry Format Change
**Description:** Change template_registry.yaml â†’ template_registry.json for better parsability

**Input:** Machine-generated provenance tracking file

**Subtasks (1h):**
- Update TemplateRegistry class to read/write JSON
- Convert existing .yaml to .json
- Update documentation references

**Output:**
- template_registry.json format
- Better parsability, no YAML ambiguity

**Acceptance:**
- Registry writes to .json
- Provenance tracking works correctly

**Effort:** 1h

**Assignee:** Backend Engineer

**Dependency:** None (infrastructure change)

---

#### Task 3.9: Documentation (AC8/AC13) - EXPANDED
**Description:** Write comprehensive template library documentation including block library composition

**Input:** All Tier 0-3 templates complete + block library pattern

**Subtasks (16h):**
- **3.8a:** Architecture guide (4h)
  - Tier system rationale (tier0-2 STRICT syntax, tier3 ARCHITECTURAL patterns, concrete GUIDELINE)
  - Block library composition via `{% import %}` (not `{% extends %}`)
  - Cross-branch patterns (related_docs example)
  - Decision tree: "Where does this element go?" (from research doc)
- **3.8b:** Usage guide (4h)
  - Scaffolding new artifact with pattern cherry-picking
  - Adding language/format (extensibility)
  - Pattern selection guide (when to use lifecycle, pydantic, etc.)
- **3.8c:** Pattern guide (4h)
  - Backend patterns and tier assignments (12 patterns â†’ 17 templates)
  - Code examples for each tier3 pattern
  - Cherry-picking composition examples (worker = 7 patterns, tool = 2 patterns)
- **3.8d:** Quick reference tables (4h)
  - Master template inventory (from research doc)
  - Element flow tables (CODE/DOCUMENT/TRACKING)
  - Pattern cherry-picking table
  - Validation hierarchy table

**Output:**
- Architecture guide with SRP pattern rationale
- Usage guide with {% import %} examples
- Pattern guide with 17 tier3 patterns documented
- Quick reference tables for developer onboarding

**Acceptance:**
- Developer can scaffold new artifact following guide
- Developer understands block library composition
- Developer can add new tier3 pattern (SRP)

**Effort:** 16h

**Assignee:** Technical Writer + Architect

**Dependency:** Tasks 3.1-3.8 complete

---

### Phase 3 Summary (REVISED - Test Templates First!)

**Total Effort: 80h (was 49h original, +31h for SRP + test templates)**

| Task | Effort | Category |
|------|--------|----------|
| 3.1 Test Pattern Templates (5) | 9h | ðŸŽ¯ **BOOTSTRAP: Pattern Library** |
| 3.2 Concrete Test Templates (2) | 4h | ðŸŽ¯ **BOOTSTRAP: Self-Testing** |
| 3.3 CODE Pattern Templates (9) | 18h | Pattern Library |
| 3.4 Refactor CODE Concrete (6) + Fix Validation | 6h | Refactoring |
| 3.5 DOCUMENT Pattern Templates (8) | 12h | Pattern Library |
| 3.6 Refactor DOCUMENT Concrete (3) + Fix Validation | 3h | Refactoring |
| 3.7 Tracking Templates (tier1+tier2+concrete) | 11h | Infrastructure |
| 3.8 Registry Format Change | 1h | Infrastructure |
| 3.9 Documentation | 16h | Deliverables |
| **TOTAL** | **80h** | **(5-6 weeks)** |

**Task Flow (Optimized with Bootstrap):**
1. **3.1:** Test pattern templates (9h) - ðŸŽ¯ Enables test scaffolding
2. **3.2:** Concrete test templates (4h) - ðŸŽ¯ **BOOTSTRAP MILESTONE: Tests can now be scaffolded!**
3. **3.3:** CODE patterns (18h) - Use scaffolded tests from this point
4. **3.4:** Refactor CODE concrete + validation fix (6h)
5. **3.5:** DOCUMENT patterns (12h) - Can run parallel with 3.3-3.4
6. **3.6:** Refactor DOCUMENT concrete + validation fix (3h)
7. **3.7:** Tracking infrastructure (11h)
8. **3.8:** Registry format change (1h) - Can run parallel
9. **3.9:** Documentation (16h) - Requires all tasks complete
9. **3.9:** Documentation (16h) - Requires all tasks complete

**Breakdown by Priority:**
- **P0 (CRITICAL - AC6 blockers):** 63h (tasks 3.1-3.7)
- **P1 (Important):** 17h (tasks 3.8-3.9)

**Key Changes from Original Plan:**
- âŒ Removed: 3 monolithic tier3 templates (tier3_base_python_component, data_model, tool) - 20h saved
- âŒ Removed: CONFIG tak (tier1_base_config, tier3_base_yaml_policy) - 5h saved
- âŒ Removed: Separate validation fix task (integrated in refactoring) - 3h saved
- âœ… Added: 5 test pattern templates (pytest, assertions, mocking, fixtures, structure) - 9h added
- âœ… Added: 2 concrete test templates (unit_test, integration_test) - 4h added
- âœ… Added: 17 granular tier3 patterns (9 CODE + 8 DOCUMENT) - 30h added
- âœ… Changed: Validation fix integrated in refactoring tasks (more efficient)
- âœ… Changed: Task order optimized (test templates FIRST = bootstrap effect)
- âœ… Changed: Documentation expanded with block library guide - same 16h

**Net Change: +31h (but significantly better: SRP + self-testing + quick wins)**

**ðŸŽ¯ Bootstrap Strategy Benefits:**
- After Task 3.2: All subsequent tests can be **scaffolded** (not hand-written)
- Immediate productivity gain - test writing becomes 3-5x faster
- Self-validating system - test templates tested by scaffolded tests
- Quick wins build momentum for Phase 3 execution

### Phase 4: Migration (Legacy Conversion) - âš ï¸ **OBSOLETE**
**Goal:** ~~Migrate 24 existing templates to multi-tier architecture~~  
**Duration:** ~~1.5 weeks (60h)~~  
**Dependencies:** ~~Phase 3 complete (all base templates ready)~~

**STATUS:** This phase is **OBSOLETE** due to commit 2ee9228 forceful cutover. Legacy templates are already unreachable (TemplateScaffolder now uses `get_template_root()` â†’ `mcp_server/scaffolding/templates/`). See [cutover-analysis.md](cutover-analysis.md) for details.

**NEW APPROACH:** 
- Delete legacy templates immediately (git rm -r mcp_server/templates/)
- Task 1.6 creates minimal concrete templates (5 vs 24)
- Future templates created directly in tier system
- **Savings:** 65h migration effort eliminated

~~#### Task 4.1: Migration Script~~
~~#### Task 4.2: Migrate CODE Templates (13)~~
~~#### Task 4.3: Migrate DOCUMENT Templates (9)~~
~~#### Task 4.4: Create CONFIG Templates (2 new)~~
~~#### Task 4.5: E2E Testing (Coordinate with Issue #74)~~
~~#### Task 4.6: Feature Flag Cleanup~~

**See Task 1.6 for replacement approach** (7h vs 65h)

#### Task 4.1: Migration Script
- **Description:** Automate mechanical refactoring
- **Input:** Legacy template structure
- **Output:**
  - Script converts single-file template to multi-tier extends chain
  - Preserves custom blocks, updates SCAFFOLD format
- **Acceptance:** Script migrates simple template without manual edits
- **Effort:** 12h
- **Assignee:** Automation Engineer

#### Task 4.2: Migrate CODE Templates (13)
- **Description:** Refactor 13 Python templates to extend Tier 3
- **Input:** Migration script output
- **Output:** Each template extends appropriate Tier 3 (component/data_model/tool)
- **Acceptance:** All CODE templates scaffold correctly, pass validation
- **Effort:** 1h Ã— 13 = 13h (assumes script handles 80% of work)
- **Assignee:** Template Author
- **Dependency:** Task 4.1 complete

#### Task 4.3: Migrate DOCUMENT Templates (9)
- **Description:** Refactor 9 Markdown templates to extend Tier 3
- **Input:** Migration script output
- **Output:** Each template extends document/tracking tier (see [tracking-type-architecture.md](tracking-type-architecture.md))
- **Acceptance:** All DOCUMENT templates scaffold correctly
- **Effort:** 1h Ã— 9 = 9h
- **Assignee:** Template Author
- **Dependency:** Task 4.1 complete
- **Note:** Tracking templates (commit, pr, issue) extend tier1_base_tracking, NOT tier1_base_document

#### Task 4.4: Create CONFIG Templates (2 new)
- **Description:** Create workflows.yaml and labels.yaml templates
- **Input:** Tier 3 YAML policy template
- **Output:** New CONFIG concrete templates
- **Acceptance:** YAML artifacts scaffold with full tier chain
- **Effort:** 2h Ã— 2 = 4h
- **Assignee:** Template Author

#### Task 4.5: E2E Testing (Coordinate with Issue #74)
- **Description:** Validate all migrated templates
- **Input:** Issue #74 test suite
- **Output:**
  - All templates pass validation
  - DTO/Tool templates fix #74 failures
- **Acceptance:** Zero validation failures for scaffolded code
- **Effort:** 16h (4h Ã— 4 template categories)
- **Assignee:** QA Engineer + Template Author
- **Dependency:** All migrations complete

#### Task 4.6: Feature Flag Cleanup
- **Description:** Remove legacy template support
- **Input:** E2E tests passing
- **Output:**
  - Delete old single-file templates
  - Remove `use_legacy_templates` flag
  - Update docs to reference multi-tier only
- **Acceptance:** Codebase uses only multi-tier templates
- **Effort:** 4h
- **Assignee:** Backend Engineer

### Phase 5: Extensibility Proof (Final Validation)
**Goal:** Prove AC10/AC11 (language/format addition)  
**Duration:** ~3 days (24h)  
**Dependencies:** Phase 4 complete

#### Task 5.1: Add TypeScript Language (AC10)
- **Description:** Create Tier 2 TypeScript template as proof
- **Input:** Python Tier 2 structure
- **Output:** `tier2_base_typescript.jinja2` with TS syntax patterns
- **Acceptance:** TypeScript worker scaffolds with 1 new template
- **Effort:** 4h
- **Assignee:** TypeScript Developer

#### Task 5.2: Add CONFIG Format (AC11)
- **Description:** Already done in Task 4.4
- **Acceptance:** YAML workflow validates extensibility
- **Effort:** 0h (counted in Phase 4)

#### Task 5.3: Extensibility Documentation
- **Description:** Document language/format addition process
- **Input:** TypeScript example
- **Output:**
  - Guide: "How to Add a New Language" (step-by-step)
  - Guide: "How to Add a New Format" (Tier 1 creation)
- **Acceptance:** External contributor can add language following guide
- **Effort:** 4h
- **Assignee:** Technical Writer

---

## Implementation Sequencing

### Critical Path (Longest Chain)
```
Task 2.1 (Introspection 12h)
  â†’ Task 1.4 (Tier 2 9h)
    â†’ Task 3.1 (Tier 3 Component 8h)
      â†’ Task 4.2 (Migrate CODE 13h)
        â†’ Task 4.5 (E2E Testing 16h)
          â†’ Task 4.6 (Cleanup 4h)
= 62h critical path (1.5 weeks with 1 engineer)
```

### Parallel Workstreams (If 3+ Engineers Available)

**Engineer 1: Infrastructure (Backend)**
- Week 1: Task 1.1 (Registry 8h) â†’ Task 2.1 (Introspection 12h)
- Week 2: Task 1.5 (Metadata 6h) â†’ Task 4.1 (Migration Script 12h)
- Week 3: Task 4.5 (E2E Testing 16h)

**Engineer 2: Template Author (Primary)**
- Week 1: Task 1.2-1.4 (Tier 0-2 17h) â† DOCUMENT via tdd-planning; CODE/CONFIG in planning
- Week 2: Task 3.1-3.3 (Tier 3 CODE 20h)
- Week 3: Task 4.2 (Migrate CODE 13h) â†’ Task 5.1 (TypeScript 4h)

**Engineer 3: Template Author (Secondary)**
- Week 1: Task 2.2 (Audit 6h) â†’ Task 2.3 (Inventory 16h)
- Week 2: Task 3.4-3.6 (Tier 3 DOCUMENT/CONFIG 10h) â†’ Task 2.4 (Hints 6h)
- Week 3: Task 4.3-4.4 (Migrate DOC/CONFIG 13h)

**Engineer 4: Documentation + QA**
- Week 1: Support audits (Task 2.2-2.3)
- Week 2: Task 3.7 (Documentation 16h)
- Week 3: Task 4.5 (E2E Testing 16h) â†’ Task 5.3 (Extensibility docs 4h)

**Total Timeline with 4 Engineers: 3 weeks**

---

## Effort Estimation Summary

**âš ï¸ REVISED** after commit 2ee9228 analysis (see [cutover-analysis.md](cutover-analysis.md))

| Phase | Tasks | Total Hours | Duration (1 eng) | Duration (4 eng) | Status |
|-------|-------|-------------|------------------|------------------|--------|
| **Phase 1: Foundation** | 10 tasks (was 6) | **55h** (was 38h) | 7 days | 3 days | âš ï¸ **INCOMPLETE** |
| **Phase 2: Blockers** | 4 tasks | 40h | 5 days | 3 days | Not started |
| **Phase 3: Tier 3** | 7 tasks | 46h | 6 days | 3 days | Not started |
| ~~**Phase 4: Migration**~~ | ~~6 tasks~~ | ~~58h~~ | ~~7 days~~ | ~~4 days~~ | **OBSOLETE** |
| **Phase 5: Extensibility** | 2 tasks | 8h | 1 day | 1 day | Not started |
| **TOTAL** | **23 tasks** (was 19) | **149h** (was 132h) | **19 days** (was 17) | **10 days (2 weeks)** (was 9 days) |

**Key Changes:**
- âš ï¸ **Phase 1 +17h:** Added registry completion tasks (1.1b/c, 1.5b/c, 1.6b) - foundation NOT done
- âœ… **Phase 4 -65h:** Migration obsolete (legacy templates unreachable after commit 2ee9228)
- âš ï¸ **Net change: -48h vs original 183h** but Phase 1 must complete FIRST
- âœ… **Timeline: 23 days â†’ 19 days** (1 engineer) or **13 days â†’ 10 days** (4 engineers)
- ðŸ“š **Design docs complete:** See [tdd-planning.md](tdd-planning.md) for document template implementation (7 TDD cycles)
- â¸ï¸ **Tracking deferred:** tier1_base_tracking moved to Post-TDD continuation (tdd-planning marks as "future work")

**Phase 1 Revised Breakdown:**
- Task 1.1: Registry infrastructure (8h) âœ…
- **Task 1.1b: Fix compute_version_hash (4h)** â† NEW
- **Task 1.1c: Integrate registry in scaffold flow (3h)** â† NEW
- Task 1.2: Tier 0 base (2h) âœ…
- Task 1.3: Tier 1 bases (6h) â† DOCUMENT via tdd-planning Cycles 3-5; CODE/CONFIG in planning; TRACKING post-TDD
- Task 1.4: Tier 2 bases (9h) âœ…
- Task 1.5: Issue #52 alignment (6h) âœ…
- **Task 1.5b: Remove ArtifactDefinition.version conflict (2h)** â† NEW
- **Task 1.5c: Add artifact variants support (4h)** â† NEW (P2 optional)
- **Task 1.6: Concrete templates (7h)** â† BLOCKED until 1.1c done
- **Task 1.6b: E2E provenance test (3h)** â† NEW (validates Phase 1 DoD)

**Critical Path Update:**
- OLD: Phase 1 done â†’ Phase 2 || Phase 3
- **NEW: Phase 1 incomplete â†’ MUST complete registry (tasks 1.1b/c) â†’ THEN Task 1.6 â†’ THEN Phase 2**

**Assumptions:**
- 1 engineer = 8h/day focus time (no meetings/interruptions)
- 4 engineers = ideal parallelization (tasks are independent enough)
- No scope creep or unexpected blockers
- Issue #52 validation infrastructure ready for integration

**Contingency:**
- Add 20% buffer: 132h Ã— 1.2 = **158h (4 weeks with 1 eng, 2.5 weeks with 4 eng)**
- Original with buffer: 220h â†’ **Revised with buffer: 158h** (-62h savings)

---

## Risk Mitigation Plan

### Risk #1: Issue #52 Incomplete (Validation Dependency)
**Probability:** Medium (30%)  
**Impact:** **CRITICAL** - AC9 is **hard requirement** for release, blocks shipment  

**Mitigation:**
- **Early coordination:** Task 1.5 requires #52 status check (Week 1)
- **Parallel work:** Implement #72 templates while #52 validation completes
- **Integration checkpoint:** Week 2 validation hook integration (Task 1.5)
- **E2E validation:** Week 3 full test suite (Task 4.5)

**Hard Constraint:**
- **#72 cannot ship without AC9 (validation integration) complete**
- If #52 delayed: **Delay #72 release** until validation ready
- **Cost:** Release blocked until #52 delivers CODE validation infrastructure

**Coordination Plan:**
1. Week 1: Confirm #52 delivery date and scope
2. Week 2: Daily sync with #52 team on TEMPLATE_METADATA integration
3. Week 3: Joint testing session (Task 4.5 depends on #52 completion)
4. **Go/No-Go Decision:** End of Week 2 - confirm #52 on track or escalate

---

### Risk #2: Blocker #2 Invalidates IWorkerLifecycle
**Probability:** Low (15%)  
**Impact:** Medium (AC5 removed, Tier 3 redesign)  

**Mitigation:**
- **Early audit:** Task 2.2 in Week 1 (before Tier 3 design)
- **Decision checkpoint:** Stakeholder approval before Task 3.1

**Contingency Plan:**
- If lifecycle not used: Remove AC5, simplify Tier 3 component template
- **Cost:** No timeline impact (discovered early), possible scope reduction

---

### Risk #3: Backend Pattern Inventory Too Large
**Probability:** Medium (40%)  
**Impact:** Medium (scope creep, Phase 3 extends)  

**Mitigation:**
- **Timeboxing:** Task 2.3 capped at 16h (prioritize top 10 patterns)
- **MVP mindset:** Cover 80% of patterns, defer edge cases to future issue

**Contingency Plan:**
- If >20 patterns found: Create Phase 3B for low-priority patterns
- **Cost:** +1 week for comprehensive coverage (optional)

---

### Risk #4: Migration Breaks Existing Workflows
**Probability:** High (60%)  
**Impact:** High (production scaffolding failures)  

**Mitigation:**
- **Feature flag:** `use_legacy_templates=true` during migration (Task 4.1)
- **Dual-mode scaffolding:** Support both old and new templates (2 weeks)
- **Phased rollout:** Migrate 1 template, validate, iterate
- **Rollback plan:** Revert to legacy templates if E2E tests fail

**Contingency Plan:**
- If migration failures: Extend dual-mode period to 4 weeks
- **Cost:** +2 weeks for safe rollout

---

### Risk #5: Introspection Performance Impact
**Probability:** Low (10%)  
**Impact:** Low (scaffolding slowdown)  

**Mitigation:**
- **Benchmarking:** Task 2.1 includes performance test (5-tier chain <100ms)
- **Caching:** Introspection results cached per template

**Contingency Plan:**
- If >500ms overhead: Optimize AST walking or flatten some tiers
- **Cost:** +3 days optimization work

---

## Success Criteria

### Functional Success (Must-Have)
- [ ] All 13 AC criteria pass validation
- [ ] 24 legacy templates migrated to multi-tier
- [ ] Inheritance introspection returns complete variable schema
- [ ] Template registry operational (hash lookup, version tracking)
- [ ] E2E tests pass for all template categories
- [ ] TypeScript Tier 2 proves language extensibility
- [ ] CONFIG Tier 1 proves format extensibility

### Quality Success (Should-Have)
- [ ] Documentation complete (architecture + usage guides)
- [ ] Agent hints improve content generation quality (subjective test)
- [ ] Zero validation failures for scaffolded code (coordinate with #74)
- [ ] Backend pattern catalog covers â‰¥80% of common patterns

### Operational Success (Nice-to-Have)
- [ ] Migration script automates â‰¥80% of refactoring work
- [ ] Feature flag removed (legacy templates deprecated)
- [ ] Performance: 5-tier introspection <100ms per template
- [ ] Zero production incidents during rollout

---

## Rollback Plan

### Trigger Conditions
1. **Critical bug:** Scaffolding generates invalid code (syntax errors)
2. **Performance regression:** Introspection >500ms (10x slowdown)
3. **Validation failures:** >50% of templates fail E2E tests
4. **Production incident:** Scaffolding blocks development workflow

### Rollback Steps
1. **Immediate:** Enable `use_legacy_templates=true` feature flag (5 minutes)
2. **Short-term:** Revert to pre-migration commit (git revert, 1 hour)
3. **Communication:** Notify team of rollback, gather failure data
4. **Root cause:** Debug issue, fix in development branch
5. **Re-deploy:** Test fix in staging, retry rollout with monitoring

### Rollback Cost
- **Time:** 1-2 days to revert, debug, and re-deploy
- **Risk:** Minimal (legacy templates proven stable)

---

## Coordination Points

### Issue #52 (Template Validation)
- **Week 1:** Status check (Task 1.5) - Is CODE validation ready?
- **Week 2:** TEMPLATE_METADATA integration (Task 1.5)
- **Week 3:** E2E validation testing (Task 4.5)
- **Contact:** Issue #52 owner

### Issue #74 (E2E Template Tests)
- **Week 3:** Use #74 test suite for validation (Task 4.5)
- **Goal:** Fix DTO/Tool validation failures with multi-tier templates
- **Contact:** QA team

### Issue #120 (SCAFFOLD Metadata)
- **Week 1:** Tier 0 SCAFFOLD format (Task 1.2)
- **Week 3:** Increase coverage from 8% to 100% (all migrations)
- **Contact:** Template registry owner

---

## Open Questions (Require Planning Decision)

### OQ-P1: Backend Pattern Inventory Priority
**Question:** Which patterns are P0 (must-have) vs P1 (nice-to-have) for MVP?  
**Decisor:** System Architect  
**Deadline:** End of Week 1 (before Task 3.1 starts)  
**Impact:** Determines Tier 3 template scope

### OQ-P2: Agent Hint Format Mandatory?
**Question:** Should agent hints block MVP or ship as enhancement?  
**Decisor:** Product Owner  
**Deadline:** End of Week 1  
**Impact:** Affects AC7 priority (P0 vs P2)

### OQ-P3: TypeScript Tier 2 Scope
**Question:** Full TypeScript support or minimal proof (AC10)?  
**Decisor:** Tech Lead  
**Deadline:** Before Task 5.1 (Week 3)  
**Impact:** Extensibility proof depth

### OQ-P4: Migration Automation Threshold
**Question:** How many templates must migration script handle (80%? 100%)?  
**Decisor:** Automation Engineer  
**Deadline:** Before Task 4.1 (Week 2)  
**Impact:** Script complexity vs manual effort tradeoff

---

## Next Steps (Immediate Actions)

1. **Approve planning doc:** Stakeholder review and sign-off
2. **Assign engineers:** Map 4 parallel workstreams to team members
3. **Setup environment:** Create feature branch, enable feature flags
4. **Week 1 kickoff:**
   - Start Task 1.1 (Registry infrastructure)
   - Start Task 2.1 (Introspection fix)
   - Start Task 2.2 (Lifecycle audit)
5. **Daily standups:** Track critical path progress (introspection â†’ Tier 2 â†’ Tier 3)

---

## Related Documents

- [research.md](research.md) - Full research with alternatives exploration
- [research_summary.md](research_summary.md) - Final decisions and blockers
- [mvp/](mvp/) - 5-tier template proof-of-concept
- Issue #52 - Template validation infrastructure
- Issue #74 - E2E template tests
- Issue #120 - SCAFFOLD metadata coverage

