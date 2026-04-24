# Issue #55: Git Conventions Configuration - Implementation Planning

**Status:** DRAFT
**Author:** GitHub Copilot (Claude Sonnet 4.5)
**Created:** 2026-01-13
**Issue:** #55 - Git Conventions Configuration
**Phase:** Planning

---

## 1. Overview

### 1.1 Purpose

This document provides the TDD implementation strategy for Issue #55: externalizing 6 hardcoded git conventions into `.st3/git.yaml` configuration. This is a **planning** document - design decisions and code specifications belong in the design phase.

### 1.2 Implementation Approach

- **Strategy:** Test-Driven Development (RED → GREEN → REFACTOR)
- **Build Order:** Config foundation → GitManager integration → PolicyEngine integration
- **Phases:** Planning → Design → TDD → Integration → Documentation
- **Quality Gates:** Pytest coverage, type checking, validation tests

### 1.3 Related Documents

- [research.md](docs/development/issue55/research.md) - 6 hardcoded conventions identified
- [Design Phase Output](docs/development/issue55/design.md) - YAML schema, Pydantic models (NEXT PHASE)
- [Epic #49 Context](https://github.com/user/repo/issues/49) - Configuration Externalization Epic

---

## 2. TDD Implementation Strategy

### 2.1 Red-Green-Refactor Cycles

**Cycle 1: Config Foundation**
1. **RED:** Test `.st3/git.yaml` loading fails with FileNotFoundError
2. **GREEN:** Create empty git.yaml, implement basic loader
3. **RED:** Test git.yaml validation fails with invalid schema
4. **GREEN:** Implement Pydantic model with validation
5. **RED:** Test cross-validation fails (e.g., invalid phase in commit_prefix_map)
6. **GREEN:** Implement cross-validation logic
7. **REFACTOR:** Add singleton pattern (ClassVar!), helper methods

**Cycle 2: GitManager Integration (Branch Types)**
1. **RED:** Test create_branch() with config-based branch type validation
2. **GREEN:** Refactor create_branch() to use GitConfig.get_instance()
3. **REFACTOR:** Remove hardcoded branch_types list

**Cycle 3: GitManager Integration (TDD Phases)**
1. **RED:** Test commit_tdd_phase() with config-based phase validation
2. **GREEN:** Refactor commit_tdd_phase() to use GitConfig
3. **RED:** Test commit prefix mapping from config
4. **GREEN:** Refactor prefix logic to use commit_prefix_map
5. **REFACTOR:** Remove hardcoded prefix_map dict

**Cycle 4: GitManager Integration (Protected Branches)**
1. **RED:** Test delete_branch() with config-based protection
2. **GREEN:** Refactor delete_branch() to use GitConfig
3. **REFACTOR:** Remove hardcoded protected_branches list

**Cycle 5: GitManager Integration (Branch Name Pattern)**
1. **RED:** Test create_branch() pattern validation from config
2. **GREEN:** Refactor pattern check to use GitConfig.branch_name_pattern
3. **REFACTOR:** Remove hardcoded regex pattern

**Cycle 6: PolicyEngine Integration (Commit Prefixes)**
1. **RED:** Test _decide_commit() derives prefixes from GitConfig
2. **GREEN:** Refactor _decide_commit() to derive from commit_prefix_map
3. **REFACTOR:** Remove hardcoded tdd_prefixes tuple
4. **REFACTOR:** Fix prefix inconsistency bug (test: vs red:)

**Cycle 7: Integration Tests**
1. **RED:** End-to-end workflow tests fail with missing config
2. **GREEN:** Full workflow tests pass with git.yaml
3. **REFACTOR:** Cleanup, documentation

### 2.2 Commit Strategy

**Commit Pattern:** `{phase}: {description}`

**Example Commits:**
- `red: test git.yaml loading fails with FileNotFoundError`
- `green: implement GitConfig Pydantic model and loader`
- `refactor: add singleton pattern with ClassVar to GitConfig`
- `red: test create_branch validates branch types from config`
- `green: refactor GitManager.create_branch to use GitConfig`
- `refactor: remove hardcoded branch_types list from git_manager.py`

**Micro-Commits:** One test → one implementation → one refactor (small, atomic commits)

---

## 3. Build Order

### 3.1 Component Dependencies

```
Layer 1: Config Foundation
├── .st3/git.yaml (data file)
├── GitConfig Pydantic model (mcp_server/config/git_config.py)
└── Config tests (tests/mcp_server/config/test_git_config.py)

Layer 2: GitManager Integration
├── Refactor create_branch() - branch_types (Convention #1), branch_name_pattern (Convention #5)
├── Refactor commit_tdd_phase() - tdd_phases (Convention #2), commit_prefix_map (Convention #3)
├── Refactor delete_branch() - protected_branches (Convention #4)
└── Integration tests (tests/mcp_server/managers/test_git_manager_config.py)

Layer 3: PolicyEngine Integration
├── Refactor _decide_commit() - derive prefixes from commit_prefix_map (Convention #6)
├── Fix prefix inconsistency bug (Convention #3 vs #6: test: vs red:)
└── Integration tests (tests/mcp_server/core/test_policy_engine_git_config.py)

Layer 4: Git Tools Integration
├── Refactor branch type regex - use config (Convention #7)
├── Refactor commit prefix detection - use config (Convention #8)
├── Remove DRY violations (sync with Conventions #1 and #3)
└── Integration tests (tests/mcp_server/tools/test_git_tools_config.py)

Layer 5: PR Tools Integration
├── Refactor default base branch - use config (Conventions #9, #10, #11)
├── Update pr_tools.py (2 methods) and pr_dto.py (1 field)
├── Ensure backward compatibility
└── Integration tests (tests/mcp_server/tools/test_pr_tools_config.py)

Layer 6: Integration & Documentation
├── End-to-end workflow tests
├── Reference documentation
└── Migration guide
```

### 3.2 Implementation Sequence

**Phase 1: Foundation (Design → TDD)**
1. **Design Phase:** Create design.md with YAML schema, Pydantic model design
2. **TDD Cycle 1:** Implement config loading with validation

**Phase 2: GitManager (TDD)**
1. **TDD Cycle 2:** Branch type validation from config (Convention #1)
2. **TDD Cycle 3:** TDD phase + prefix mapping from config (Conventions #2, #3)
3. **TDD Cycle 4:** Protected branch validation from config (Convention #4)
4. **TDD Cycle 5:** Branch name pattern from config (Convention #5)

**Phase 3: PolicyEngine (TDD)**
1. **TDD Cycle 6:** Commit prefix derivation + bug fix (Convention #6, fix #3 vs #6 inconsistency)

**Phase 4: Git Tools (TDD)**
1. **TDD Cycle 7:** Branch type regex from config (Convention #7, eliminate DRY violation with #1)
2. **TDD Cycle 8:** Commit prefix detection from config (Convention #8, eliminate DRY violation with #3)

**Phase 5: PR Tools (TDD)**
1. **TDD Cycle 9:** Default base branch from config (Conventions #9, #10, #11)

**Phase 6: Integration**
1. **TDD Cycle 10:** End-to-end tests
2. Quality gate validation

**Phase 7: Documentation**
1. Reference docs (git.yaml schema)
2. Migration guide (how to customize)

---

## 4. File Changes

### 4.1 New Files (9 files)

**Configuration:**
1. `.st3/git.yaml` - Git conventions configuration (YAML data file)

**Implementation:**
2. `mcp_server/config/git_config.py` - GitConfig Pydantic model + singleton loader

**Tests:**
3. `tests/mcp_server/config/test_git_config.py` - Config loading tests
4. `tests/mcp_server/managers/test_git_manager_config.py` - GitManager config integration tests
5. `tests/mcp_server/core/test_policy_engine_git_config.py` - PolicyEngine config integration tests
6. `tests/mcp_server/tools/test_git_tools_config.py` - Git tools config integration tests (NEW)
7. `tests/mcp_server/tools/test_pr_tools_config.py` - PR tools config integration tests (NEW)
8. `tests/integration/test_git_workflow_config.py` - End-to-end workflow tests

**Documentation:**
9. `docs/development/issue55/design.md` - Component designs (NEXT PHASE - design phase output)

### 4.2 Modified Files (5 files)

**Core Changes:**
1. `mcp_server/managers/git_manager.py` - 5 methods refactored (Conventions #1-5):
   - Line 38: `create_branch()` - branch type validation (Convention #1)
   - Line 46: `create_branch()` - branch name pattern (Convention #5)
   - Line 89: `commit_tdd_phase()` - TDD phase validation (Convention #2)
   - Line 99: `commit_tdd_phase()` - commit prefix mapping (Convention #3)
   - Line 206: `delete_branch()` - protected branch check (Convention #4)
   
2. `mcp_server/core/policy_engine.py` - 1 method refactored (Convention #6):
   - Line 123: `_decide_commit()` - derive TDD prefixes from config (fixes #3 vs #6 inconsistency)

3. `mcp_server/tools/git_tools.py` - 2 locations refactored (Conventions #7, #8):
   - Line 153: Branch type regex - use config (Convention #7, eliminates DRY violation with #1)
   - Lines 173-179: Commit prefix detection - use config (Convention #8, eliminates DRY violation with #3)

4. `mcp_server/tools/pr_tools.py` - 2 methods refactored (Conventions #9, #10):
   - Line 69: `create_pr()` - default base branch from config (Convention #9)
   - Line 143: `merge_pr()` - default base branch from config (Convention #10)

5. `mcp_server/dtos/pr_dto.py` - 1 field refactored (Convention #11):
   - Line 17: `base` field default - from config (Convention #11)

**Summary:**
- **11 hardcoded conventions** removed (researched in research.md Section 2.5)
- **3 DRY violations** eliminated (branch types, commit prefixes, default base branch)
- **1 critical bug** fixed (prefix inconsistency between GitManager and PolicyEngine)

---

## 5. Test Coverage Plan

### 5.1 Unit Tests

**Config Loading (test_git_config.py):**
- ✅ Test successful loading from .st3/git.yaml
- ✅ Test FileNotFoundError when git.yaml missing
- ✅ Test validation error on invalid YAML syntax
- ✅ Test validation error on invalid schema (missing required fields)
- ✅ Test cross-validation: commit_prefix_map keys ⊆ tdd_phases
- ✅ Test cross-validation: branch_name_pattern is valid regex
- ✅ Test cross-validation: protected_branches non-empty
- ✅ Test singleton pattern: multiple calls return same instance
- ✅ Test helper methods: has_branch_type(), has_phase(), get_prefix()

**GitManager Integration (test_git_manager_config.py):**
- ✅ Test create_branch() validates branch types from config
- ✅ Test create_branch() validates branch name pattern from config
- ✅ Test commit_tdd_phase() validates phases from config
- ✅ Test commit_tdd_phase() maps prefixes from config
- ✅ Test delete_branch() checks protected branches from config
- ✅ Test error messages reference config file location

**PolicyEngine Integration (test_policy_engine_git_config.py):**
- ✅ Test _decide_commit() derives prefixes from commit_prefix_map
- ✅ Test prefix consistency: GitManager generates same prefixes PolicyEngine validates
- ✅ Test bug fix: "red:" prefix works (not "test:")

### 5.2 Integration Tests

**End-to-End Workflow (test_git_workflow_config.py):**
- ✅ Test complete feature workflow with config-based validation
- ✅ Test custom branch type added to git.yaml works immediately
- ✅ Test custom TDD phase added to git.yaml works immediately
- ✅ Test modified protected branches respected
- ✅ Test modified branch name pattern enforced

### 5.3 Coverage Target

- **Line Coverage:** >95% for new code (git_config.py)
- **Branch Coverage:** 100% for validation logic
- **Integration Coverage:** All 11 hardcoded conventions tested with config (5 files refactored)

---

## 6. Quality Gates

### 6.1 Pre-Integration Checklist

**Code Quality:**
- [ ] All tests passing (pytest shows 100% pass rate)
- [ ] Type hints complete (mypy --strict passes)
- [ ] No hardcoded conventions remaining (11 conventions eliminated):
  - [ ] git_manager.py: Conventions #1-5 removed
  - [ ] policy_engine.py: Convention #6 removed (prefix bug fixed)
  - [ ] git_tools.py: Conventions #7-8 removed (DRY violations eliminated)
  - [ ] pr_tools.py: Conventions #9-10 removed
  - [ ] pr_dto.py: Convention #11 removed
- [ ] Singleton pattern uses ClassVar (not single underscore!)
- [ ] Cross-validation implemented (commit_prefix_map references valid phases)

**Test Quality:**
- [ ] Config loading tests cover happy path + 5 error cases
- [ ] GitManager integration tests cover all 5 refactored methods (Conventions #1-5)
- [ ] PolicyEngine integration tests verify prefix derivation (Convention #6 + bug fix)
- [ ] Git tools integration tests verify regex + detection from config (Conventions #7-8)
- [ ] PR tools integration tests verify default base branch from config (Conventions #9-11)
- [ ] End-to-end workflow tests demonstrate config flexibility
- [ ] Coverage report shows >95% line coverage for git_config.py

**Documentation:**
- [ ] design.md documents YAML schema with examples (all 11 conventions)
- [ ] design.md documents Pydantic model with field descriptions
- [ ] design.md documents cross-validation rules
- [ ] design.md documents DRY violation fixes (Conventions #7-8 sync with #1, #3)
- [ ] Inline comments explain singleton pattern (ClassVar gotcha)
- [ ] Docstrings follow project conventions

### 6.2 Quality Gate Validation

**Run Before Integration Phase:**
```bash
# Full test suite
pytest tests/ -v

# Coverage report
pytest tests/ --cov=mcp_server/config/git_config --cov-report=term-missing

# Type checking
mypy mcp_server/config/git_config.py --strict

# Validation: No hardcoded conventions (11 total)
# GitManager (Conventions #1-5)
grep -n '"feature"' mcp_server/managers/git_manager.py           # Should find 0 results
grep -n '"red"' mcp_server/managers/git_manager.py               # Should find 0 results
grep -n 'prefix_map' mcp_server/managers/git_manager.py          # Should find 0 results (dict)
grep -n 'protected_branches' mcp_server/managers/git_manager.py  # Should find 0 results (list)
grep -n 'r"\^' mcp_server/managers/git_manager.py                # Should find 0 results (regex)

# PolicyEngine (Convention #6)
grep -n 'tdd_prefixes' mcp_server/core/policy_engine.py          # Should find 0 results

# Git Tools (Conventions #7-8)
grep -n 'feature\|fix\|refactor' mcp_server/tools/git_tools.py   # Should find 0 results (regex)
grep -n 'startswith.*test:' mcp_server/tools/git_tools.py        # Should find 0 results (if-elif)

# PR Tools (Conventions #9-11)
grep -n 'default="main"' mcp_server/tools/pr_tools.py            # Should find 0 results
grep -n 'default="main"' mcp_server/dtos/pr_dto.py               # Should find 0 results
```

---

## 7. Phase Transitions

### 7.1 Planning → Design Transition

**Blocking Condition:** Planning document approved (this document)

**Force Transition Required:** YES (design not in refactor workflow)
```bash
force_phase_transition(
    branch="refactor/55-git-yaml",
    to_phase="design",
    skip_reason="Custom design phase required before TDD. Refactor workflow normally skips dedicated design (research → planning → tdd), but Issue #55 requires detailed YAML schema design + Pydantic model design before implementation.",
    human_approval="User explicitly requested: 'ik wil na de planning fase een overgang naar een ingepaste design fase forceren'"
)
```

**Design Phase Deliverable:** design.md with:
- Complete git.yaml schema (all 5 conventions)
- GitConfig Pydantic model design (fields, types, validators)
- Cross-validation rule specifications
- Helper method signatures
- Integration point designs (GitManager, PolicyEngine)

### 7.2 Design → TDD Transition

**Blocking Condition:** design.md complete and approved

**Normal Transition:** YES (TDD is next phase in refactor workflow)
```bash
transition_phase(
    branch="refactor/55-git-yaml",
    to_phase="tdd"
)
```

**TDD Phase Entry Criteria:**
- design.md exists with complete specifications
- YAML schema documented with examples
- Pydantic model designed (including ClassVar singleton!)
- All integration points identified

### 7.3 TDD → Integration Transition

**Blocking Condition:** All TDD cycles complete (Cycles 1-10)

**Entry Criteria:**
- All unit tests passing (config, GitManager, PolicyEngine, git tools, PR tools)
- All 11 hardcoded conventions removed:
  - ✅ git_manager.py: Conventions #1-5 eliminated
  - ✅ policy_engine.py: Convention #6 eliminated + bug fixed
  - ✅ git_tools.py: Conventions #7-8 eliminated (DRY violations fixed)
  - ✅ pr_tools.py + pr_dto.py: Conventions #9-11 eliminated
- Singleton pattern implemented with ClassVar
- Prefix inconsistency bug fixed
- DRY violations eliminated (3 duplications removed)

**Exit Criteria:**
- End-to-end integration tests passing
- Coverage >95% for new code
- Quality gates passed (see section 6.2)
- All 11 grep validations return 0 results

### 7.4 Integration → Documentation Transition

**Blocking Condition:** Quality gates passed, all tests green

**Documentation Phase Deliverables:**
- Reference docs: git.yaml schema guide (all 11 conventions documented)
- Migration guide: How to customize git conventions
- Update Epic #49 progress tracker (4/8 issues complete)

---

## 8. Risk Mitigation

### 8.1 Identified Risks

**Risk 1: Pydantic v2 Singleton Bug**
- **Impact:** ClassVar pattern not used → ModelPrivateAttr conversion
- **Mitigation:** Lessons learned from Issue #54 documented in research.md Section 3.3
- **Action:** Use `singleton_instance: ClassVar[Optional[GitConfig]] = None`
- **Validation:** Test immediately after implementation (pytest test_git_config.py)

**Risk 2: Prefix Inconsistency Bug (Convention #3 vs #6)**
- **Impact:** GitManager generates "test:" but PolicyEngine validates "red:" - commits would be BLOCKED!
- **Mitigation:** Documented in research.md Section 2.5 as critical finding
- **Action:** Derive PolicyEngine prefixes from commit_prefix_map (single source of truth)
- **Validation:** Integration test verifies GitManager + PolicyEngine consistency

**Risk 3: DRY Violations (Conventions #1+#7, #3+#8, #9+#10+#11)**
- **Impact:** Branch types/prefixes/base branch hardcoded in multiple locations → sync issues
- **Mitigation:** Documented in research.md Section 2.5 as synchronization risk
- **Action:** All 3 DRY violations eliminated by using single config source
- **Validation:** Grep checks confirm no duplicated literals remain (section 6.2)

**Risk 4: Incomplete Hardcoded Convention Removal**
- **Impact:** Some hardcoded values remain after refactor (11 conventions across 5 files)
- **Mitigation:** Comprehensive grep validation in quality gates (section 6.2)
- **Action:** Search for ALL 11 conventions' literal strings before integration
- **Validation:** Manual code review + 11 automated grep checks (all must return 0 results)

**Risk 5: Breaking Changes to Existing Workflows**
- **Impact:** Changing git conventions breaks existing branches/PRs
- **Mitigation:** Default git.yaml values match current hardcoded values
- **Action:** Integration tests verify backward compatibility
- **Validation:** Run full test suite (1097 tests) before integration

### 8.2 Rollback Plan

**If Integration Fails:**
1. Revert git_config.py (remove new file)
2. Revert git_manager.py changes (restore hardcoded lists)
3. Revert policy_engine.py changes (restore tdd_prefixes tuple)
4. Delete .st3/git.yaml
5. All tests should return to 1097/1097 passing

**Rollback Validation:**
```bash
git checkout refactor/55-git-yaml -- mcp_server/managers/git_manager.py
git checkout refactor/55-git-yaml -- mcp_server/core/policy_engine.py
rm mcp_server/config/git_config.py
rm .st3/git.yaml
pytest tests/  # Should show 1097 passed
```

---

## 9. Success Criteria

### 9.1 Functional Criteria

- ✅ `.st3/git.yaml` exists with all 11 conventions externalized:
  - Branch types (Convention #1)
  - TDD phases (Convention #2)
  - Commit prefix mapping (Convention #3)
  - Protected branches (Convention #4)
  - Branch name pattern (Convention #5)
  - Default base branch (Conventions #9-11 consolidated)
- ✅ GitConfig singleton loads and validates git.yaml
- ✅ GitManager uses config (5 methods, Conventions #1-5, no hardcoded values)
- ✅ PolicyEngine uses config (1 method, Convention #6, prefix bug fixed)
- ✅ Git tools use config (2 locations, Conventions #7-8, DRY violations eliminated)
- ✅ PR tools use config (3 locations, Conventions #9-11, DRY violations eliminated)
- ✅ Adding new branch type = edit YAML only (no code changes in 2 locations)
- ✅ Customizing TDD phases = edit YAML only (no code changes)
- ✅ Customizing commit prefixes = edit YAML only (no code changes in 3 locations)
- ✅ Changing default base branch = edit YAML only (no code changes in 3 locations)

### 9.2 Quality Criteria

- ✅ All 1097 existing tests remain passing
- ✅ 30+ new tests added (config + 5 file integrations):
  - Config loading tests (10 tests)
  - GitManager integration (5 tests, Conventions #1-5)
  - PolicyEngine integration (3 tests, Convention #6 + bug fix)
  - Git tools integration (4 tests, Conventions #7-8)
  - PR tools integration (4 tests, Conventions #9-11)
  - End-to-end workflow (4 tests)
- ✅ >95% line coverage for git_config.py
- ✅ Type checking passes (mypy --strict)
- ✅ All 11 grep validations return 0 results (no hardcoded conventions)
- ✅ 3 DRY violations eliminated:
  - Branch types: git_manager.py + git_tools.py → git.yaml
  - Commit prefixes: git_manager.py + policy_engine.py + git_tools.py → git.yaml
  - Default base branch: pr_tools.py (2x) + pr_dto.py → git.yaml

### 9.3 Documentation Criteria

- ✅ design.md documents complete YAML schema (11 conventions) and Pydantic model
- ✅ Reference docs explain each git.yaml field with examples
- ✅ Migration guide shows customization examples for all conventions
- ✅ DRY violation fixes documented (how consolidation works)
- ✅ Inline comments document ClassVar singleton pattern

---

## 10. Timeline Estimate

**Planning Phase:** 1 hour (this document) ✅  
**Design Phase:** 3-4 hours (YAML schema for 11 conventions, Pydantic model, 5 file integration designs)  
**TDD Phase:** 10-12 hours (10 TDD cycles with tests):
  - Cycle 1: Config foundation (2 hours)
  - Cycles 2-5: GitManager (3 hours)
  - Cycle 6: PolicyEngine (1 hour)
  - Cycles 7-8: Git tools (2 hours)
  - Cycle 9: PR tools (2 hours)
  - Cycle 10: Integration (2 hours)
**Integration Phase:** 2-3 hours (end-to-end tests, 11 grep validations, quality gates)  
**Documentation Phase:** 2-3 hours (reference docs for 11 conventions, migration guide, DRY fixes)  

**Total Estimate:** 18-23 hours (updated from 13-16 due to 5 additional conventions discovered)

**Critical Path:**
1. Design phase (blocks TDD - now 3-4 hours due to 11 conventions)
2. TDD Cycle 1 (config foundation - blocks all other cycles)
3. TDD Cycles 2-9 (can be partially parallelized by file: GitManager → PolicyEngine → Git tools → PR tools)
4. Quality gates (blocks integration phase - now includes 11 grep validations)

---

## 11. Next Actions

### 11.1 Immediate Actions (Planning Phase Complete)

1. ✅ **Approve this planning document**
2. ⏳ **Force transition to design phase:**
   ```bash
   force_phase_transition(
       branch="refactor/55-git-yaml",
       to_phase="design",
       skip_reason="Custom design phase required for YAML schema + Pydantic model design",
       human_approval="User requested custom design phase after planning"
   )
   ```
3. ⏳ **Create design.md** with:
   - Complete git.yaml schema (5 conventions)
   - GitConfig Pydantic model (fields, validators, ClassVar singleton)
   - Cross-validation specifications
   - GitManager integration design (6 methods)
   - PolicyEngine integration design (prefix derivation)

### 11.2 Post-Design Actions

4. ⏳ **Transition to TDD phase** (normal transition)
5. ⏳ **Execute TDD Cycles 1-7** (per section 2.1)
6. ⏳ **Run quality gates** (per section 6.2)
7. ⏳ **Transition to integration phase**
8. ⏳ **Transition to documentation phase**
9. ⏳ **Create PR** and merge to main

---

**Document Status:** DRAFT → APPROVED (ready for design phase)  
**Last Updated:** 2026-01-13  
**Next Phase:** Design (forced transition required)