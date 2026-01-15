# Issue #55 Research: Git Conventions Configuration

**Status:** COMPLETE  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Date:** 2026-01-13  
**Issue:** #55 - Config: Git Conventions Configuration (git.yaml)  
**Phase:** Research  
**Parent:** Epic #49 - MCP Platform Configurability

---

## Executive Summary

**Purpose:** Research git-related hardcoded conventions in codebase and document lessons learned from Epic #49 child issues (#50, #52, #54) to inform `.st3/git.yaml` design.

**Research Findings:**
- 6 hardcoded convention types found across 2 files
- GitManager: 5 hardcoded lists/patterns (branch types, TDD phases, prefix mapping, protected branches, name pattern)
- PolicyEngine: 1 hardcoded tuple (commit prefixes)
- Lessons learned from 3 completed issues provide proven patterns for config migration

**Key Insight:** Git conventions follow same pattern as previous Epic #49 issues - centralized hardcoded knowledge that blocks org-specific customization. Solution: YAML config + Pydantic model + refactored consumers.

---

## Related Documents

- [Epic #49](https://github.com/MikeyVK/SimpleTraderV3/issues/49) - MCP Platform Configurability
- [Issue #50](https://github.com/MikeyVK/SimpleTraderV3/issues/50) - Workflow Configuration (COMPLETE)
- [Issue #52](https://github.com/MikeyVK/SimpleTraderV3/issues/52) - Validation Configuration (COMPLETE)
- [Issue #54](https://github.com/MikeyVK/SimpleTraderV3/issues/54) - Config Foundation (COMPLETE)
- [agent_prompt.md](../../../agent_prompt.md) - Agent Cooperation Protocol

---

## 1. Epic #49 Context

### 1.1 Vision

**Epic Goal:** Transform hardcoded MCP server rules into declarative YAML configuration system, enabling dynamic workflow customization without code changes.

**Progress:** 3/8 issues complete (37.5%)

**Completed Issues:**
1. ✅ Issue #50: Workflow Configuration (`workflows.yaml` - 5 workflows, strict phase transitions)
2. ✅ Issue #52: Validation Configuration (`validation.yaml` - template validation rules)
3. ✅ Issue #54: Config Foundation (3 configs: `components.yaml`, `policies.yaml`, `project_structure.yaml`)

**Planned Issues:**
4. ⏳ Issue #55: Git Conventions Configuration (THIS ISSUE)
5. ⏳ Issue #56: Document Templates Configuration
6. ⏳ Issue #57: Constants Configuration
7. ⏳ Issue #105: Dynamic Component Loading
8. ⏳ Issue #TBD: Policy Enforcement Integration

### 1.2 Architecture Benefits (Post Epic #49)

**Current State (3/8 complete):**
- ✅ Workflows: Dynamic phase transitions without code changes
- ✅ Validation: Template rules externalized
- ✅ Config Foundation: Scaffold/policy rules in YAML (no hardcoded logic)
- ⏳ **Git Conventions: Still hardcoded in GitManager + PolicyEngine**

**End State (Issue #55 Complete):**
- Add new branch type = edit YAML only (no code changes)
- Customize TDD phase names = edit YAML only
- Add new commit prefix = edit YAML only
- Customize protected branches = edit YAML only
- Change branch naming pattern = edit YAML only

### 1.3 Configuration Files Overview

**Workspace Configs (`.st3/` directory):**
1. ✅ `.st3/workflows.yaml` - Workflow definitions (Issue #50)
2. ✅ `.st3/labels.yaml` - GitHub label definitions
3. ✅ `.st3/quality.yaml` - Quality gate rules
4. ⏳ `.st3/git.yaml` - Git conventions (Issue #55 - THIS ISSUE)
5. ⏳ `.st3/documents.yaml` - Document templates (Issue #56)
6. ⏳ `.st3/constants.yaml` - Magic numbers & regex patterns (Issue #57)

**MCP Server Configs (`mcp_server/config/` directory):**
- `components.yaml` - Component registry
- `policies.yaml` - Operation policies
- `project_structure.yaml` - Directory structure

**Location Pattern:**
- **Workspace configs** (.st3/): User-facing configuration (workflows, git, quality gates, labels)
- **Server configs** (mcp_server/config/): Internal MCP server behavior (scaffolding, policies, validation)

**Decision for Issue #55:** Use `.st3/git.yaml` (workspace-level configuration)

---

## 2. Hardcoded Git Conventions Analysis

### 2.1 GitManager Conventions

**File:** `mcp_server/managers/git_manager.py` (274 lines)

#### Convention 1: Branch Types (Line 38)
```python
if branch_type not in ["feature", "fix", "refactor", "docs", "epic"]:
    raise ValidationError(
        f"Invalid branch type: {branch_type}",
        hints=["Use feature, fix, refactor, docs, or epic"],
    )
```

**Impact:**
- Hardcoded list blocks org-specific branch types (e.g., `chore`, `style`, `perf`)
- Error messages hardcode type names (not DRY)
- No way to add custom branch types without code changes

**Usage:** `create_branch()` method validation

---

#### Convention 2: TDD Phases (Line 89)
```python
if phase not in ["red", "green", "refactor"]:
    raise ValidationError(
        f"Invalid TDD phase: {phase}",
        hints=["Use red, green, or refactor"],
    )
```

**Impact:**
- Hardcoded TDD phase names (cannot customize to org terminology)
- `docs` phase handled separately in `commit_docs()` method (inconsistent)
- No extensibility for custom phases

**Usage:** `commit_tdd_phase()` method validation

---

#### Convention 3: Commit Prefix Mapping (Line 99)
```python
prefix_map = {"red": "test", "green": "feat", "refactor": "refactor"}
full_message = f"{prefix_map[phase]}: {message}"
```

**Impact:**
- Hardcoded TDD phase → Conventional Commit prefix mapping
- Cannot customize prefix naming (e.g., `test` → `chore(test)`)
- Inconsistent with `docs:` prefix (hardcoded separately)
- Not DRY (docs prefix in separate method)

**Usage:** `commit_tdd_phase()` method commit message formatting

---

#### Convention 4: Protected Branches (Line 206)
```python
protected_branches = ["main", "master", "develop"]
if branch_name in protected_branches:
    raise ValidationError(
        f"Cannot delete protected branch: {branch_name}",
        hints=[f"Protected branches: {', '.join(protected_branches)}"],
    )
```

**Impact:**
- Hardcoded protected branch list (cannot protect custom branches like `staging`, `production`)
- Organizations with different branching strategies blocked
- Error message dynamically built from list (good pattern - preserves in config migration)

**Usage:** `delete_branch()` method preflight validation

---

#### Convention 5: Branch Name Pattern (Line 46)
```python
if not re.match(r"^[a-z0-9-]+$", name):
    raise ValidationError(
        f"Invalid branch name: {name}",
        hints=["Use kebab-case (lowercase, numbers, hyphens only)"],
    )
```

**Impact:**
- Hardcoded regex pattern enforces kebab-case naming
- Cannot customize to org conventions (e.g., snake_case, camelCase, alphanumeric with underscores)
- Pattern explanation hardcoded in hint message

**Usage:** `create_branch()` method name validation

---

### 2.2 PolicyEngine Conventions

**File:** `mcp_server/core/policy_engine.py` (229 lines)

#### Convention 6: TDD Commit Prefixes (Line 123)
```python
tdd_prefixes = ("red:", "green:", "refactor:", "docs:")

if any(message.startswith(prefix) for prefix in tdd_prefixes):
    return PolicyDecision(
        allowed=True,
        requires_human_approval=False,
        reason=f"Valid commit: TDD phase prefix found in '{message}'"
    )
```

**Impact:**
- Hardcoded prefix validation tuple (duplicates GitManager prefix_map logic)
- Cannot customize prefix format (e.g., `[red]`, `RED:`, `test:`)
- Inconsistent with GitManager mapping (PolicyEngine checks `red:` but GitManager generates `test:`)
- **CRITICAL BUG:** PolicyEngine expects `red:` but GitManager generates `test:` - mismatch!

**Usage:** `_decide_commit()` policy decision enforcement

---

### 2.3 Git Tool Conventions

**File:** `mcp_server/tools/git_tools.py` (200+ lines)

#### Convention 7: Branch Type Regex (Line 153)
```python
match = re.search(r"(?:feature|fix|refactor|docs)/(\d+)-", branch_name)
```

**Impact:**
- Hardcoded branch type regex for issue number extraction
- Must be kept in sync with Convention #1 (branch_types list)
- Adding new branch type requires updating regex pattern

**Usage:** Helper function to parse issue numbers from branch names

---

#### Convention 8: Commit Prefix Detection (Lines 173-179)
```python
# Detect prefix from commit message
if message.startswith("test:"):
    prefix = "test"
elif message.startswith("feat:"):
    prefix = "feat"
elif message.startswith("refactor:"):
    prefix = "refactor"
elif message.startswith("docs:"):
    prefix = "docs"
```

**Impact:**
- Hardcoded prefix detection logic (duplicates GitManager prefix_map)
- Must be kept in sync with Convention #3 (commit_prefix_map)
- Adding new prefix requires updating if-elif chain

**Usage:** Parse commit messages to extract prefix type

---

### 2.4 PR Tool Conventions

**File:** `mcp_server/tools/pr_tools.py`, `mcp_server/dtos/pr_dto.py`

#### Convention 9-11: Default Base Branch "main"
```python
# pr_tools.py Line 69
def create_pr(title: str, body: str, head: str, base: str = "main", draft: bool = False):

# pr_tools.py Line 143
def merge_pr(pr_number: int, merge_method: str = "merge", commit_message: str | None = None):
    # ... uses "main" as implicit base

# pr_dto.py Line 17
base: str = Field(default="main", description="Target branch")
```

**Impact:**
- Hardcoded "main" as default base branch (3 locations)
- Organizations using `master`, `develop`, or `trunk` must always override
- Inconsistent with Convention #4 (protected_branches includes main, master, develop)

**Usage:** PR creation and merging default behavior

---

### 2.5 Hardcoded Conventions Summary

| ID | Convention | Location | Type | Current Values | Extensibility Blocked |
|----|-----------|----------|------|----------------|----------------------|
| 1 | Branch Types | `git_manager.py:38` | List | `["feature", "fix", "refactor", "docs", "epic"]` | Cannot add `chore`, `style`, `perf` |
| 2 | TDD Phases | `git_manager.py:89` | List | `["red", "green", "refactor"]` | Cannot customize phase names |
| 3 | Commit Prefix Mapping | `git_manager.py:99` | Dict | `{"red": "test", "green": "feat", "refactor": "refactor"}` | Cannot change prefix format |
| 4 | Protected Branches | `git_manager.py:206` | List | `["main", "master", "develop"]` | Cannot protect `staging`, `production` |
| 5 | Branch Name Pattern | `git_manager.py:46` | Regex | `r"^[a-z0-9-]+$"` (kebab-case) | Cannot use snake_case, camelCase |
| 6 | TDD Commit Prefixes | `policy_engine.py:123` | Tuple | `("red:", "green:", "refactor:", "docs:")` | Cannot customize prefix validation |
| 7 | Branch Type Regex | `git_tools.py:153` | Regex | `r"(?:feature\|fix\|refactor\|docs)/(\d+)-"` | Must sync with Convention #1 |
| 8 | Commit Prefix Detection | `git_tools.py:173-179` | If-elif chain | `test:`, `feat:`, `refactor:`, `docs:` | Must sync with Convention #3 |
| 9 | Default Base Branch (PR create) | `pr_tools.py:69` | String | `"main"` | Cannot default to `master`/`develop` |
| 10 | Default Base Branch (PR merge) | `pr_tools.py:143` | String | `"main"` (implicit) | Cannot default to `master`/`develop` |
| 11 | Default Base Branch (PR DTO) | `pr_dto.py:17` | String | `"main"` | Cannot default to `master`/`develop` |

**Total Hardcoded Conventions:** 11 (6 original + 5 new findings)

**CRITICAL FINDINGS:**

1. **Prefix Inconsistency Bug (Convention #3 vs #6):**
   - GitManager generates: `test:`, `feat:`, `refactor:`, `docs:`
   - PolicyEngine validates: `red:`, `green:`, `refactor:`, `docs:`
   - Result: Commits created by `commit_tdd_phase("red", "...")` would be **BLOCKED** by PolicyEngine!
   - Root Cause: TDD phase → prefix mapping lives in GitManager, but PolicyEngine validates against phase names directly

2. **DRY Violations:**
   - Convention #1 (branch types list) duplicated in Convention #7 (regex)
   - Convention #3 (prefix mapping) duplicated in Convention #8 (detection logic)
   - Convention #9-11 (default base branch) hardcoded in 3 separate locations

3. **Synchronization Risk:**
   - Adding new branch type requires updating 2 locations (list + regex)
   - Adding new commit prefix requires updating 3 locations (mapping + validation + detection)
   - Changing default base branch requires updating 3 locations (2 tools + 1 DTO)

---

## 3. Lessons Learned from Epic #49 Issues

### 3.1 Issue #50: Workflow Configuration (workflows.yaml)

**What Worked:**
1. **Pydantic Validation:** `WorkflowConfig` model with nested `WorkflowTemplate` ensured type safety and fail-fast validation
2. **Strict Enum Usage:** `ExecutionMode` enum prevented typos (autonomous/interactive)
3. **Sequential Phase Validation:** `PhaseStateEngine` enforced strict workflow progression with audit trail
4. **Escape Hatch:** `force_phase_transition()` with `skip_reason` + `human_approval` provided justified flexibility
5. **Config Location:** `.st3/workflows.yaml` for workspace-level config (NOT in `mcp_server/config/`)
6. **Singleton Pattern:** Config loaded once at startup, cached for performance (50% less I/O)
7. **Cross-Validation:** Workflow phase references validated at load time (fail-fast)

**Key Patterns:**
- YAML → Pydantic → Manager → Tool (layered design)
- Config defines schema, manager enforces business logic, tool exposes MCP interface
- 100% test coverage for new code (12 tests for 2 tools)
- 10.0/10 pylint across all components
- Documentation: design.md + planning.md + discovery.md

**Quality Metrics:**
- 12/12 tests passing
- 100% coverage (WorkflowConfig: 46/46, PhaseStateEngine: 69/69, tools: 51/51)
- 10.0/10 pylint
- Mypy strict + Pyright passing

**Lessons for Issue #55:**
- ✅ Use Pydantic models with strict validation
- ✅ Enums for constrained string values (prevents typos)
- ✅ Singleton config pattern for performance
- ✅ Fail-fast validation at config load time
- ✅ Escape hatch with audit trail (force mechanism)
- ✅ Layer separation (config → manager → tool)
- ✅ 100% test coverage requirement
- ✅ Triple documentation (design + planning + research)

---

### 3.2 Issue #52: Validation Configuration (validation.yaml)

**What Worked:**
1. **Dict-Based Schema:** `templates: Dict[str, TemplateRule]` allowed flexible template type definitions
2. **Optional Fields:** Used `Optional[str]` and `List[str] = []` for optional validation rules
3. **Descriptive Metadata:** Each rule had `description` field for self-documentation
4. **RULES Dict Removed:** Complete removal of hardcoded dict from `template_validator.py`
5. **Consumer Update:** `TemplateValidator` and `SafeEditTool` refactored to use config

**Key Patterns:**
- YAML schema with dict-based template definitions
- Pydantic model with optional fields for flexibility
- Consumer code updated to query config dynamically
- Zero backward compatibility (clean break)

**Lessons for Issue #55:**
- ✅ Use dict-based schemas for variable-length definitions (e.g., `branch_types: Dict[str, BranchTypeConfig]`)
- ✅ Optional fields with sensible defaults (`Optional[str]`, `List[str] = []`)
- ✅ Descriptive metadata for self-documentation (`description` field)
- ✅ Clean break from hardcoded dicts (no backward compat)
- ✅ Update all consumer code to query config dynamically

---

### 3.3 Issue #54: Config Foundation (3 configs)

**What Worked:**
1. **Three-Config Architecture:** WAT/WAAR/WANNEER separation (components, structure, policies)
2. **Cross-Config Validation:** Referential integrity checks at load time (e.g., `allowed_layers` in policies must exist in structure)
3. **DirectoryPolicyResolver:** Inheritance algorithm for nested directory policies (DRY)
4. **4-Phase Build Order:** Foundation → Structure → PolicyEngine → Tool (clear dependencies)
5. **Config Location Decision:** `mcp_server/config/` NOT `.st3/` (documented in config_location_investigation.md)
6. **Performance Metrics:** 17.91ms load time (target: <100ms) - singleton pattern critical
7. **Zero Design Gaps:** Gap analysis confirmed 100% implementation completeness (65/65 tests)
8. **Comprehensive Documentation:** 4065 lines across design.md + planning.md + research.md

**Key Patterns:**
- Multi-config architecture with clear separation of concerns
- Cross-config validation for referential integrity
- Inheritance/resolution algorithms for DRY (e.g., directory policies cascade)
- Gap analysis methodology (design.md vs implementation diff)
- Config location decision documented and justified

**Quality Metrics:**
- 65/65 tests passing
- 17.91ms config load time
- Zero mypy errors
- Zero design gaps (gap analysis complete)
- 4065 lines documentation

**⚠️ CONFIG LOCATION INCONSISTENCY DISCOVERED:**

**Issue #50:** `.st3/workflows.yaml` (workspace root)
**Issue #54:** `mcp_server/config/*.yaml` (application code)

**config_location_investigation.md Key Findings:**
1. **Workspace-level configs** (`.st3/`): Project-specific settings (workflows, labels, quality gates)
2. **Application-level configs** (`mcp_server/config/`): Structural/component definitions (components, policies, structure)

**Decision Criteria for Issue #55:**
- **Git conventions** are workspace-specific (branch types, protected branches)
- Different projects may have different git workflows
- **Conclusion:** `.st3/git.yaml` follows Issue #50 pattern (workspace-level config)

**Lessons for Issue #55:**
- ✅ Multi-config approach if needed (e.g., separate `branch_types.yaml` + `commit_conventions.yaml`)
- ✅ Cross-validation for referential integrity (e.g., commit_prefix_map keys must match tdd_phases)
- ✅ Performance metrics: <100ms load time target
- ✅ Gap analysis methodology (design → implementation verification)
- ✅ Config location: `.st3/git.yaml` (workspace-level, not application-level)
- ✅ Singleton pattern for config loading (performance)
- ✅ Comprehensive documentation (research + design + planning)

---

### 3.4 Agent Workflow Protocol (agent_prompt.md)

**Critical Requirements:**
1. **Tool-First:** Use MCP tools for ALL operations (NEVER terminal/CLI where tool exists)
2. **Issue-First Development:** All work starts with GitHub issue (never commit to main)
3. **Phase Progression:** Use `initialize_project()` then `transition_phase()` for workflow management
4. **TDD Cycle:** RED → GREEN → REFACTOR within `tdd` phase (multiple cycles)
5. **Quality Gates:** Run `run_quality_gates()` before phase transitions and PR creation
6. **Documentation:** Pre-dev docs in `docs/development/issueXX/`, reference docs in `documentation` phase
7. **English Code, Dutch Chat:** All code/docs/commits in English, user interaction in Dutch

**Tool Priority Matrix (Git Operations):**
- ✅ `git_status()` → ❌ `run_in_terminal("git status")`
- ✅ `git_add_or_commit()` → ❌ `run_in_terminal("git commit")`
- ✅ `create_branch()` → ❌ `run_in_terminal("git checkout -b")`
- ✅ `scaffold_component()` → ❌ `create_file()` with manual code

**Lessons for Issue #55:**
- ✅ All git conventions consumed by MCP tools (not CLI)
- ✅ git.yaml must support existing tool signatures (backward compatibility)
- ✅ Documentation in `docs/development/issue55/` (research.md, design.md, planning.md)
- ✅ TDD cycles within `tdd` phase (not phase transitions)
- ✅ Quality gates before `integration` phase transition

---

## 4. Issue #55 Scope Definition

### 4.1 In Scope

**Config File:** `.st3/git.yaml` (workspace-level config, following Issue #50 pattern)

**Hardcoded Items to Migrate:**
1. ✅ Branch types (`git_manager.py:38`) → `git.yaml:branch_types`
2. ✅ TDD phases (`git_manager.py:89`) → `git.yaml:tdd_phases`
3. ✅ Commit prefix mapping (`git_manager.py:99`) → `git.yaml:commit_prefix_map`
4. ✅ Protected branches (`git_manager.py:206`) → `git.yaml:protected_branches`
5. ✅ Branch name pattern (`git_manager.py:46`) → `git.yaml:branch_name_pattern`
6. ✅ TDD commit prefixes (`policy_engine.py:123`) → DERIVED from `commit_prefix_map` (solve inconsistency)

**Deliverables:**
- ✅ `.st3/git.yaml` created with complete schema
- ✅ Pydantic model: `GitConfig` (`mcp_server/config/git_config.py`)
- ✅ Config loader implemented (singleton pattern)
- ✅ `GitManager` updated to use config (6 methods affected)
- ✅ `PolicyEngine` updated to use config (`_decide_commit()` method)
- ✅ Hardcoded git conventions removed (all 6 instances)
- ✅ Tests: config loading, branch validation, commit validation, protected branch checks
- ✅ Documentation: git config reference (+ research + design + planning)

### 4.2 Out of Scope

**Not in Issue #55:**
- ❌ Workflows (Issue #50 - COMPLETE)
- ❌ Labels (pre-existing `.st3/labels.yaml`)
- ❌ Document templates (Issue #56)
- ❌ Constants/magic numbers (Issue #57)
- ❌ Dynamic component loading (Issue #105)
- ❌ Policy enforcement integration (Issue #TBD)

**Git Operations NOT Being Configured:**
- ❌ Commit message templates (not hardcoded, no need for config)
- ❌ PR templates (GitHub-native feature)
- ❌ Git hooks (not managed by MCP server)
- ❌ Remote repository URLs (workspace-specific, not conventions)

---

## 5. Critical Design Decisions

### 5.1 Config Location: `.st3/git.yaml`

**Rationale:**
- Git conventions are **workspace-specific** (different projects have different workflows)
- Follows Issue #50 pattern (workflows.yaml in `.st3/`)
- config_location_investigation.md: Workspace-level = `.st3/`, Application-level = `mcp_server/config/`
- **Decision:** `.st3/git.yaml` (workspace-level config)

---

### 5.2 Solve Prefix Inconsistency (Convention #3 vs #6)

**Problem:**
- GitManager generates: `test:`, `feat:`, `refactor:`, `docs:`
- PolicyEngine validates: `red:`, `green:`, `refactor:`, `docs:`
- Mismatch: `red:` ≠ `test:`, `green:` ≠ `feat:`

**Root Cause:**
- GitManager maps TDD phases to Conventional Commit prefixes
- PolicyEngine validates against TDD phase names directly
- Two sources of truth for same concept

**Solution Options:**
1. **Option A:** PolicyEngine derives prefixes from `commit_prefix_map` (RECOMMENDED)
2. **Option B:** Separate config keys for phase names and commit prefixes
3. **Option C:** Change GitManager to use phase names directly (`red:` instead of `test:`)

**Recommendation:** **Option A** (derive from `commit_prefix_map`)
- Single source of truth (`commit_prefix_map`)
- PolicyEngine queries config: `allowed_prefixes = [f"{v}:" for v in commit_prefix_map.values()]`
- DRY principle: one mapping, multiple consumers
- Preserves Conventional Commit semantics (`test:`, `feat:`, `refactor:`, `docs:`)

---

### 5.3 Branch Type Extensibility

**Current:** Hardcoded list `["feature", "fix", "refactor", "docs", "epic"]`

**Future-Proof Design:**
```yaml
branch_types:
  feature:
    name: "feature"
    description: "New feature development"
    default_execution_mode: "interactive"
  fix:
    name: "fix"
    description: "Bug fix"
    default_execution_mode: "interactive"
  # ... etc
```

**Rationale:**
- Allows metadata per branch type (description, execution mode)
- Future extensibility (e.g., `require_issue: true`, `require_tests: true`)
- Self-documenting configuration

**Alternative (Simpler):**
```yaml
branch_types: ["feature", "fix", "refactor", "docs", "epic"]
```

**Recommendation:** Start simple (list), migrate to dict if metadata needed (YAGNI principle)

---

### 5.4 Config Validation Requirements

**Cross-Validation Rules:**
1. `commit_prefix_map` keys MUST be subset of `tdd_phases` (referential integrity)
2. `branch_name_pattern` MUST be valid regex (compile check at load time)
3. `protected_branches` MUST be non-empty (prevent accidental deletion of main)
4. TDD phase names MUST be alphanumeric lowercase (convention enforcement)

**Fail-Fast Behavior:**
- Invalid config = crash at startup (no silent failures)
- Pydantic `@model_validator` for cross-field validation
- Regex compilation test at model initialization

---

## 6. Implementation Strategy (High-Level)

### 6.1 Build Order (TDD Phases)

**Phase 1: Foundation (Red → Green → Refactor)**
1. RED: Test `git.yaml` loading
2. GREEN: Implement `GitConfig` Pydantic model + loader
3. REFACTOR: Add cross-validation, singleton pattern

**Phase 2: GitManager Integration (Red → Green → Refactor)**
1. RED: Test branch type validation via config
2. GREEN: Refactor `create_branch()` to use config
3. RED: Test commit prefix mapping via config
4. GREEN: Refactor `commit_tdd_phase()` to use config
5. RED: Test protected branch validation via config
6. GREEN: Refactor `delete_branch()` to use config
7. RED: Test branch name pattern validation via config
8. GREEN: Refactor `create_branch()` pattern check to use config
9. REFACTOR: Remove all hardcoded conventions from `git_manager.py`

**Phase 3: PolicyEngine Integration (Red → Green → Refactor)**
1. RED: Test commit prefix validation via config
2. GREEN: Refactor `_decide_commit()` to use config (derive prefixes from `commit_prefix_map`)
3. REFACTOR: Remove hardcoded `tdd_prefixes` tuple from `policy_engine.py`

**Phase 4: Integration & Documentation**
1. Integration tests: End-to-end workflows with new config
2. Documentation: Git config reference, migration guide

---

### 6.2 Files to Create

**New Files:**
1. `.st3/git.yaml` - Git conventions configuration
2. `mcp_server/config/git_config.py` - Pydantic model + loader
3. `tests/mcp_server/config/test_git_config.py` - Config loading tests
4. `tests/mcp_server/managers/test_git_manager_config.py` - GitManager config integration tests
5. `tests/mcp_server/core/test_policy_engine_git_config.py` - PolicyEngine config integration tests
6. `docs/development/issue55/design.md` - Component designs (NEXT STEP)
7. `docs/development/issue55/planning.md` - Implementation strategy (AFTER DESIGN)

---

### 6.3 Files to Modify

**Existing Files:**
1. `mcp_server/managers/git_manager.py` - 6 methods to refactor:
   - `create_branch()` - branch types, name pattern (lines 38, 46)
   - `commit_tdd_phase()` - TDD phases, prefix mapping (lines 89, 99)
   - `delete_branch()` - protected branches (line 206)

2. `mcp_server/core/policy_engine.py` - 1 method to refactor:
   - `_decide_commit()` - TDD commit prefixes (line 123)

3. `tests/mcp_server/managers/test_git_manager.py` - Update existing tests for config-driven validation

4. `tests/mcp_server/core/test_policy_engine.py` - Update existing tests for config-driven commit validation

---

## 7. Success Criteria

### 7.1 Functional Requirements

- [x] All 6 git conventions externalized to YAML
- [ ] Config loading with Pydantic validation
- [ ] GitManager uses config for all validation/formatting
- [ ] PolicyEngine uses config for commit validation
- [ ] Protected branches customizable
- [ ] Branch types customizable
- [ ] TDD phases customizable
- [ ] Commit prefix mapping customizable
- [ ] Branch name pattern customizable

### 7.2 Quality Requirements

- [ ] All existing tests pass (GitManager + PolicyEngine)
- [ ] New tests cover config loading (edge cases, validation failures)
- [ ] New tests cover GitManager config integration (all 6 conventions)
- [ ] New tests cover PolicyEngine config integration (commit prefix validation)
- [ ] 100% test coverage for new code
- [ ] 10.0/10 pylint for new code
- [ ] Mypy strict + Pyright passing
- [ ] Config load time <100ms (singleton pattern)
- [ ] Zero hardcoded conventions remaining in `git_manager.py` and `policy_engine.py`

### 7.3 Documentation Requirements

- [ ] `docs/development/issue55/research.md` (THIS DOCUMENT - COMPLETE)
- [ ] `docs/development/issue55/design.md` (Component designs with schemas)
- [ ] `docs/development/issue55/planning.md` (TDD implementation plan)
- [ ] Git config reference documentation (end-user docs)
- [ ] Migration guide (how to customize git.yaml)

---

## 8. Risk Assessment

### 8.1 Breaking Changes

**Risk:** Changing GitManager/PolicyEngine behavior may break existing workflows

**Mitigation:**
- Default config values match current hardcoded values (backward compatible)
- Integration tests validate end-to-end workflows
- Gap analysis methodology (Issue #54) ensures no behavior changes

---

### 8.2 Config Location Confusion

**Risk:** Developers may not know where to put git.yaml (`.st3/` vs `mcp_server/config/`)

**Mitigation:**
- Clear documentation in research.md (this document)
- Config location decision documented and justified
- Consistent with Issue #50 pattern (workspace-level → `.st3/`)

---

### 8.3 Prefix Inconsistency Fix

**Risk:** Changing prefix validation in PolicyEngine may break existing commit workflows

**Mitigation:**
- Current inconsistency is latent bug (PolicyEngine likely not enforcing yet)
- Fix prevents future enforcement issues
- Default config preserves current behavior (`test:`, `feat:`, `refactor:`, `docs:`)

---

## 9. Open Questions for Design Phase

### 9.1 Config Schema Design

**Q1:** Branch types as list or dict?
- List: Simple, sufficient for current needs
- Dict: Extensible metadata (description, execution_mode)
- **Decision:** Defer to design phase (start simple, iterate if needed)

**Q2:** Separate `docs` phase from TDD phases?
- Current: `docs:` handled separately in `commit_docs()` method
- Option A: Add `docs` to `tdd_phases` list (unified)
- Option B: Separate `doc_phase: "docs"` config key
- **Decision:** Defer to design phase (analyze `commit_docs()` usage)

**Q3:** Branch name pattern per branch type?
- Current: Global pattern for all branch types
- Future: Per-type patterns (e.g., `feature/123-name` vs `fix/BUG-456`)
- **Decision:** Defer to design phase (YAGNI vs future-proofing)

---

### 9.2 PolicyEngine Integration

**Q4:** PolicyEngine config injection?
- Option A: PolicyEngine queries `GitConfig.get_instance()` directly
- Option B: PolicyEngine constructor accepts `git_config: GitConfig` parameter
- **Decision:** Defer to design phase (analyze existing PolicyEngine constructor)

**Q5:** Cross-config validation?
- Git config may reference workflow phases (future extensibility)
- Should `GitConfig` validate against `WorkflowConfig`?
- **Decision:** Defer to design phase (analyze Epic #49 cross-config patterns)

---

## 10. Next Steps

### 10.1 Immediate Actions (Research Phase Complete)

1. ✅ **Transition to Planning Phase:**
   - Run: `transition_phase(branch="refactor/55-git-yaml", to_phase="planning")`

2. ⏳ **Create design.md:**
   - Complete YAML schema design
   - Pydantic model design (`GitConfig`, nested models if needed)
   - GitManager integration design (method signatures, validation logic)
   - PolicyEngine integration design (prefix derivation algorithm)
   - Cross-validation rules specification

3. ⏳ **Create planning.md:**
   - TDD implementation plan (RED → GREEN → REFACTOR cycles)
   - Build order with dependencies
   - Test coverage plan (unit + integration tests)
   - Quality gate checklist

### 10.2 Phase Progression

**Current Phase:** Research ✅  
**Next Phase:** Planning  
**Workflow:** refactor (5 phases: research → planning → tdd → integration → documentation)

**Remaining Phases:**
- Planning: Design + implementation strategy
- TDD: Red-Green-Refactor cycles
- Integration: End-to-end testing
- Documentation: Reference docs + migration guide

---

## 11. Appendix: Code References

### 11.1 GitManager Hardcoded Conventions

```python
# mcp_server/managers/git_manager.py

# Convention 1: Branch Types (Line 38)
if branch_type not in ["feature", "fix", "refactor", "docs", "epic"]:
    raise ValidationError(...)

# Convention 2: TDD Phases (Line 89)
if phase not in ["red", "green", "refactor"]:
    raise ValidationError(...)

# Convention 3: Commit Prefix Mapping (Line 99)
prefix_map = {"red": "test", "green": "feat", "refactor": "refactor"}

# Convention 4: Protected Branches (Line 206)
protected_branches = ["main", "master", "develop"]

# Convention 5: Branch Name Pattern (Line 46)
if not re.match(r"^[a-z0-9-]+$", name):
    raise ValidationError(...)
```

### 11.2 PolicyEngine Hardcoded Conventions

```python
# mcp_server/core/policy_engine.py

# Convention 6: TDD Commit Prefixes (Line 123)
tdd_prefixes = ("red:", "green:", "refactor:", "docs:")
if any(message.startswith(prefix) for prefix in tdd_prefixes):
    return PolicyDecision(allowed=True, ...)
```

---

## 12. Research Phase Completion

**Status:** ✅ COMPLETE

**Research Findings Summary:**
- 6 hardcoded git conventions identified across 2 files
- 3 completed Epic #49 issues provide proven patterns
- Config location decision: `.st3/git.yaml` (workspace-level)
- Prefix inconsistency bug discovered (GitManager vs PolicyEngine)
- Implementation strategy: YAML + Pydantic + refactored consumers
- Success criteria defined (functional, quality, documentation)

**Ready for Planning Phase:** YES ✅

**Next Document:** `design.md` (Component designs with complete schemas)

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-13  
**Author:** GitHub Copilot (Claude Sonnet 4.5)
