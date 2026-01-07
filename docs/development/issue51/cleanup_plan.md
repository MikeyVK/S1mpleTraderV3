# Issue #51: GitHub Label Cleanup Plan

**Date:** 2025-12-30  
**Status:** Ready for Execution  
**Issue:** #51 - Config: Label Management System (labels.yaml)

---

## Executive Summary

This document defines the complete label cleanup strategy for the SimpleTraderV3 repository. We are reducing from 54 GitHub labels to 32 strategic labels (27 structured + 5 freeform exceptions), with strict enforcement via labels.yaml validation.

**Key Principles:**
1. **Structured labels only:** All labels follow `category:value` pattern (except freeform exceptions)
2. **Workflows.yaml alignment:** Phase labels match workflow definitions exactly
3. **No missing priorities:** Issues without priority get `priority:triage` (not a default, requires explicit triage)
4. **Epic detection:** Issues with children automatically get `type:epic` label
5. **Enhancement ≠ Feature:** `type:enhancement` = improve existing, `type:feature` = new capability

---

## 1. Final Label Schema (32 Labels)

### TYPE Labels (7 labels)

| Label | Color | Description | Usage |
|-------|-------|-------------|-------|
| `type:feature` | 1D76DB | New functionality or capability | Net nieuwe features |
| `type:enhancement` | A2EEEF | Improvement to existing feature | Verbetering van bestaande functionaliteit |
| `type:bug` | D73A4A | Something isn't working | Defect fixes |
| `type:refactor` | 0E8A16 | Code improvement without behavior change | Internal restructuring |
| `type:docs` | 0075CA | Documentation changes | Docs only |
| `type:research` | 1D76DB | Research and exploration work | Discovery/analysis |
| `type:epic` | 5319E7 | Large feature with multiple sub-issues | Parent issues with children |

**Distinction: Feature vs Enhancement:**
- **Feature:** Completely new capability that didn't exist before
  - Example: "Add SafeEditTool for file modifications"
- **Enhancement:** Improve/extend existing functionality
  - Example: "Add line-based editing to SafeEditTool"
- **Refactor:** Internal code quality improvement, no behavior change
  - Example: "Extract validation logic to separate module"

### PRIORITY Labels (5 labels)

| Label | Color | Description | Usage |
|-------|-------|-------------|-------|
| `priority:critical` | B60205 | Must be fixed immediately | Blockers, production issues |
| `priority:high` | D93F0B | Should be addressed soon | Important for milestone |
| `priority:medium` | FBCA04 | Normal priority | Standard work items |
| `priority:low` | BFD4F2 | Nice to have | Future enhancements |
| `priority:triage` | EDEDED | Needs prioritization | NEW issues awaiting triage |

**Priority Assignment Strategy:**
- **No default priority:** Issues without priority label get `priority:triage`
- **Triage is explicit:** Forces conscious decision about importance
- **Review triage queue:** Weekly review of all `priority:triage` issues

### PHASE Labels (6 labels)

| Label | Color | Description | Workflow Alignment |
|-------|-------|-------------|-------------------|
| `phase:research` | C5DEF5 | Research/discovery phase | workflows.yaml: research |
| `phase:planning` | C5DEF5 | Planning phase | workflows.yaml: planning |
| `phase:design` | C5DEF5 | Design phase | workflows.yaml: design |
| `phase:tdd` | 0E8A16 | TDD implementation phase | workflows.yaml: tdd |
| `phase:integration` | 1D76DB | Integration testing phase | workflows.yaml: integration |
| `phase:documentation` | 0075CA | Documentation phase | workflows.yaml: documentation |

**Alignment:** 1:1 mapping met workflows.yaml phases (geen sub-phases zoals red/green/refactor)

**NOT included:** `phase:red/green/refactor` - these are **commit prefixes** and **branch state**, not issue metadata.

### STATUS Labels (4 labels)

