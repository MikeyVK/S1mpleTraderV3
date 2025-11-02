# Documentation Maintenance Guide

## Overview

This guide ensures S1mpleTrader V3 documentation **stays modular, focused, and AI-friendly**. Follow these rules when updating documentation to prevent chaos and bloat.

**Last Updated:** October 2025  
**Document Structure:** Established October 2025 (agent.md 1657→195 lines restructure)

## Core Principles

### 1. Modular Over Monolithic

**Rule:** No single document should exceed **300 lines** (except templates/references with code examples).

**Why:** AI context windows work better with focused documents. Developers can find information faster.

**Action when exceeded:**
```
Document > 300 lines → Split into focused sub-documents + create/update index
```

**Example:** agent.md grew to 1657 lines → Split into architecture/, coding_standards/, reference/, implementation/

### 2. Single Source of Truth

**Rule:** Each concept has **ONE authoritative location**. Link to it, don't duplicate it.

**Why:** Updates in one place propagate everywhere. No conflicting information.

**Action:**
- ✅ Link: `See [TDD_WORKFLOW.md](coding_standards/TDD_WORKFLOW.md) for details`
- ❌ Copy-paste: Same TDD explanation in 5 different files

### 3. Index-Driven Navigation

**Rule:** Every directory with >3 files **must have a README.md index** with:
- Quick links section
- Brief description per document
- Common workflows (when to read what)

**Why:** Developers and AI agents need entry points to find information.

**Example:** [docs/reference/README.md](reference/README.md) - Templates status matrix + workflows

### 4. Iterative Documentation with AI

**Rule:** Documentation is **written incrementally alongside code**, not as afterthought.

**Why:** Fresh context = better docs. Incremental = manageable chunks.

**Workflow:**
1. Write code (TDD cycle)
2. Immediately document new patterns/decisions
3. AI assists with formatting/completion
4. Commit docs with code changes

## Documentation Structure

### Current Layout

```
docs/
├── DOCUMENTATION_MAINTENANCE.md    # ← This file (meta-rules)
├── TODO.md                         # Project roadmap
│
├── architecture/                   # System design (4 files, ~900 lines)
│   ├── README.md                   # Navigation index
│   ├── CORE_PRINCIPLES.md          # 4 fundamental principles
│   ├── ARCHITECTURAL_SHIFTS.md     # 3 critical V2→V3 changes
│   └── POINT_IN_TIME_MODEL.md      # IStrategyCache, DTOs, RunAnchor
│
├── coding_standards/               # Development rules (5 files, ~1500 lines)
│   ├── README.md                   # Navigation index
│   ├── TDD_WORKFLOW.md             # RED→GREEN→REFACTOR cycle
│   ├── QUALITY_GATES.md            # 5 mandatory gates (10/10 required)
│   ├── GIT_WORKFLOW.md             # Branching, commits, merging
│   └── CODE_STYLE.md               # PEP 8, file headers, Pydantic
│
├── implementation/                 # Status tracking (1 file, ~300 lines)
│   └── IMPLEMENTATION_STATUS.md    # Quality metrics dashboard
│
└── reference/                      # Templates & examples (5 files, ~2000 lines)
    ├── README.md                   # Navigation + status matrix
    ├── dtos/
    │   ├── STRATEGY_DTO_TEMPLATE.md     # Copy-paste boilerplate
    │   └── signal.md        # Reference implementation
    ├── testing/
    │   └── DTO_TEST_TEMPLATE.md         # Test boilerplate
    └── platform/
        └── strategy_cache.md            # Service reference
```

**Total:** 15 focused documents, ~5,000 lines (was 1 file, 1,657 lines)

### Directory Ownership

| Directory | Purpose | Max File Size | Update Trigger |
|-----------|---------|---------------|----------------|
| `architecture/` | System design decisions | 300 lines | New architectural pattern |
| `coding_standards/` | Development rules | 300 lines | New quality requirement |
| `implementation/` | Progress tracking | 500 lines | Module completion (tests passing) |
| `reference/` | Templates & examples | 600 lines* | New component type implemented |

*Templates may exceed 300 lines due to code examples - this is acceptable.

