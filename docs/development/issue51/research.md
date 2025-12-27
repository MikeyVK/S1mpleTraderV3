# Issue #51 Discovery: Label Management System - SimpleTraderV3

**Phase:** Discovery  
**Status:** COMPLETE
**Date:** 2025-12-27  
**Issue:** #51 - Config: Label Management System (labels.yaml)

---

## Research Objectives

1. Understand current label usage in codebase
2. Analyze WorkflowConfig pattern from Issue #50 as reference
3. Identify all label categories and patterns
4. Document GitHub label API requirements
5. Define labels.yaml schema structure

---

## Current Label Usage Analysis

### Files Using Labels

**MCP Tools (`mcp_server/tools/label_tools.py`):**
- ✅ `ListLabelsTool` - Lists all repository labels
- ✅ `CreateLabelTool` - Creates new labels
- ✅ `DeleteLabelTool` - Deletes labels
- ✅ `AddLabelsTool` - Adds labels to issues
- ✅ `RemoveLabelsTool` - Removes labels from issues

**GitHub Adapter (`mcp_server/platform/github_adapter.py`):**
- Methods: `create_label()`, `get_labels()`, `delete_label()`, `add_labels_to_issue()`, `remove_labels_from_issue()`
- Uses PyGithub's `Label` class

**GitHub Manager (`mcp_server/managers/github_manager.py`):**
- Delegates label operations to adapter layer

**Issue Tools (`mcp_server/tools/issue_tools.py`):**
- Accepts `labels` parameter in create/update operations

### Current State: **No Validation**

❌ **No centralized label registry**  
❌ **No validation of label patterns**  
❌ **No label constants or enums**  
❌ **Labels are hardcoded strings in documentation only**

**Key Finding:** Tools accept ANY string as label without validation - creates risk of typos and inconsistency.

---

## Label Categories & Patterns

### Documentation Analysis

**Two primary docs found:**
1. `docs/development/44/IMPLEMENTATION_PLAN.md` (41 labels, 8 categories)
2. `docs/reference/STANDARDS.md` (34 labels, 4 categories)

### Complete Label Inventory

#### Type Labels (`#1D76DB` - Blue)
- `type:feature` - New feature implementation
- `type:bug` - Something isn't working
- `type:refactor` - Code restructuring
- `type:docs` - Documentation changes
- `type:infra` - Infrastructure/tooling
- `type:test` - Test-related changes
- `type:design` - Design phase work
- `type:discussion` - Requires discussion
- `type:tech-debt` - Technical debt cleanup
- `type:validation` - Validation/enforcement work

#### Priority Labels (Red scale)
- `priority:critical` (`#B60205`) - Urgent, blocking
- `priority:high` (`#D93F0B`) - Important, soon
- `priority:medium` (`#FBCA04`) - Normal priority
- `priority:low` (`#BFD4F2`) - Nice to have
- `priority:triage` (`#EDEDED`) - Needs prioritization

#### Phase Labels (`#0E8A16` - Green)
- `phase:discovery` - Research/analysis phase
- `phase:discussion` - Requires team discussion
- `phase:planning` - Planning phase
- `phase:design` - Design phase
- `phase:review` - Under review
- `phase:approved` - Design approved
- `phase:red` - TDD RED phase (failing tests)
- `phase:green` - TDD GREEN phase (passing tests)
- `phase:refactor` - TDD REFACTOR phase
- `phase:implementation` - Implementation phase
- `phase:verification` - Verification phase
- `phase:documentation` - Documentation phase
- `phase:done` - Complete

#### Status Labels (`#FBCA04` - Yellow)
- `status:blocked` - Blocked by dependency
- `status:needs-info` - Requires more information
- `status:ready-for-review` - Ready for review
- `needs:discussion` - Needs discussion
- `needs:design` - Needs design work
- `needs:info` - Needs more information

#### Scope Labels
- `scope:architecture` - Architectural changes
- `scope:component` - Component-level changes
- `scope:mcp-server` - MCP server scope
- `scope:platform` - Platform scope
- `scope:tooling` - Tooling scope
- `scope:process` - Process scope
- `scope:workflow` - Workflow scope

#### Parent/Child Labels (Dynamic)
- `parent:issue-XX` - Parent issue reference
- Pattern: `parent:issue-{number}`

### Label Pattern Structure

**Common Pattern:** `category:value`

```
{category}:{value}
│          └─ Specific value (lowercase, hyphenated)
└─ Category prefix (type/priority/status/phase/scope/component/effort/parent)
```

---

## GitHub Label API Requirements

### Label Attributes

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Cannot be empty, case-sensitive, emoji supported |
| `color` | string | **Yes** | 6-char hex **WITHOUT** `#` (e.g., `f29513`) |
| `description` | string | No | Max 100 characters |

### Color Format (CRITICAL)

**GitHub API expects hex WITHOUT `#` prefix:**
- ✅ Correct: `"e10c02"`
- ❌ Wrong: `"#e10c02"`

**labels.yaml must store colors WITHOUT `#`**