| Label | Color | Description | Usage |
|-------|-------|-------------|-------|
| `status:blocked` | D73A4A | Blocked by external dependency | Waiting on other issue/PR |
| `status:in-progress` | 0E8A16 | Currently being worked on | Active development |
| `status:needs-info` | D876E3 | Needs more information | Awaiting clarification |
| `status:ready` | FBCA04 | Ready for review/merge | Implementation complete |

### SCOPE Labels (6 labels)

| Label | Color | Description | Usage |
|-------|-------|-------------|-------|
| `scope:architecture` | BFD4F2 | Architectural changes | System design, patterns |
| `scope:mcp-server` | BFD4F2 | MCP server internals | Tools, resources, managers |
| `scope:platform` | BFD4F2 | GitHub/git platform integration | API, git operations |
| `scope:tooling` | BFD4F2 | Development tooling | Scaffolding, validation |
| `scope:workflow` | BFD4F2 | Workflow/process improvements | Phase management, branching |
| `scope:documentation` | BFD4F2 | Documentation scope | Docs structure, templates |

### PARENT Labels (Dynamic)

**Pattern:** `parent:issue-{number}`

**Current parent issues:**
- `parent:issue-18` - Issue #18 (TDD Enforcement Epic) - 10+ children
- `parent:issue-42` - Issue #42 (Phase Workflow) - 2 children
- `parent:issue-49` - Issue #49 (MCP Configurability Epic) - 8 children
- `parent:issue-51` - Issue #51 (Label Management) - 2 children

**Strategy:** Parent labels are **NOT** predefined in labels.yaml. They are dynamically created when an issue has children.

### FREEFORM Exceptions (5 labels)

| Label | Color | Description | Usage |
|-------|-------|-------------|-------|
| `good first issue` | 7057FF | Good for newcomers | Community contribution |
| `help wanted` | 008672 | Extra attention is needed | Seeking contributors |
| `duplicate` | CFD3D7 | Duplicate issue/PR | Close as duplicate |
| `invalid` | E4E669 | Invalid issue | Close as invalid |
| `wontfix` | FFFFFF | Will not be worked on | Rejected feature |

**Note:** `question` removed - use issue discussions or `status:needs-info` instead.

---

## 2. GitHub Cleanup Actions

### A. Delete Labels (22 labels)

**Freeform duplicates (replaced with type:* pattern):**
```
✗ bug                    → use type:bug
✗ feature                → use type:feature  
✗ refactor               → use type:refactor
✗ testing                → use type:test (NOT INCLUDED, see below)
✗ documentation          → use type:docs
```

**Unused/redundant:**
```
✗ complexity:medium           # Not in strategy, no tooling
✗ component:developer-experience  # Redundant with scope:tooling
✗ developer-experience        # Duplicate
✗ gap-analysis                # Single use, not strategic
✗ mcp                         # Too generic
✗ mcp-server                  # Duplicate of scope:mcp-server
✗ process                     # Use scope:workflow
✗ qa                          # Use priority + quality gates
✗ quality                     # Not strategic
✗ tech-debt                   # Use type:refactor + priority:high
✗ tooling                     # Use scope:tooling
✗ question                    # Use status:needs-info
```

**Redundant scope labels (consolidate):**
```
✗ scope:core              → merge to scope:architecture
✗ scope:git               → merge to scope:platform
✗ scope:git-tooling       → merge to scope:tooling
✗ scope:phase-workflow    → merge to scope:workflow
✗ scope:process           → merge to scope:workflow
```

**Decision: Remove type:test and type:analysis:**
- `type:test` - Only for test-specific issues (not common)
- `type:analysis` - Use `type:research` instead (same semantic)
- Removed from strategy: 0 issues currently use them uniquely

### B. Create Labels (7 new labels)

```yaml
✓ type:enhancement         # Improve existing features (6 issues use freeform 'enhancement')
✓ type:research            # Research/analysis work (replaces type:analysis)
✓ priority:triage          # Needs prioritization (explicit triage queue)
✓ phase:design             # workflows.yaml alignment
✓ phase:tdd                # workflows.yaml alignment
✓ phase:integration        # workflows.yaml alignment
✓ phase:documentation      # workflows.yaml alignment
```

### C. Rename Labels (2 labels)