## Update Workflows

### Workflow 1: New Feature Implementation

**Trigger:** Implementing new DTO, Worker, Service

**Steps:**

1. **Code First (TDD):**
   ```powershell
   git checkout -b feature/my-new-dto
   # RED → GREEN → REFACTOR (see TDD_WORKFLOW.md)
   ```

2. **Update Implementation Status:**
   ```markdown
   # docs/implementation/IMPLEMENTATION_STATUS.md
   # Add row to relevant table with test count, quality metrics
   ```

3. **Add Reference (if novel pattern):**
   ```markdown
   # docs/reference/{category}/my_component.md
   # Only if this introduces NEW patterns worth documenting
   ```

4. **Update Reference README:**
   ```markdown
   # docs/reference/README.md
   # Add to status matrix if new component type
   ```

5. **Commit Pattern:**
   ```powershell
   git add docs/implementation/IMPLEMENTATION_STATUS.md docs/reference/...
   git commit -m "docs: add MyDTO reference and update status
   
   - Updated implementation status (22/22 tests)
   - Added reference example for new validation pattern"
   ```

**Decision Tree: Do I need reference docs?**
```
Is this a new component type (first Worker, first EventAdapter)?
├─ YES → Create reference/examples/{component}.md
└─ NO → Is this pattern significantly different from existing?
    ├─ YES → Add section to existing reference doc
    └─ NO → Only update IMPLEMENTATION_STATUS.md
```

### Workflow 2: Architectural Decision

**Trigger:** Major design change, new principle, shift in approach

**Steps:**

1. **Document Decision:**
   ```markdown
   # Create docs/architecture/NEW_PATTERN.md
   # OR add section to existing architecture doc
   ```

2. **Update Architecture README:**
   ```markdown
   # docs/architecture/README.md
   # Add quick link and description
   ```

3. **Link from Relevant Docs:**
   ```markdown
   # Update coding_standards/ or reference/ with links to new architecture
   ```

4. **Commit Pattern:**
   ```powershell
   git commit -m "docs: document EventAdapter pattern
   
   - Created EVENTADAPTER_PATTERN.md
   - Updated architecture README with navigation
   - Linked from reference/workers/ examples"
   ```

**Size Check:**
```
New architecture doc > 300 lines?
├─ YES → Split into sub-topics with index
└─ NO → Keep as single focused document
```

### Workflow 3: Coding Standard Change

**Trigger:** New quality rule, tool configuration change, pattern enforcement

**Steps:**

1. **Update Relevant Standard:**
   ```markdown
   # docs/coding_standards/{TDD_WORKFLOW|QUALITY_GATES|GIT_WORKFLOW|CODE_STYLE}.md
   # Add new section or update existing rule
   ```

2. **Update Examples:**
   ```markdown
   # docs/reference/{relevant}/
   # Update templates/examples to reflect new standard
   ```

3. **Update IMPLEMENTATION_STATUS (if affects metrics):**
   ```markdown
   # docs/implementation/IMPLEMENTATION_STATUS.md
   # Add new quality gate or update acceptance criteria
   ```

4. **Commit Pattern:**
   ```powershell
   git commit -m "docs: add import ordering rule to CODE_STYLE
   
   - Added 3-group import pattern (Standard/Third-party/Project)
   - Updated DTO template with import groups
   - Updated quality checklist"
   ```

### Workflow 4: Template Update

**Trigger:** Better pattern discovered, boilerplate improved

**Steps:**

1. **Update Template:**
   ```markdown
   # docs/reference/{dtos|testing|platform}/TEMPLATE.md
   # Improve boilerplate, add better examples
   ```

2. **Update Status Matrix:**
   ```markdown
   # docs/reference/README.md
   # Note template version/update in status matrix
   ```

3. **Create Migration Note (if breaking):**
   ```markdown
   # Add "## Template Updates" section in reference README
   # Document what changed and why
   ```

4. **Commit Pattern:**
   ```powershell
   git commit -m "docs: improve DTO template with causality decision tree
   
   - Added visual decision tree for causality inclusion
   - Updated field ordering examples
   - Added frozen vs mutable guidelines"
   ```

