# Epic #49 Planning: MCP Platform Configurability

**Status:** IN PROGRESS
**Author:** AI Agent + Human
**Created:** 2025-12-26
**Epic:** #49

---

## 1. Child Issue Breakdown

Based on research findings (150+ config items across 10 categories), we define **8 child issues** - one per configuration file:

### Child Issues

| Issue | Config File | Scope | Priority | Blocks |
|-------|-------------|-------|----------|--------|
| **#50** | `config/workflows.yaml` | PHASE_TEMPLATES, issue types, phase sequences, execution modes | CRITICAL | #42 |
| **#51** | `config/labels.yaml` | GitHub label definitions, type/priority/status/phase patterns, colors, sync mechanism | CRITICAL | #42 |
| **#52** | `config/documents.yaml` | TEMPLATES dict, SCOPE_DIRS dict, template paths | MEDIUM | - |
| **#53** | `.st3/quality.yaml` | Pylint/Mypy/Pyright configs, timeouts, thresholds, output patterns | HIGH | #18 |
| **#54** | `config/validation.yaml` | RULES dict (5 template types), component validation rules | HIGH | #18 |
| **#55** | `config/scaffold.yaml` | Valid component types, scaffold phases, file policies | HIGH | #18 |
| **#56** | `config/git.yaml` | Branch types, TDD phases, commit prefixes, protected branches | MEDIUM | - |
| **#57** | `config/constants.yaml` | Magic numbers (timeouts, limits, thresholds), regex patterns | MEDIUM | - |

### Rationale for Structure

**Why 1 config file = 1 issue?**
- ✅ Clean separation of concerns
- ✅ 1-to-1 mapping (clear scope)
- ✅ Independent Pydantic models
- ✅ Parallel implementation possible
- ✅ Clear git history per domain