```
phase:discovery → phase:research   # Align with workflows.yaml
status:review   → status:ready     # Clearer semantics
```

---

## 3. Issue Relabeling Plan (36 Open Issues)

### Epic Detection Strategy

**Rule:** If issue has children (other issues with `parent:issue-X`), add `type:epic`.

**Current epics detected:**
- #18: 10+ children → add `type:epic`
- #42: 2 children (#59, #62) → add `type:epic`
- #49: 8 children → already has `type:epic` ✓
- #51: 2 children (#60, #62) → add `type:epic`

**NOT epics (no children):**
- All other issues remain with their current type labels

### Phase Alignment (2 issues)

| Issue | Current | New | Reason |
|-------|---------|-----|--------|
| #37 | phase:discovery | phase:research | Align with workflows.yaml |
| #48 | (none) | phase:research | Add missing phase |

### Scope Consolidation (4 issues)

| Issue | Remove | Add | Reason |
|-------|--------|-----|--------|
| #45 | scope:core | scope:architecture | Core → Architecture |
| #46 | scope:git-tooling, scope:phase-workflow | scope:tooling, scope:workflow | Consolidate 2→2 |
| #59 | scope:process | scope:workflow | Process → Workflow |

### Add Missing Types (4 issues using freeform)

| Issue | Current | Add | Reason |
|-------|---------|-----|--------|
| #24 | enhancement (freeform) | type:enhancement | Structured label |
| #18 | enhancement (freeform) | type:enhancement | Structured label |
| #14 | enhancement (freeform) | type:enhancement | Structured label |
| #15 | enhancement (freeform) | type:enhancement | Structured label |

### Add Missing Priorities → Triage (8 issues)

**Strategy:** No priority = needs triage (NOT default to medium)

| Issue | Current Priority | Add | Reason |
|-------|------------------|-----|--------|
| #19 | (none) | priority:triage | Needs triage |
| #22 | (none) | priority:triage | Needs triage |
| #24 | (none) | priority:triage | Needs triage |
| #14 | (none) | priority:triage | Needs triage |
| #15 | (none) | priority:triage | Needs triage |
| #16 | (none) | priority:triage | Needs triage |
| #40 | (none) | priority:triage | Needs triage |
| #48 | (none) | priority:triage | Needs triage |

### Add Epic Labels (4 issues)

| Issue | Add | Reason |
|-------|-----|--------|
| #18 | type:epic | Has 10+ children |
| #42 | type:epic | Has 2 children (#59, #62) |
| #51 | type:epic | Has 2 children (#60, #62) |

**Note:** #49 already has `type:epic` ✓

### Remove Freeform Duplicates (Cleanup)

| Issue | Remove | Keep | Reason |
|-------|--------|------|--------|
| #16 | tdd, qa, testing | type:research, priority:triage | Use structured labels |
| #18 | tdd, qa, tooling | type:enhancement (add), type:epic (add) | Use structured labels |
| #47 | quality, tech-debt | type:refactor | Use structured labels |
| #19 | mcp-server, developer-experience, documentation | scope:mcp-server (add), type:docs (add) | Use structured labels |
| #22 | (none - only type:analysis) | Replace with type:research | Consolidate |

---

## 4. Validation Rules (Enforceable)

### Mandatory Labels

**Every issue MUST have:**
1. Exactly **1 TYPE label** (type:*)
2. Exactly **1 PRIORITY label** (priority:*)
3. Zero or **1 PHASE label** (phase:*) - optional during triage
4. Zero or **1 STATUS label** (status:*) - optional
5. Zero or **more SCOPE labels** (scope:*) - multi-scope OK

### Label Combinations

**Valid combinations:**
```
✓ type:feature + priority:high + phase:tdd + scope:mcp-server
✓ type:bug + priority:critical + status:blocked + scope:platform + scope:git
✓ type:epic + priority:critical + phase:planning + scope:architecture
```

**Invalid combinations:**
```
✗ type:feature + type:bug              # Multiple types
✗ priority:high + priority:medium      # Multiple priorities
✗ phase:planning + phase:tdd           # Multiple phases
✗ (no type label)                      # Missing mandatory type
✗ (no priority label)                  # Missing mandatory priority
```