### Workflow 5: Documentation Cleanup

**Trigger:** Monthly maintenance, after major milestone, when docs feel cluttered

**Steps:**

1. **Check File Sizes:**
   ```powershell
   # Find docs > 300 lines
   Get-ChildItem docs -Recurse -Filter "*.md" | Where-Object {
       (Get-Content $_.FullName | Measure-Object -Line).Lines -gt 300
   } | Select-Object Name, @{Name="Lines";Expression={(Get-Content $_.FullName | Measure-Object -Line).Lines}}
   ```

2. **Identify Duplication:**
   ```powershell
   # Search for repeated patterns
   grep -r "TDD workflow" docs/ | wc -l  # If count > 3, consolidate
   ```

3. **Split Oversized Docs:**
   ```markdown
   # If architecture/CORE_PRINCIPLES.md > 300 lines:
   # → Split into CORE_PRINCIPLES.md (overview) + detailed sub-docs
   # → Update architecture/README.md index
   ```

4. **Consolidate Duplicates:**
   ```markdown
   # Replace duplicated content with links
   # Keep ONE authoritative source
   ```

5. **Commit Pattern:**
   ```powershell
   git checkout -b docs/monthly-cleanup
   git commit -m "docs: October 2025 maintenance cleanup
   
   - Split POINT_IN_TIME_MODEL.md (was 450 lines → 3 docs @ 150 lines each)
   - Consolidated TDD workflow duplicates (5 references → 1 source + links)
   - Updated all README indices with new structure"
   git checkout main && git merge docs/monthly-cleanup
   ```

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Copy-Paste Documentation

**Problem:** Same explanation in multiple files → Updates miss some copies → Conflicting info

**Example:**
```markdown
# ❌ BAD - TDD workflow explained in 5 different files
# coding_standards/TDD_WORKFLOW.md (full explanation)
# reference/dtos/TEMPLATE.md (copy-pasted explanation)
# reference/testing/TEST_TEMPLATE.md (copy-pasted explanation)
# implementation/IMPLEMENTATION_STATUS.md (copy-pasted explanation)
# agent.md (copy-pasted explanation)
```

**Fix:**
```markdown
# ✅ GOOD - One source, multiple links
# coding_standards/TDD_WORKFLOW.md (ONLY authoritative source)
# All other files: "See [TDD_WORKFLOW.md](../coding_standards/TDD_WORKFLOW.md)"
```

### ❌ Anti-Pattern 2: Orphaned Documentation

**Problem:** Document exists but not linked from any index → Lost, never found

**Example:**
```markdown
# ❌ BAD - docs/architecture/SECRET_PATTERN.md exists
# But NOT linked from architecture/README.md
# Result: No one knows it exists
```

**Fix:**
```markdown
# ✅ GOOD - Always update index when creating docs
# 1. Create docs/architecture/SECRET_PATTERN.md
# 2. Update docs/architecture/README.md with link + description
```

### ❌ Anti-Pattern 3: Stale Status Information

**Problem:** IMPLEMENTATION_STATUS.md shows old test counts, wrong completion status

**Example:**
```markdown
# ❌ BAD - Signal shows 22/22 tests, but now 27/27
# Status not updated after refactor
```

**Fix:**
```markdown
# ✅ GOOD - Update status WITH code changes
# Same commit that adds 5 new tests → updates IMPLEMENTATION_STATUS.md
git add backend/dtos/strategy/signal.py
git add tests/unit/dtos/strategy/test_opportunity_signal.py
git add docs/implementation/IMPLEMENTATION_STATUS.md  # ← Don't forget!
git commit -m "feat: add confidence validation to Signal

- Added confidence range validator (0.0-1.0)
- Added 5 new tests for confidence edge cases
- All tests passing (27/27)
- Updated implementation status"
```

### ❌ Anti-Pattern 4: Monolithic Document Growth

**Problem:** Keep adding to same file → 500, 700, 1000+ lines → Unusable

