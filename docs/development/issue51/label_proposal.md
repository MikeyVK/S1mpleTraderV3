# Label Categorization Proposal - SimpleTraderV3

**Issue:** #51 - Config: Label Management System  
**Phase:** Planning  
**Date:** 2025-12-28  
**Status:** Awaiting Review

---

## Executive Summary

This document proposes a structured approach to labels.yaml based on:
1. Current GitHub repository labels (52 labels analyzed)
2. Research.md recommendations (41 labels documented)
3. Current yaml implementation (37 labels, incomplete)

**Key Finding:** Labels are used **exclusively for GitHub Issues and Pull Requests** - not for branches, commits, or other git objects.

**Current Gap:** 15+ labels exist in GitHub but are missing from yaml, causing validation failures.

---

## Label Usage Analysis

### Where Labels Are Used

**Primary Usage:**
- `CreateIssueTool` - Issues can be created with labels
- `UpdateIssueTool` - Labels can be added/modified
- `AddLabelsTool` - Adds labels to existing issues (validates against yaml)
- `CreateLabelTool` - Creates new labels (validates against yaml)

**Secondary Usage:**
- `CreatePRTool` - Pull requests accept labels parameter
- `ListLabelsTool` - Lists all repository labels

**Key Insight:** Labels are **GitHub metadata only** - they organize, categorize, and track issue/PR workflow.

---

## Proposed Label Categories

### 1. TYPE - Issue Classification

**Rationale:** Classifies the TYPE of work being done  
**Usage:** Applied at issue creation, determines workflow/template  
**Pattern:** `type:{value}`

**Existing in GitHub:**
- ✅ `type:feature` - New functionality
- ✅ `type:bug` - Something isn't working
- ✅ `type:refactor` - Code improvement without behavior change
- ✅ `type:enhancement` - Existing feature improvement
- ✅ `type:epic` - Large feature with multiple sub-issues
- ✅ `type:research` - Research phase work
- ✅ `type:analysis` - Analysis work

**From research.md but NOT in GitHub:**
- ❓ `type:docs` - Documentation changes
- ❓ `type:test` - Test additions
- ❓ `type:discussion` - Discussion needed
- ❓ `type:tech-debt` - Tech debt cleanup
- ❓ `type:validation` - Validation work

**Recommendation:**
- ✅ **KEEP:** All 7 existing `type:*` labels from GitHub
- ✅ **ADD:** `type:docs`, `type:test`, `type:discussion` (useful for workflow)
- ❌ **SKIP:** `type:tech-debt` (GitHub already has `tech-debt` freeform label in heavy use)
- ❌ **SKIP:** `type:validation` (unclear value, no GitHub usage)

**Total: 10 labels** (7 existing + 3 new)

---

### 2. PRIORITY - Urgency Level

**Rationale:** Determines urgency/importance for planning  
**Usage:** Applied during triage, determines work order  
**Pattern:** `priority:{value}`

**Existing in GitHub:**
- ✅ `priority:critical` - Must fix immediately
- ✅ `priority:high` - Should address soon
- ✅ `priority:medium` - Normal priority
- ✅ `priority:low` - Nice to have

**From research.md but NOT in GitHub:**
- ❓ `priority:triage` - Not yet prioritized

**Recommendation:**
- ✅ **KEEP:** All 4 existing priorities
- ✅ **ADD:** `priority:triage` (useful to mark new issues awaiting review)

**Total: 5 labels** (4 existing + 1 new)

---

### 3. PHASE - Workflow State

**Rationale:** Tracks which phase in development lifecycle the issue is in  
**Usage:** Issues move through phases (discovery → planning → implementation → done)  
**Pattern:** `phase:{value}`

**Existing in GitHub:**
- ✅ `phase:research` - Research/exploration phase
- ✅ `phase:planning` - Planning phase

**From research.md but NOT in GitHub:**
- ❓ `phase:discussion` - Discussion phase
- ❓ `phase:design` - Design phase
- ❓ `phase:review` - Review phase
- ❓ `phase:approved` - Design approved
- ❓ `phase:red` - TDD RED (failing tests)
- ❓ `phase:green` - TDD GREEN (passing tests)
- ❓ `phase:refactor` - TDD REFACTOR
- ❓ `phase:implementation` - Implementation phase
- ❓ `phase:verification` - Verification phase
- ❓ `phase:documentation` - Documentation phase
- ❓ `phase:done` - Complete

**Recommendation:**
- ✅ **KEEP:** `phase:research`, `phase:planning`
- ✅ **ADD TDD phases:** `phase:red`, `phase:green`, `phase:refactor` (critical for TDD workflow this project uses)
- ✅ **ADD from workflows.yaml:** `phase:design`, `phase:integration`, `phase:documentation` (match workflow phases)
- ✅ **ADD terminal state:** `phase:done` (end state, not in workflow)
- ❌ **SKIP:** `phase:discussion`, `phase:approved`, `phase:verification`, `phase:review` (not in workflows.yaml)

