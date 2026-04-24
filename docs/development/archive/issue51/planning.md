# Issue #51 Planning: Label Management System

**Phase:** Planning  
**Status:** IN PROGRESS  
**Date:** 2025-12-28  
**Issue:** #51 - Config: Label Management System (labels.yaml)

---

## 1. Work Breakdown

### Phase 1: Configuration Infrastructure (2-3 hours)
**Tasks:**
- Create `.st3/labels.yaml` with 60+ labels from research
- Create `mcp_server/config/label_config.py` structure
- Implement YAML loading + Pydantic validation
- Add color format validator (reject `#` prefix)
**Deliverables:** labels.yaml, LabelConfig class, tests

### Phase 2: Label Operations (2 hours)
**Tasks:**
- Add lookup methods (by name, by category)
- Add validation methods (name pattern, exists)
- Create GitHub sync mechanism interface
**Deliverables:** Query/validation methods, sync contract

### Phase 3: Tool Integration (1-2 hours)
**Tasks:**
- Update CreateLabelTool with validation
- Update AddLabelsTool with validation
- Add SyncLabelsToGitHubTool
**Deliverables:** Updated tools, sync tool

### Phase 4: Testing & Documentation (2 hours)
**Tasks:**
- Unit tests (loading, validation, queries)
- Integration tests (GitHub sync simulation)
- Update STANDARDS.md
**Deliverables:** 100% coverage, documentation

**Total Effort:** 7-9 hours

---

## 2. API Contracts

### 2.1 Configuration Classes

```python
# Label dataclass (simple data holder)
@dataclass
class Label:
    name: str
    color: str  # 6-char hex WITHOUT #
    description: str = ""

# Main config class (Pydantic validation)
class LabelConfig(BaseModel):
    version: str
    labels: list[Label]
    
    @classmethod
    def load(cls, path: Path | None = None) -> "LabelConfig"
    
    def get_label(self, name: str) -> Label | None
    def get_labels_by_category(self, category: str) -> list[Label]
    def validate_label_name(self, name: str) -> bool
    def sync_to_github(self, github_adapter) -> dict[str, Any]
```

### 2.2 Validation Rules

**Color validation:**
- Regex: `^[0-9a-fA-F]{6}$`
- Reject `#` prefix with clear error
- Case-insensitive hex

**Name validation (strict mode from Q1):**
- Regex: `^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$`
- Allowed freeform list for exceptions (`good first issue`, etc.)

### 2.3 GitHub Sync Contract

```python
def sync_to_github(self, github_adapter) -> dict[str, Any]:
    """
    Returns:
    {
        "created": ["type:new-label"],
        "updated": ["type:feature"],  # color/description changed
        "skipped": ["type:existing"],  # unchanged
        "errors": []
    }
    """
```

---

## 3. Test Strategy

### 3.1 Unit Tests

**Config Loading:**
- ✅ Load valid labels.yaml
- ✅ Reject missing version field
- ✅ Reject invalid color format (`#abc123`)
- ✅ Reject duplicate label names
- ✅ Reject empty label name

**Validation:**
- ✅ Valid label names (all categories)
- ✅ Invalid label names (no colon, wrong category)
- ✅ Freeform label exceptions

**Queries:**
- ✅ get_label() by name
- ✅ get_labels_by_category() filters correctly
- ✅ Non-existent label returns None

### 3.2 Integration Tests

**GitHub Sync (mocked):**
- ✅ Create new labels
- ✅ Update existing labels (color change)
- ✅ Skip unchanged labels
- ✅ Handle API errors gracefully

**Tool Integration:**
- ✅ CreateLabelTool validates against labels.yaml
- ✅ AddLabelsTool rejects undefined labels (strict mode)
- ✅ SyncLabelsToGitHubTool shows diff preview

### 3.3 Coverage Target

**100% coverage** for:
- LabelConfig class
- All validation logic
- Sync mechanism

---

## 4. Labels YAML Content

### 4.1 Label Categories to Include