**Example:**
```markdown
# ❌ BAD - CODE_STYLE.md grows to 800 lines
# Started at 200 lines (PEP 8, imports, docstrings)
# Added validation patterns (50 lines)
# Added Pydantic conventions (100 lines)
# Added test patterns (150 lines)
# Added error handling (100 lines)
# Added async patterns (200 lines)
# Result: 800 lines, hard to navigate
```

**Fix:**
```markdown
# ✅ GOOD - Split when > 300 lines
# coding_standards/CODE_STYLE.md (core style rules, 200 lines)
# coding_standards/PYDANTIC_PATTERNS.md (Pydantic-specific, 150 lines)
# coding_standards/TEST_PATTERNS.md (testing conventions, 200 lines)
# coding_standards/ASYNC_PATTERNS.md (async/await rules, 150 lines)
# coding_standards/README.md (updated index with all 5 docs)
```

### ❌ Anti-Pattern 5: README Without Quick Links

**Problem:** README is just a list of files → No guidance on what to read when

**Example:**
```markdown
# ❌ BAD
# Reference Documentation

This directory contains reference docs.

- STRATEGY_DTO_TEMPLATE.md
- DTO_TEST_TEMPLATE.md
- signal.md
- strategy_cache.md
```

**Fix:**
```markdown
# ✅ GOOD
# Reference Documentation

## Quick Links

📋 **Templates:**
- [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md) - DTO boilerplate
- [DTO_TEST_TEMPLATE.md](testing/DTO_TEST_TEMPLATE.md) - Test boilerplate

📚 **Examples:**
- [signal.md](dtos/signal.md) - Signal DTO with causality
- [strategy_cache.md](platform/strategy_cache.md) - StrategyCache service

## Common Workflows

### Creating a New DTO
1. Copy [STRATEGY_DTO_TEMPLATE.md](dtos/STRATEGY_DTO_TEMPLATE.md)
2. Check [signal.md](dtos/signal.md) example
3. Follow [TDD_WORKFLOW.md](../coding_standards/TDD_WORKFLOW.md)
```

## AI-Assisted Documentation Rules

### When to Use AI for Documentation

**✅ Good Uses:**
- Formatting existing notes into proper Markdown
- Expanding bullet points into paragraphs
- Creating examples based on code patterns
- Generating template boilerplate
- Checking grammar/clarity
- Cross-referencing related docs

**❌ Bad Uses:**
- Inventing architectural decisions (AI hallucinates)
- Documenting code AI hasn't seen (outdated info)
- Creating docs without verifying against actual code
- Copy-pasting AI output without review

### AI Documentation Workflow

**1. Capture Intent First (Human):**
```markdown
# Quick notes while coding:
- Signal now has confidence field (0.0-1.0)
- Added 5 tests for edge cases
- Signal/Risk confrontation uses this for weighting
- Similar to Risk.severity pattern
```

**2. Ask AI to Expand (AI + Human Review):**
```
Prompt: "Convert these notes into a section for signal.md 
reference documentation. Include:
- Field description
- Validation rules
- Usage example
- Link to similar Risk pattern"
```

**3. Verify Against Code (Human):**
```python
# Check AI output matches actual implementation
# backend/dtos/strategy/signal.py
confidence: Optional[float] = Field(
    default=None,
    ge=0.0,  # ✅ Matches doc
    le=1.0,  # ✅ Matches doc
    ...
)
```

**4. Integrate + Link (Human):**
```markdown
# Add to signal.md
# Update cross-references to threat_signal.md
# Update IMPLEMENTATION_STATUS.md test count
# Commit together with code
```

### AI Prompts for Common Documentation Tasks

**Create Reference Doc:**
```
I implemented {Component} in {file_path}. Create a reference doc 
following the structure in docs/reference/{category}/README.md. 
Include:
- Overview section
- Architecture context
- API reference (for services) OR Field details (for DTOs)
- Usage patterns
- Testing strategy
- Quality metrics

Base it on {similar_component}.md structure but adapt for this component.
```

**Update Implementation Status:**
```
I just completed {Component} with {X} tests passing, all quality gates 10/10.
Update docs/implementation/IMPLEMENTATION_STATUS.md:
- Add row to {Layer} table
- Update test count totals
- Add to Recent Updates section

Follow the existing table format exactly.
```