**Total: 10 labels** (2 existing + 8 new: 3 TDD sub-states + 3 workflow phases + 1 terminal + 1 rename)

**Note:** This aligns with workflows.yaml which defines phase sequences per workflow type.

**Workflow Mapping (Optie B - Granular Sub-phases):**

We chose **Optie B** (granular labels) instead of 1:1 workflow mapping because:
1. Issues remain in TDD phase for extended periods - valuable to track red/green/refactor progress
2. Git commits already use `red:/green:/refactor:` prefix (commit convention alignment)
3. Granularity helps enforce TDD discipline and measure compliance

```
workflows.yaml phase → GitHub labels (1:1 for main phases, 1:3 for TDD)

research        → phase:research (renamed from discovery)
planning        → phase:planning (1:1 mapping)
design          → phase:design (1:1 mapping)
tdd             → phase:red / phase:green / phase:refactor (3 sub-states)
integration     → phase:integration (1:1 mapping)
documentation   → phase:documentation (1:1 mapping)
(terminal)      → phase:done (end state, not in workflow)
```

**Label list (10 total):**
- `phase:research` (rename discovery in GitHub)
- `phase:planning` (exists)
- `phase:design` (add)
- `phase:red` (add - TDD sub-state)
- `phase:green` (add - TDD sub-state)
- `phase:refactor` (add - TDD sub-state)
- `phase:integration` (add - from workflows.yaml)
- `phase:documentation` (add - from workflows.yaml)
- `phase:done` (add - terminal state)

---

### 4. STATUS - Current State

**Rationale:** Real-time status indicating why work is paused or what's needed  
**Usage:** Indicates blockers, dependencies, or next actions required  
**Pattern:** `status:{value}` (unified, not mixing `needs:*` pattern)

**Existing in GitHub:**
- ✅ `status:blocked` - Blocked by external dependency

**From research.md but NOT in GitHub:**
- ❓ `status:needs-info` - More information required
- ❓ `status:ready-for-review` - Ready for review
- ❓ `needs:discussion` - Discussion needed
- ❓ `needs:design` - Design work needed
- ❓ `needs:info` - Info needed

**Recommendation:**
- ✅ **KEEP:** `status:blocked`
- ✅ **ADD:** `status:needs-info`, `status:in-progress`, `status:ready-for-review` (standard workflow states)
- ❌ **SKIP:** `needs:*` labels (creates inconsistency with two patterns; use `status:needs-*` instead)

**Total: 4 labels** (1 existing + 3 new)

---

### 5. SCOPE - Impact Area

**Rationale:** Identifies which part of the system is affected  
**Usage:** Filters issues by technical domain, helps with impact assessment and code ownership  
**Pattern:** `scope:{value}`

**Existing in GitHub:**
- ✅ `scope:architecture` - Architectural changes
- ✅ `scope:mcp-server` - MCP server scope
- ✅ `scope:platform` - Platform scope
- ✅ `scope:tooling` - Tooling scope
- ✅ `scope:workflow` - Workflow improvements
- ✅ `scope:process` - Process improvements
- ✅ `scope:core` - Core system
- ✅ `scope:git-tooling` - Git tooling
- ✅ `scope:phase-workflow` - Phase workflow
- ✅ `scope:documentation` - Documentation

**From research.md but NOT in GitHub:**
- ❓ `scope:component` - Component-level changes

**Recommendation:**
- ✅ **KEEP:** All 10 existing scope labels (well-used, good differentiation)
- ❌ **SKIP:** `scope:component` (redundant, unclear vs other scopes)

**Total: 10 labels** (10 existing + 0 new)

---

### 6. COMPONENT - Technical Component (Added by agent, NOT in research)

**Rationale:** ❌ **NONE** - I added this without justification

**Labels I created:**
- `component:mcp-server`
- `component:tools`
- `component:resources`
- `component:config`

**Problem:** Overlaps with existing `scope:*` labels

**Recommendation:**
- ❌ **REMOVE ENTIRELY** - No value add, creates confusion with scope labels

**Total: 0 labels**

---

### 7. EFFORT - Size Estimation (Added by agent, NOT in research)

**Rationale:** ❌ **NONE** - I added this without justification

**Labels I created:**
- `effort:small` (< 1 day)
- `effort:medium` (1-3 days)
- `effort:large` (> 3 days)

**Existing in GitHub:**
- `complexity:medium` (similar concept, different name)

**Recommendation:**
- ❌ **SKIP FOR NOW** - Not in research, not in GitHub (except one complexity label)
- 💡 **IF NEEDED:** Add with clear rationale (e.g., "For sprint planning and velocity tracking")

**Total: 0 labels**

---