### Special Rules

**Epic issues:**
- MUST have `type:epic` if children exist (parent:issue-X labels found)
- CAN have other type labels? **NO** - epic is mutually exclusive with other types

**Triage issues:**
- `priority:triage` = "not yet triaged"
- During triage: replace with appropriate priority (critical/high/medium/low)
- Goal: Zero issues in triage queue

**Phase labels:**
- Phase is **optional** during initial triage
- Once work starts, phase becomes **mandatory**
- Phase must match workflows.yaml sequence

---

## 5. Migration Execution Plan

### Step 1: Update labels.yaml (Local)

File: `.st3/labels.yaml`

```yaml
version: "1.0"

freeform_exceptions:
  - "good first issue"
  - "help wanted"
  - "wontfix"
  - "duplicate"
  - "invalid"

labels:
  # TYPE - Issue Classification (7 labels)
  - name: "type:feature"
    color: "1D76DB"
    description: "New functionality or capability"
  
  - name: "type:enhancement"
    color: "A2EEEF"
    description: "Improvement to existing feature"
  
  - name: "type:bug"
    color: "D73A4A"
    description: "Something isn't working"
  
  - name: "type:refactor"
    color: "0E8A16"
    description: "Code improvement without behavior change"
  
  - name: "type:docs"
    color: "0075CA"
    description: "Documentation changes"
  
  - name: "type:research"
    color: "1D76DB"
    description: "Research and exploration work"
  
  - name: "type:epic"
    color: "5319E7"
    description: "Large feature with multiple sub-issues"
  
  # PRIORITY - Urgency Level (5 labels)
  - name: "priority:critical"
    color: "B60205"
    description: "Must be fixed immediately"
  
  - name: "priority:high"
    color: "D93F0B"
    description: "Should be addressed soon"
  
  - name: "priority:medium"
    color: "FBCA04"
    description: "Normal priority"
  
  - name: "priority:low"
    color: "BFD4F2"
    description: "Low priority, nice to have"
  
  - name: "priority:triage"
    color: "EDEDED"
    description: "Needs prioritization"
  
  # PHASE - Workflow State (6 labels)
  - name: "phase:research"
    color: "C5DEF5"
    description: "Research/discovery phase"
  
  - name: "phase:planning"
    color: "C5DEF5"
    description: "Planning phase"
  
  - name: "phase:design"
    color: "C5DEF5"
    description: "Design phase"
  
  - name: "phase:tdd"
    color: "0E8A16"
    description: "TDD implementation phase"
  
  - name: "phase:integration"
    color: "1D76DB"
    description: "Integration testing phase"
  
  - name: "phase:documentation"
    color: "0075CA"
    description: "Documentation phase"
  
  # STATUS - Current State (4 labels)
  - name: "status:blocked"
    color: "D73A4A"
    description: "Blocked by external dependency"
  
  - name: "status:in-progress"
    color: "0E8A16"
    description: "Currently being worked on"
  
  - name: "status:needs-info"
    color: "D876E3"
    description: "Needs more information"
  
  - name: "status:ready"
    color: "FBCA04"
    description: "Ready for review/merge"
  
  # SCOPE - Impact Area (6 labels)
  - name: "scope:architecture"
    color: "BFD4F2"
    description: "Architectural changes"
  
  - name: "scope:mcp-server"
    color: "BFD4F2"
    description: "MCP server internals"
  
  - name: "scope:platform"
    color: "BFD4F2"
    description: "GitHub/git platform integration"
  
  - name: "scope:tooling"
    color: "BFD4F2"
    description: "Development tooling"
  
  - name: "scope:workflow"
    color: "BFD4F2"
    description: "Workflow/process improvements"
  
  - name: "scope:documentation"
    color: "BFD4F2"
    description: "Documentation scope"
```

### Step 2: GitHub Label Cleanup (22 deletes)