**Split Oversized Document:**
```
docs/{path}/{file}.md is now {X} lines (over 300 line limit).
Split it into:
1. Overview doc (keep current filename)
2-N. Sub-topic docs (suggest logical splits)

Create an index section in the overview doc linking to sub-docs.
Preserve all content, just reorganize.
```

**Cleanup Duplicates:**
```
I found the same TDD workflow explanation in:
- {file1}
- {file2}
- {file3}

Keep the FULL explanation only in coding_standards/TDD_WORKFLOW.md.
Replace duplicates with links: "See [TDD_WORKFLOW.md](../coding_standards/TDD_WORKFLOW.md)"
```

## Maintenance Schedule

### Weekly (During Active Development)

**Every Friday or after major feature completion:**

1. **Check IMPLEMENTATION_STATUS.md:**
   - ✅ Test counts match actual tests
   - ✅ Quality metrics accurate (10/10 gates)
   - ✅ Recent Updates section current

2. **Quick Link Verification:**
   - ✅ All README.md indices have working links
   - ✅ No broken cross-references

**Time Required:** 5-10 minutes

### Monthly (Last Day of Month)

**Comprehensive cleanup:**

1. **File Size Audit:**
   ```powershell
   # Find oversized docs
   Get-ChildItem docs -Recurse -Filter "*.md" | 
   Where-Object {(Get-Content $_.FullName | Measure-Object -Line).Lines -gt 300}
   ```

2. **Duplication Check:**
   ```powershell
   # Search for repeated patterns (adjust keywords)
   grep -r "TDD workflow" docs/ | wc -l
   grep -r "quality gates" docs/ | wc -l
   grep -r "Point-in-Time" docs/ | wc -l
   ```

3. **Orphan Detection:**
   ```powershell
   # Find .md files not mentioned in any README.md
   # (Manual review required)
   ```

4. **Update README Quick Links:**
   - ✅ New components added to status matrices
   - ✅ Common workflows reflect current patterns

**Time Required:** 30-45 minutes

### Quarterly (After Major Milestone)

**Full documentation review:**

1. **Architecture Alignment:**
   - ✅ Architecture docs reflect actual implementation
   - ✅ No outdated design decisions documented

2. **Template Updates:**
   - ✅ Templates use latest best practices
   - ✅ Examples updated with new patterns

3. **Cross-Reference Validation:**
   - ✅ All links point to existing sections
   - ✅ Related documentation properly linked

**Time Required:** 2-3 hours

**Deliverable:** Git commit with "docs: Q{X} 2025 maintenance review" message

## Decision Framework

### Should I Create a New Document?

```
Is this a NEW concept (not covered anywhere)?
├─ YES → Does it fit in existing directory?
│   ├─ YES → Create docs/{directory}/{concept}.md + update README
│   └─ NO → Is it big enough for new directory?
│       ├─ YES → Create docs/{new_directory}/ + README.md
│       └─ NO → Add section to most relevant existing doc
└─ NO → Is existing doc < 250 lines?
    ├─ YES → Add section to existing doc
    └─ NO → Split existing doc, then add to relevant sub-doc
```

### Should I Update Existing vs Create New Section?

```
Is this an UPDATE to existing concept?
├─ YES → Update in-place (keep history with git)
└─ NO → Is it RELATED to existing concept?
    ├─ YES → Add new section in same doc
    └─ NO → Create new doc (different concept)
```

### Should I Link or Duplicate?

```
Does this information appear in multiple contexts?
├─ YES → Is it > 3 lines of explanation?
│   ├─ YES → Write once, link everywhere
│   └─ NO → Inline duplication OK (e.g., "DTO must be Pydantic BaseModel")
└─ NO → Write once in most relevant location
```

## Git Workflow for Documentation

### Commit Patterns

**Documentation WITH code changes:**
```powershell
git add backend/dtos/strategy/my_dto.py
git add tests/unit/dtos/strategy/test_my_dto.py
git add docs/implementation/IMPLEMENTATION_STATUS.md
git add docs/reference/dtos/my_dto.md  # If new reference needed

git commit -m "feat: implement MyDTO with validation

- Add MyDTO with 22 tests (all passing)
- Reference docs for new validation pattern
- Updated implementation status

Closes #123"
```

