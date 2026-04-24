# Tracking Artifact Type Architecture

**Status:** PROPOSED  
**Date:** 2026-01-26  
**Context:** Issue #72 Tier Structure Discussion

---

## Decision Summary

Promote `tracking` from artifact type_id to top-level artifact **type** (alongside `code` and `doc`), replacing the vague term "ephemeral".

## Current Structure (Before)

```yaml
artifact_types:
  # ===== CODE ARTIFACTS =====
  - type: code
    type_id: dto, worker, service...
    
  # ===== DOCUMENT ARTIFACTS =====
  - type: doc
    type_id: design, architecture, reference...
    type_id: tracking  # ⚠️ CONFLICT: treated as knowledge doc
    
  # ===== EPHEMERAL ARTIFACTS =====
  - type: doc  # ⚠️ Wrong category
    type_id: commit_message
    output_type: "ephemeral"
```

**Problems:**
1. "ephemeral" is vague terminology
2. `tracking` type_id conflicts with Git workflow artifacts
3. Git artifacts incorrectly categorized as `type: doc`
4. No clear distinction between knowledge docs vs workflow artifacts

## Proposed Structure (After)

```yaml
artifact_types:
  # ===== CODE ARTIFACTS =====
  - type: code
    type_id: dto, worker, service, adapter...
    
  # ===== DOCUMENT ARTIFACTS =====
  - type: doc
    type_id: design, architecture, reference, research, planning
    # Features: versioning, status lifecycle (DRAFT→APPROVED→DEFINITIVE)
    
  # ===== TRACKING ARTIFACTS =====
  - type: tracking
    type_id: commit, pr, issue, milestone, changelog, release_notes
    # Features: ephemeral, no versioning, workflow context, VCS-agnostic
```

## Tier Mapping

### Tier 1: Artifact Type (Format Level)

```
tier1_base_code.jinja2        # Python classes, functions, imports
tier1_base_document.jinja2    # Status, Purpose, Scope, Version History
tier1_base_tracking.jinja2    # No status, no versioning, workflow metadata
```

### Tier 2: Language Syntax

```
tier1_base_code
├── tier2_base_python.jinja2

tier1_base_document
├── tier2_base_markdown.jinja2

tier1_base_tracking
├── tier2_tracking_text.jinja2      # Plain text (commit messages)
└── tier2_tracking_markdown.jinja2  # Markdown (PR, issue, milestone)
```

### Concrete: Specific Artifacts

```
# CODE
dto.py.jinja2 → tier2_base_python → tier1_base_code

# DOCUMENT  
design.md.jinja2 → tier2_base_markdown → tier1_base_document

# TRACKING
commit.txt.jinja2 → tier2_tracking_text → tier1_base_tracking
pr.md.jinja2 → tier2_tracking_markdown → tier1_base_tracking
issue.md.jinja2 → tier2_tracking_markdown → tier1_base_tracking
```

## Migration Impact

### Files to Create
- `mcp_server/scaffolding/templates/tier1_base_tracking.jinja2`
- `mcp_server/scaffolding/templates/tier2_tracking_text.jinja2`
- `mcp_server/scaffolding/templates/tier2_tracking_markdown.jinja2`
- `mcp_server/scaffolding/templates/concrete/commit.txt.jinja2`
- `mcp_server/scaffolding/templates/concrete/pr.md.jinja2`
- `mcp_server/scaffolding/templates/concrete/issue.md.jinja2`

### Files to Update
- `.st3/artifacts.yaml` - Change `commit_message` artifact:
  ```yaml
  # OLD
  - type: doc
    type_id: commit_message
    output_type: "ephemeral"
    template_path: "docs/commit-message.txt.jinja2"
  
  # NEW
  - type: tracking
    type_id: commit
    output_type: "ephemeral"
    template_path: "concrete/commit.txt.jinja2"
  ```