### PyGithub Methods

```python
# Repository level
repo.create_label(name: str, color: str, description: str = "")
repo.get_labels()  # PaginatedList[Label]

# Label object
label.edit(name: str, color: str, description: str)
label.delete()

# Issue level
issue.add_to_labels(*labels)  # str or Label objects
issue.set_labels(*labels)  # Replace all
```

---

## WorkflowConfig Pattern Reference

**File:** `mcp_server/managers/project_manager.py`

### Structure
```python
@dataclass
class Workflow:
    name: str
    phases: list[str]

class WorkflowConfig(BaseModel):
    version: str
    workflows: dict[str, Workflow]
    
    @classmethod
    def load(cls, path: Path | None = None) -> "WorkflowConfig":
        if path is None:
            path = Path(".st3/workflows.yaml")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

# Module-level singleton
workflow_config = WorkflowConfig.load()
```

### Key Patterns to Reuse

1. **Pydantic BaseModel** for validation
2. **@dataclass** for nested structures
3. **@classmethod load()** for YAML loading
4. **Module-level singleton**
5. **Type hints** with `dict[str, T]`
6. **Custom validators** with `@field_validator`
7. **Default path** in `.st3/` directory

---

## Proposed labels.yaml Schema

### YAML Structure

```yaml
version: "1.0"

labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature implementation"
  
  - name: "type:bug"
    color: "1D76DB"
    description: "Something isn't working"
```

### Python Classes (Planned)

```python
@dataclass
class Label:
    name: str
    color: str
    description: str = ""

class LabelConfig(BaseModel):
    version: str
    labels: list[Label]
    
    def get_label(self, name: str) -> Label | None:
        ...
    
    def sync_to_github(self, github_adapter) -> dict:
        ...
```

---

## Implementation Scope

### In Scope

✅ `.st3/labels.yaml` configuration file  
✅ `LabelConfig` Pydantic model  
✅ `Label` dataclass  
✅ YAML loading with validation  
✅ GitHub sync mechanism  
✅ Label validation in tools  
✅ Module-level singleton pattern  
✅ Tests: config loading, validation, GitHub sync  

### Out of Scope

❌ Workflows (Issue #50 - COMPLETE)  
❌ Git conventions (Issue #55)  
❌ Automatic label application  
❌ Label analytics/reporting  

---

## Key Design Decisions

### Decision 1: Color Storage Format

**Decision:** Store colors **WITHOUT** `#` in YAML  
**Rationale:** GitHub API requires hex without `#`  
**Impact:** Users must omit `#` when editing labels.yaml  

### Decision 2: Label List vs Category Dict

**Decision:** Flat list of labels  
**Rationale:** Simpler schema, mirrors GitHub's flat structure  

### Decision 3: Validation Strategy

**Decision:** Pydantic validation + custom validators  
**Rationale:** Same pattern as WorkflowConfig, proven approach  

### Decision 4: Singleton Pattern

**Decision:** Module-level variable (not class singleton)  
**Rationale:** Matches WorkflowConfig pattern  

---

## Open Questions

### Q1: Validate label names against pattern?

**Options:**
- A: Enforce `category:value` pattern
- B: Allow freeform names with warnings

**Recommendation:** Option B (flexibility)

### Q2: Handle missing labels in YAML?

**Options:**
- A: Strict - reject operation
- B: Warn and allow (GitHub may have label)

**Recommendation:** Option B with logging

### Q3: Auto-sync on server startup?

**Options:**
- A: Auto-sync labels to GitHub
- B: Manual sync via dedicated tool

**Recommendation:** Option B (explicit sync tool)

---

## Risk Analysis

### Risk 1: Color Format Confusion
**Risk:** Users add `#` prefix  
**Mitigation:** Validation strips `#` if present  
**Severity:** Low  

### Risk 2: Label Sync Conflicts
**Risk:** GitHub has labels not in YAML  
**Mitigation:** Sync tool shows diff preview  
**Severity:** Medium  

### Risk 3: Label Name Typos
**Risk:** Typo in labels.yaml breaks workflows  
**Mitigation:** Validation at load time  
**Severity:** Medium  

---

## Success Criteria

### Discovery Phase Complete When:

- [x] Current label usage analyzed
- [x] WorkflowConfig pattern understood
- [x] All label categories identified
- [x] GitHub API requirements documented
- [x] labels.yaml schema designed
- [x] Open questions documented
- [x] Risk analysis complete

### Next Phase: Planning

**Deliverables:**
1. Detailed API design (LabelConfig, Label classes)
2. Method signatures with type hints
3. Test strategy
4. Implementation sequence
5. Migration plan

---

## References

- **Issue #50:** WorkflowConfig pattern implementation
- **Issue #3:** Original label tool implementation
- **docs/reference/STANDARDS.md:** Current label documentation
- **docs/development/44/IMPLEMENTATION_PLAN.md:** Comprehensive label list
- **GitHub API:** https://docs.github.com/en/rest/issues/labels
- **PyGithub:** https://pygithub.readthedocs.io/