**Documentation-only updates:**
```powershell
git add docs/coding_standards/QUALITY_GATES.md
git add docs/reference/dtos/STRATEGY_DTO_TEMPLATE.md

git commit -m "docs: add getattr() pattern to quality gates

- Documented Pydantic FieldInfo workaround
- Updated DTO template with usage example
- Added to known acceptable warnings section"
```

**Major restructure:**
```powershell
git checkout -b docs/restructure-reference
# ... make changes ...
git commit -m "docs: split reference documentation Phase 1

- Split REFERENCE.md into category subdirs
- Created reference/README.md navigation
- Updated cross-references

Phase: 1/3"
# ... more commits ...
git checkout main
git merge --no-ff docs/restructure-reference
```

### Documentation Branches

**When to use feature branch for docs:**
- ✅ Major restructure (splitting files, reorganizing directories)
- ✅ Multi-phase updates (3+ commits)
- ✅ Breaking changes to templates
- ✅ Experimental documentation approach

**When to commit directly to main:**
- ✅ Status updates (IMPLEMENTATION_STATUS.md)
- ✅ Typo fixes
- ✅ Adding examples to existing docs
- ✅ Updating test counts

## Emergency Fixes

### Documentation Is Becoming Chaos Again

**Symptoms:**
- 🔴 Multiple files > 400 lines
- 🔴 Can't find information without grep
- 🔴 Conflicting information in different files
- 🔴 README indices outdated (missing docs)
- 🔴 AI assistants giving wrong answers (reading outdated docs)

**Emergency Procedure:**

1. **STOP adding to existing docs**
2. **Create emergency branch:**
   ```powershell
   git checkout -b docs/emergency-cleanup
   ```

3. **Triage:**
   ```powershell
   # List all docs by size
   Get-ChildItem docs -Recurse -Filter "*.md" | 
   Select-Object FullName, @{Name="Lines";Expression={(Get-Content $_.FullName | Measure-Object -Line).Lines}} |
   Sort-Object Lines -Descending
   ```

4. **Split largest offenders first** (>400 lines)
5. **Update all README indices**
6. **Search for duplicates:**
   ```powershell
   # Find repeated content
   grep -rn "specific phrase from duplicated content" docs/
   ```

7. **Consolidate duplicates** (keep one source, link others)
8. **Commit with clear message:**
   ```powershell
   git commit -m "docs: emergency cleanup - restore modular structure

   Problem: Documentation grew to unmanageable state
   - 5 files exceeded 400 lines (split into focused docs)
   - Found TDD workflow duplicated in 7 places (consolidated)
   - Updated all README indices with current structure

   Result: Back to <300 lines per doc, single source of truth"
   ```

9. **Merge and document lesson learned:**
   ```markdown
   # Add to this file's "Lessons Learned" section
   ```

## Lessons Learned (Living Document)

### October 2025: Initial Restructure

**Problem:** agent.md grew to 1657 lines - unmanageable for AI and humans

**Solution:** Split into 4 directories (architecture, coding_standards, reference, implementation)

**Result:** 88% size reduction (1657→195 lines), modular structure

**Key Learning:** Establish 300-line limit BEFORE documents grow too large

### [Future learnings will be added here]

---

## Quick Reference Card

**File getting large?**
→ >300 lines? Split it. Update README index.

**Found duplicate content?**
→ Keep ONE authoritative source. Link from others.

**New component implemented?**
→ Update IMPLEMENTATION_STATUS.md. Add reference doc if novel pattern.

**Major design change?**
→ Document in architecture/. Link from related docs.

**Template improvement?**
→ Update template. Note change in reference/README.md.

**Monthly review?**
→ Check sizes, find duplicates, update indices, verify links.

**AI writing docs?**
→ Capture intent first. AI expands. Human verifies against code. Integrate with links.

---

**Remember:** Documentation is CODE. Apply same standards (DRY, single source of truth, modular design, version control).