- `.st3/project_structure.yaml` - Add `tracking` to allowed_artifact_types where needed

### Legacy "tracking" Document Type

**Decision:** Deprecate `type_id: tracking` document (LIVING DOCUMENT antipattern).

**Rationale:**
- Git provides better tracking (commit history, PR comments, issues)
- LIVING DOCUMENT status contradicts versioning philosophy
- Creates confusion with new `type: tracking` category

**Migration Path:**
- Existing tracking docs (e.g., `docs/TODO.md`) move to GitHub Issues/Projects
- Template `docs/tracking.md.jinja2` → deleted
- `type_id: tracking` removed from artifacts.yaml

## Characteristics: Document vs Tracking

| Feature | Document | Tracking |
|---------|----------|----------|
| **Versioning** | ✅ Version history section | ❌ No versioning |
| **Status Lifecycle** | DRAFT → APPROVED → DEFINITIVE | CREATED only |
| **Persistence** | Committed to repo | Ephemeral (Git workflow) |
| **Purpose** | Knowledge capture | Workflow metadata |
| **Examples** | design.md, architecture.md | commit msg, PR description |
| **Tier1 Base** | tier1_base_document | tier1_base_tracking |

## Rationale

### Why "tracking" instead of "ephemeral"?

1. **Descriptive:** Tracking = workflow artifacts (commits, PRs, issues)
2. **VCS-agnostic:** Works for Git, SVN, Mercurial
3. **Parallel Structure:** `type: code`, `type: doc`, `type: tracking` (balanced triad)
4. **Eliminates Conflict:** Old `type_id: tracking` deprecated, no naming collision
5. **Clear Semantics:** Tracking ≠ Documentation (different purpose, lifecycle)

### Why top-level type instead of doc subcategory?

1. **Fundamentally Different:** Documents have versioning/status, tracking artifacts don't
2. **Separate Tier1:** Different base structure (no Purpose/Scope sections)
3. **Output Behavior:** tracking artifacts often ephemeral (not written to disk)
4. **Tooling Integration:** Different validation rules (no SCAFFOLD header propagation check)

## Open Questions

1. **Should milestones be ephemeral or file-based?**
   - Ephemeral: Generated from GitHub API (no disk write)
   - File: Committed milestone docs (e.g., `docs/milestones/v1.0.md`)
   - **Recommendation:** Start ephemeral, add file-based milestone doc as separate type_id if needed

2. **Do tracking artifacts need SCAFFOLD headers?**
   - Commit messages: No (breaks Git format)
   - PR/Issue descriptions: Maybe (provenance tracking)
   - **Recommendation:** tier0 SCAFFOLD optional for tracking artifacts (controlled by tier1 block override)

3. **Where do release notes fit?**
   - Option A: `type: tracking, type_id: release_notes` (workflow artifact)
   - Option B: `type: doc, type_id: reference` (knowledge document)
   - **Recommendation:** Option A (generated from Git history, ephemeral during creation, then committed)

## Implementation Order

1. ✅ Document this decision (this file)
2. Create tier1_base_tracking.jinja2 (minimal structure, no status/version fields)
3. Create tier2_tracking_text.jinja2 (plain text syntax, no markdown)
4. Create tier2_tracking_markdown.jinja2 (markdown syntax for PR/issue)
5. Create concrete/commit.txt.jinja2 (extends tier2_tracking_text)
6. Update artifacts.yaml (commit_message → commit, add pr/issue stubs)
7. Run E2E tests (provenance tracking for tracking artifacts)
8. Deprecate old tracking doc type (remove from artifacts.yaml)

## Related Documents

- [design.md](design.md) - Multi-tier template architecture
- [planning.md](planning.md) - Task 1.6 design template implementation
- `.st3/artifacts.yaml` - Artifact registry schema
- `docs/reference/templates/TRACKING_TEMPLATE.md` - Legacy tracking doc format (to be deprecated)