**Why these groupings?**
- **workflows.yaml**: Core issue type definitions (needed for #42)
- **labels.yaml**: GitHub integration (needed for #42)
- **documents.yaml**: Documentation scaffolding (independent)
- **.st3/quality.yaml**: Static analysis gates (needed for #18)
- **validation.yaml**: Template validation (needed for #18)
- **scaffold.yaml**: File creation policies (needed for #18)
- **git.yaml**: Git conventions (independent)
- **constants.yaml**: Tuneable parameters (independent)

---

## 2. Priority & Dependencies

### Critical Path (Unblocks Issue #42)

```
Epic #49 (Planning)
├── Issue #50: workflows.yaml (CRITICAL) → Unblocks #42
├── Issue #51: labels.yaml (CRITICAL) → Unblocks #42
└── Issue #42 can resume after #50 + #51
```

**Timeline:** 5-7 days for #50 + #51

### Secondary Path (Enables Issue #18)

```
Epic #49 (Planning)
├── Issue #53: .st3/quality.yaml (HIGH) → Enables #18 enforcement
├── Issue #54: validation.yaml (HIGH) → Enables #18 enforcement
└── Issue #55: scaffold.yaml (HIGH) → Enables #18 enforcement
```

**Timeline:** 4-6 days for #53 + #54 + #55

### Tertiary Path (Completes Configurability)

```
Epic #49 (Planning)
├── Issue #52: documents.yaml (MEDIUM)
├── Issue #56: git.yaml (MEDIUM)
└── Issue #57: constants.yaml (MEDIUM)
```

**Timeline:** 3-4 days for #52 + #56 + #57

### Total Timeline

- **Critical (Phase 1):** 5-7 days → Issue #42 unblocked
- **High (Phase 2):** 4-6 days → Issue #18 enabled
- **Medium (Phase 3):** 3-4 days → Full configurability
- **Total:** ~12-17 days (2-3 weeks)

---

## 3. Implementation Approach

### 3.1 Per-Issue Pattern (All 8 follow same flow)

**Phase: TDD**

1. **Design YAML schema** (in design.md)
   - Define structure
   - Document all fields
   - Example configurations

2. **Design Pydantic models**
   - Root model
   - Nested models
   - Field validators
   - Custom validators

3. **Write tests (RED)**
   - Config loading tests
   - Validation tests (valid/invalid configs)
   - Integration tests (manager updates)

4. **Implement (GREEN)**
   - Create `mcp_server/config/<domain>_config.py`
   - Implement Pydantic models
   - Implement config loader
   - Update managers to use config

5. **Refactor**
   - Remove hardcoded constants
   - Clean up imports
   - Update documentation

**Phase: Integration**
- End-to-end workflow tests
- Verify no hardcoded config remains

**Phase: Documentation**
- Config reference docs
- Migration guide (if needed)

### 3.2 Shared Infrastructure

**All issues share:**
- Base config loader pattern
- Pydantic validation approach
- Config file location (`config/` directory)
- Fail-fast validation at startup

**Common decisions:**
- ✅ YAML format (already used in mcp_config.yaml)
- ✅ Pydantic for validation
- ✅ Fail fast if config missing/invalid
- ✅ No backward compatibility (no enforced projects exist)
- ✅ Load config once at startup

### 3.3 Technology Stack

```python
# Each config module follows this pattern:
from pathlib import Path
from pydantic import BaseModel, Field, validator
import yaml

class <Domain>Config(BaseModel):
    # ... fields with validation
    
    @classmethod
    def load(cls, config_path: Path) -> "<Domain>Config":
        content = yaml.safe_load(config_path.read_text())
        return cls(**content)

# Usage in managers:
config = WorkflowConfig.load(Path("config/workflows.yaml"))
```

---

## 4. Success Criteria

### Per Child Issue

- [ ] Config YAML file created with complete schema
- [ ] Pydantic model implemented with validation
- [ ] Config loader implemented
- [ ] Manager/tool updated to use config
- [ ] Hardcoded constants removed from code
- [ ] All tests passing
- [ ] Documentation updated

### Epic Level

- [ ] All 8 config files exist and are complete
- [ ] Zero hardcoded configuration in Python code
- [ ] All tests passing
- [ ] Issue #42 unblocked (after #50 + #51)
- [ ] Issue #18 enabled (after #53 + #54 + #55)
- [ ] Config reference documentation complete

---

## 5. Existing Issues Update

### Issues to Redefine

The following issues already exist but need scope adjustment:

| Issue | Old Scope | New Scope | Action |
|-------|-----------|-----------|--------|
| #50 | "Workflow & Issue Type Configuration" | `config/workflows.yaml` only | Update title + body |
| #51 | "Label Management & GitHub Sync" | `config/labels.yaml` only | Update title + body |
| #52 | "Validation Rules Configuration" | `config/validation.yaml` only | Update title + body |
| #53 | "Quality Gates Configuration" | `.st3/quality.yaml` only | Update title + body |
| #54 | "Scaffold Rules Configuration" | `config/scaffold.yaml` only | Update title + body |
| #55 | "Git Conventions Configuration" | `config/git.yaml` only | Update title + body |

### Issues to Create

| Issue | Config File | Scope |
|-------|-------------|-------|
| #56 | `config/git.yaml` | Branch types, commit prefixes, TDD phases, protected branches |
| #57 | `config/constants.yaml` | Magic numbers, timeouts, regex patterns |

**Wait - #56 overlaps with #55!**

### Corrected Mapping

| Issue | Config File | Scope |
|-------|-------------|-------|
| #50 | `config/workflows.yaml` | PHASE_TEMPLATES, issue types, phases |
| #51 | `config/labels.yaml` | GitHub labels, sync mechanism |
| #52 | `config/validation.yaml` | Template validation rules |
| #53 | `.st3/quality.yaml` | Quality gates (pylint/mypy/pyright) |
| #54 | `config/scaffold.yaml` | Scaffold rules, file policies |
| #55 | `config/git.yaml` | Git conventions (branches, commits, TDD) |
| NEW #56 | `config/documents.yaml` | Document templates, scopes |
| NEW #57 | `config/constants.yaml` | Magic numbers, regex patterns |

---

## 6. Next Steps

### Immediate (In this planning phase)

1. ✅ Define 8 child issues (DONE - this document)
2. Update existing issues #50-#55 with correct scope
3. Create new issues #56-#57
4. Close Epic #49 planning phase

### Phase 1 - Critical (Week 1)

1. Switch to Issue #50 branch (workflows.yaml)
2. Complete Issue #50: discovery → planning → design → tdd → integration → documentation
3. Switch to Issue #51 branch (labels.yaml)
4. Complete Issue #51: discovery → planning → design → tdd → integration → documentation
5. **Issue #42 unblocked** ✅

### Phase 2 - High Priority (Week 2)

1. Complete Issue #53 (.st3/quality.yaml)
2. Complete Issue #52 (validation.yaml)
3. Complete Issue #54 (scaffold.yaml)
4. **Issue #18 enabled** ✅

### Phase 3 - Remaining (Week 3)

1. Complete Issue #55 (git.yaml)
2. Complete Issue #56 (documents.yaml)
3. Complete Issue #57 (constants.yaml)
4. **Full configurability achieved** ✅

---

## 7. Open Questions

None - planning complete based on comprehensive research findings.

---

## Approval

- [ ] Human approval: Planning complete, child issues defined correctly?