**Commands:**
```bash
# Delete freeform duplicates
mcp_st3-workflow_delete_label(name="bug")
mcp_st3-workflow_delete_label(name="feature")
mcp_st3-workflow_delete_label(name="refactor")
mcp_st3-workflow_delete_label(name="testing")
mcp_st3-workflow_delete_label(name="documentation")

# Delete unused/redundant
mcp_st3-workflow_delete_label(name="complexity:medium")
mcp_st3-workflow_delete_label(name="component:developer-experience")
mcp_st3-workflow_delete_label(name="developer-experience")
mcp_st3-workflow_delete_label(name="gap-analysis")
mcp_st3-workflow_delete_label(name="mcp")
mcp_st3-workflow_delete_label(name="mcp-server")
mcp_st3-workflow_delete_label(name="process")
mcp_st3-workflow_delete_label(name="qa")
mcp_st3-workflow_delete_label(name="quality")
mcp_st3-workflow_delete_label(name="tech-debt")
mcp_st3-workflow_delete_label(name="tooling")
mcp_st3-workflow_delete_label(name="question")

# Delete redundant scope labels
mcp_st3-workflow_delete_label(name="scope:core")
mcp_st3-workflow_delete_label(name="scope:git")
mcp_st3-workflow_delete_label(name="scope:git-tooling")
mcp_st3-workflow_delete_label(name="scope:phase-workflow")
mcp_st3-workflow_delete_label(name="scope:process")
```

### Step 3: Create New Labels (7 creates)

**Commands:**
```bash
mcp_st3-workflow_create_label(name="type:enhancement", color="A2EEEF", description="Improvement to existing feature")
mcp_st3-workflow_create_label(name="type:research", color="1D76DB", description="Research and exploration work")
mcp_st3-workflow_create_label(name="priority:triage", color="EDEDED", description="Needs prioritization")
mcp_st3-workflow_create_label(name="phase:design", color="C5DEF5", description="Design phase")
mcp_st3-workflow_create_label(name="phase:tdd", color="0E8A16", description="TDD implementation phase")
mcp_st3-workflow_create_label(name="phase:integration", color="1D76DB", description="Integration testing phase")
mcp_st3-workflow_create_label(name="phase:documentation", color="0075CA", description="Documentation phase")
```

### Step 4: Relabel Issues (36 issues)

**Batch operations per category:**

#### Add Epic Labels (3 issues)
```bash
mcp_st3-workflow_add_labels(issue_number=18, labels=["type:epic"])
mcp_st3-workflow_add_labels(issue_number=42, labels=["type:epic"])
mcp_st3-workflow_add_labels(issue_number=51, labels=["type:epic"])
```

#### Phase Alignment (2 issues)
```bash
# #37: phase:discovery → phase:research
mcp_st3-workflow_remove_labels(issue_number=37, labels=["phase:discovery"])
mcp_st3-workflow_add_labels(issue_number=37, labels=["phase:research"])

# #48: add phase:research
mcp_st3-workflow_add_labels(issue_number=48, labels=["phase:research"])
```

#### Add Type Enhancement (4 issues)
```bash
mcp_st3-workflow_add_labels(issue_number=24, labels=["type:enhancement"])
mcp_st3-workflow_add_labels(issue_number=18, labels=["type:enhancement"])
mcp_st3-workflow_add_labels(issue_number=14, labels=["type:enhancement"])
mcp_st3-workflow_add_labels(issue_number=15, labels=["type:enhancement"])
```

#### Add Priority Triage (8 issues)
```bash
mcp_st3-workflow_add_labels(issue_number=19, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=22, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=24, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=14, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=15, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=16, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=40, labels=["priority:triage"])
mcp_st3-workflow_add_labels(issue_number=48, labels=["priority:triage"])
```