**Type (10 labels):** feature, bug, refactor, docs, infra, test, design, discussion, tech-debt, validation, epic, hotfix
**Priority (5 labels):** critical, high, medium, low, triage
**Phase (13 labels):** discovery, discussion, planning, design, review, approved, red, green, refactor, implementation, verification, documentation, done
**Status (6 labels):** blocked, needs-info, ready-for-review
**Scope (8 labels):** architecture, component, mcp-server, platform, tooling, process, workflow, reference
**Parent (dynamic):** Pattern documented, no predefined labels

**Total: ~50 concrete labels**

### 4.2 Color Palette

**Consistency with research:**
- Type: `1D76DB` (blue)
- Priority Critical: `B60205` (red)
- Priority High: `D93F0B` (orange)
- Priority Medium: `FBCA04` (yellow)
- Priority Low: `BFD4F2` (light blue)
- Phase: `0E8A16` (green)
- Status: `FBCA04` (yellow)

### 4.3 Freeform Exceptions

Allow these non-pattern labels:
- `good first issue`
- `help wanted`
- `wontfix`
- `duplicate`
- `invalid`

---

## 5. Migration Strategy

### 5.1 Phase 1: Additive (No Breaking Changes)

1. **Create labels.yaml** with all current labels
2. **Add LabelConfig** (optional usage initially)
3. **Update tools** to validate if labels.yaml exists
4. **Sync existing GitHub labels** to labels.yaml

### 5.2 Phase 2: Gradual Enforcement

1. **Warning mode:** Tools warn if label not in YAML
2. **Observation period:** 1-2 weeks
3. **Strict mode:** Tools reject undefined labels

### 5.3 Tool Updates Required

**Minimal changes:**
- `CreateLabelTool`: Add validation call
- `AddLabelsTool`: Add validation call
- **New:** `SyncLabelsToGitHubTool`

**No changes needed:**
- `ListLabelsTool`
- `DeleteLabelTool`
- `RemoveLabelsTool`

---

## 6. Implementation Sequence

### Day 1: Foundation
1. Create `.st3/labels.yaml` with full label set
2. Create `LabelConfig` + `Label` classes
3. Implement `load()` method with Pydantic validation
4. Tests: loading, validation

### Day 2: Operations
1. Implement query methods (`get_label`, `get_labels_by_category`)
2. Implement validation methods
3. Tests: queries, validation logic

### Day 3: GitHub Integration
1. Implement `sync_to_github()` method
2. Create `SyncLabelsToGitHubTool`
3. Update existing tools with validation
4. Tests: sync logic, tool integration

### Day 4: Polish & Documentation
1. 100% test coverage verification
2. Update `docs/reference/STANDARDS.md`
3. Add labels.yaml schema documentation
4. Quality gates: 10.0/10 pylint

---

## 7. Success Criteria

### Must Have
- [ ] `.st3/labels.yaml` created with 50+ labels
- [ ] `LabelConfig` loads and validates YAML
- [ ] Color validation rejects `#` prefix
- [ ] Name validation enforces pattern (with exceptions)
- [ ] `get_label()` and `get_labels_by_category()` work
- [ ] `sync_to_github()` creates/updates labels
- [ ] `SyncLabelsToGitHubTool` shows diff preview
- [ ] Existing tools validate labels
- [ ] 100% test coverage
- [ ] 10.0/10 pylint
- [ ] Documentation updated

### Nice to Have
- [ ] Label usage statistics
- [ ] Sync dry-run mode
- [ ] Label rename migration helper

---

## 8. Open Decisions (from Research)

### Decision 1: Name Validation Mode
**Decided:** Strict enforcement (Option A) with freeform exceptions list

### Decision 2: Missing Label Handling
**Decided:** Warn during migration, then strict mode after sync

### Decision 3: Sync Trigger
**Decided:** Manual sync via dedicated tool (explicit control)

---

## 9. Risks & Mitigations

### Risk: Incomplete Label Migration
**Mitigation:** Fetch all GitHub labels, compare with YAML, report missing

### Risk: Color Format Confusion
**Mitigation:** Validator REJECTS `#` prefix with clear error message

### Risk: Breaking Existing Workflows
**Mitigation:** Additive migration, warnings before strict enforcement

---

## 10. References

- **Research:** docs/development/issue51/research.md
- **Issue #50:** WorkflowConfig reference implementation
- **GitHub API:** https://docs.github.com/en/rest/issues/labels