### 8. FREEFORM - GitHub Defaults & Legacy

**Rationale:** Preserve GitHub's default labels and community standards  
**Pattern:** No pattern (flat names)

**Existing in GitHub:**
- ✅ `bug`, `enhancement`, `feature` - GitHub defaults (legacy, before type: pattern)
- ✅ `documentation`, `testing`, `refactor` - Simple tags
- ✅ `good first issue`, `help wanted` - Community/contributor labels
- ✅ `duplicate`, `invalid`, `wontfix`, `question` - Issue triage labels
- ✅ `tdd`, `qa`, `quality`, `mcp` - Project-specific tags

**Recommendation:**
- ✅ **KEEP in freeform_exceptions list** - Allows both patterns for backwards compatibility
- 💡 **FUTURE:** Gradually migrate to pattern-based (e.g., `bug` → `type:bug`)

**Total: ~15 freeform labels**

---

### 9. PARENT - Issue Hierarchy (Dynamic)

**Pattern:** `parent:issue-{number}`

**Existing in GitHub:**
- `parent:issue-18`
- `parent:issue-42`
- `parent:issue-49`
- `parent:issue-51`

**Recommendation:**
- ❌ **DO NOT ADD to labels.yaml** - These are dynamically created per epic/parent issue
- ✅ **ALLOW pattern in validation** - Pattern should be recognized as valid

**Total: 0 predefined (pattern-based validation only)**

---

## Summary Table

| Category | Existing GitHub | From Research | Agent Added | Recommended Total |
|----------|----------------|---------------|-------------|-------------------|
| type:* | 7 | +3 useful | +0 | **10** |
| priority:* | 4 | +1 useful | +0 | **5** |
| phase:* | 2 | +8 useful | +0 | **10** |
| status:* | 1 | +3 useful | +0 | **4** |
| scope:* | 10 | +0 | +0 | **10** |
| component:* | 0 | +0 | +4 (remove) | **0** |
| effort:* | 0 | +0 | +3 (skip) | **0** |
| freeform | ~15 | +5 | +0 | **~15** |
| **TOTAL** | **52** | **41** | **37** | **~54** |

---

## Implementation Plan

### Phase 1: Update labels.yaml Structure

Add category headers with rationale/description:

```yaml
version: "1.0"

# Freeform exceptions - GitHub defaults and community labels
# These labels don't follow the category:value pattern
freeform_exceptions:
  - "good first issue"
  - "help wanted"
  - "duplicate"
  - "invalid"
  - "wontfix"
  - "question"
  - "bug"
  - "enhancement"
  - "feature"
  - "documentation"
  - "testing"
  - "refactor"
  - "tdd"
  - "qa"
  - "quality"
  - "mcp"

labels:
  # TYPE - Issue Classification
  # Determines what kind of work is being done
  # Usage: Applied at issue creation, determines workflow/template
  - name: "type:feature"
    ...
```

### Phase 2: Add Missing Labels

- Add 14 new structured labels (see recommendations above)
- Preserve all 10 existing scope labels
- Remove 4 component:* labels I incorrectly added
- Update freeform_exceptions to include all GitHub legacy labels

### Phase 3: Validation Enhancement

Update `validate_label_name()` to:
- Allow `parent:issue-{number}` pattern
- Consider allowing both `type:feature` and `feature` (backwards compat)

### Phase 4: GitHub Sync

Run `sync_labels_to_github` to:
- Create missing labels in GitHub
- Update colors/descriptions to match yaml
- Report any GitHub labels not in yaml

---

## Open Questions

1. **Backwards Compatibility:** Should we allow both `bug` and `type:bug`?
2. **Effort Labels:** Do we need effort estimation labels for sprint planning?
3. **Migration Strategy:** How to handle ~15 freeform labels already in heavy use?
4. **Parent Pattern:** Should validation auto-allow `parent:issue-*` pattern?

---

## Next Steps

1. ✅ Review this proposal
2. ⏳ Get feedback on each category
3. ⏳ Update labels.yaml with approved structure
4. ⏳ Test validation with actual GitHub labels
5. ⏳ Sync to GitHub repository
6. ⏳ Update documentation

---

## Appendix: GitHub Labels Not In Research

These labels exist in GitHub but weren't documented in research.md:

- `type:epic` - Large multi-issue features
- `type:analysis` - Analysis work
- `scope:core` - Core system
- `scope:git-tooling` - Git tooling
- `scope:phase-workflow` - Phase workflow
- `complexity:medium` - Effort estimation
- `component:developer-experience` - DX improvements
- `developer-experience` - DX (freeform)
- `gap-analysis` - Gap analysis work
- `process` - Process work (freeform)
- `mcp-server` - MCP server (freeform, duplicates `scope:mcp-server`)

**Recommendation:** Include type:epic and type:analysis (useful), skip the rest or consolidate duplicates.