#### Scope Consolidation (4 issues)
```bash
# #45: scope:core → scope:architecture
mcp_st3-workflow_remove_labels(issue_number=45, labels=["scope:core"])
mcp_st3-workflow_add_labels(issue_number=45, labels=["scope:architecture"])

# #46: consolidate 2 scopes
mcp_st3-workflow_remove_labels(issue_number=46, labels=["scope:git-tooling", "scope:phase-workflow"])
mcp_st3-workflow_add_labels(issue_number=46, labels=["scope:tooling", "scope:workflow"])

# #59: scope:process → scope:workflow
mcp_st3-workflow_remove_labels(issue_number=59, labels=["scope:process"])
mcp_st3-workflow_add_labels(issue_number=59, labels=["scope:workflow"])
```

#### Remove Freeform Duplicates (5 issues)
```bash
# #16: remove tdd, qa, testing (keep type:research, add priority:triage)
# Already added priority:triage above

# #18: remove tdd, qa, tooling (already adding type:epic, type:enhancement)
# Note: Can't remove 'enhancement' until after adding 'type:enhancement'

# #47: remove quality, tech-debt
# Keep type:refactor which already exists

# #19: add missing structured labels
mcp_st3-workflow_add_labels(issue_number=19, labels=["type:docs", "scope:mcp-server"])

# #22: replace type:analysis with type:research
mcp_st3-workflow_remove_labels(issue_number=22, labels=["type:analysis"])
mcp_st3-workflow_add_labels(issue_number=22, labels=["type:research"])
```

### Step 5: Drift Detection Verification

**Run drift detection:**
```bash
mcp_st3-workflow_detect_label_drift()
```

**Expected result:**
- Zero drift between labels.yaml and GitHub
- All issues have mandatory labels (type + priority)
- No freeform labels except approved exceptions

---

## 6. Post-Cleanup Validation

### Checklist

- [ ] labels.yaml updated with 32 labels (27 structured + 5 freeform)
- [ ] GitHub has exactly 32 labels (+ dynamic parent:* labels)
- [ ] All 36 open issues have type label
- [ ] All 36 open issues have priority label
- [ ] Phase labels align with workflows.yaml (6 phases)
- [ ] Scope consolidated to 6 categories
- [ ] Epic detection: #18, #42, #49, #51 have type:epic
- [ ] Triage queue: 8 issues with priority:triage
- [ ] Zero drift detected

### Metrics

**Before:**
- 54 GitHub labels (many redundant)
- 12 issues missing type label
- 8 issues missing priority label
- 13 phase labels (inconsistent with workflows.yaml)
- 11 scope labels (fragmented)

**After:**
- 32 GitHub labels (+ 4 dynamic parent labels)
- 0 issues missing type label
- 0 issues missing priority label (8 in triage)
- 6 phase labels (aligned with workflows.yaml)
- 6 scope labels (consolidated)

**Reduction:** 54 → 32 labels (41% reduction)

---

## 7. Future Enhancements

### Auto-Epic Detection (Issue #60)

**Tooling can enforce:**
```python
def detect_epic_issues():
    """Auto-add type:epic to issues with children"""
    all_issues = list_issues()
    parent_labels = [label for label in list_labels() if label.startswith("parent:issue-")]
    
    for parent_label in parent_labels:
        issue_number = int(parent_label.split("-")[1])
        issue = get_issue(issue_number)
        
        if "type:epic" not in issue.labels:
            add_labels(issue_number, ["type:epic"])
```

### Weekly Triage Review

**Goal:** Zero issues in triage queue

**Process:**
1. Filter: `priority:triage`
2. Review each issue
3. Assign appropriate priority (critical/high/medium/low)
4. Remove `priority:triage` label

### Label Analytics

**Track:**
- Label distribution (which types/priorities most common)
- Time in each phase (phase label timestamps)
- Scope coverage (which scopes underrepresented)
- Triage latency (time between creation and priority assignment)

---

## Summary

**This cleanup plan:**
- ✅ Reduces label count by 41% (54 → 32)
- ✅ Enforces structured labeling (category:value pattern)
- ✅ Aligns phases with workflows.yaml
- ✅ Introduces explicit triage queue
- ✅ Distinguishes feature vs enhancement
- ✅ Auto-detects epic issues
- ✅ Consolidates fragmented scopes
- ✅ Zero information loss (all data preserved or upgraded)

**Ready for execution:** All commands documented, validation criteria defined.
