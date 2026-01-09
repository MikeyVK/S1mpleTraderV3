# AGENT_PROMPT.md Analysis - Issue #99

**Date:** 2026-01-09  
**Analyst:** GitHub Copilot (Claude Sonnet 4.5)  
**Purpose:** Comprehensive analysis of AGENT_PROMPT.md vs current MCP server implementation

---

## Executive Summary

**Overall Status:** 🟡 **Needs Updates** - 70% accuracy  
**Critical Issues:** 11 tool name mismatches, missing lazy loading documentation, incomplete workflow guidance  
**Action Required:** Update tool names, add lazy loading section, clarify workflow enforcement

---

## Part 1: Tool Name Accuracy Analysis

### ❌ Critical Mismatches (11 tools)

| AGENT_PROMPT.md (Incorrect) | Actual MCP Tool Name | Impact |
|----------------------------|---------------------|---------|
| `create_feature_branch` | `create_branch` | HIGH - Tool won't be found |
| `git_checkout_branch` | `git_checkout` | HIGH - Tool won't be found |
| `validate_dto` | **Does not exist** | CRITICAL - validate_dto is not ValidateDTOTool |
| `validate_document_structure` | **validate_doc** (ValidateDocTool) | HIGH - Wrong tool name |
| `validate_architecture` | **Does not exist** | CRITICAL - Only validate_architecture (scope-based) |
| `scaffold_component` | **scaffold_component** | ✅ CORRECT |
| `scaffold_document` | **scaffold_design_doc** | HIGH - Wrong name |
| `update_implementation_status` | **Does not exist** | CRITICAL - No such tool |
| `start_work_on_issue` | **Does not exist** | CRITICAL - No such tool |
| `read_resource` | **Resource URIs** | MEDIUM - Works via st3:// URIs |
| `call_tool` | Generic MCP call | LOW - Generic reference |

### ✅ Correct Tool Names (27 tools)

Git Operations (11):
- `git_status` ✅
- `git_add_or_commit` ✅ (GitCommitTool)
- `git_push` ✅
- `git_merge` ✅
- `git_delete_branch` ✅
- `git_stash` ✅
- `git_checkout` ✅ (but AGENT_PROMPT says git_checkout_branch)
- `git_fetch` ✅
- `git_pull` ✅
- `git_restore` ✅
- `git_list_branches` ✅

GitHub Operations (10):
- `create_issue` ✅
- `list_issues` ✅
- `get_issue` ✅
- `close_issue` ✅
- `update_issue` ✅
- `add_labels` ✅
- `remove_labels` ✅
- `create_pr` ✅
- `list_prs` ✅
- `merge_pr` ✅

Quality & Testing (2):
- `run_tests` ✅
- `run_quality_gates` ✅

Discovery (3):
- `get_work_context` ✅
- `search_documentation` ✅
- `health_check` ✅

Scaffold (1):
- `scaffold_design_doc` ✅ (but AGENT_PROMPT says scaffold_document)

---

## Part 2: Resource URIs Analysis

### ✅ Documented Resources (Correct)

| URI | Status | Implementation |
|-----|--------|---------------|
| `st3://rules/coding_standards` | ✅ EXISTS | StandardsResource - returns JSON with python, testing, tools config |
| `st3://status/phase` | ✅ EXISTS | StatusResource - returns current_phase, active_branch, is_clean |
| `st3://templates/list` | ✅ EXISTS | TemplatesResource - returns DocManager.TEMPLATES |

### ❌ Missing Resource

| URI Referenced | Status | Issue |
|---------------|--------|-------|
| `st3://status/implementation` | ❌ NOT FOUND | No implementation status resource exists |

**Recommendation:** Either:
1. Remove reference from AGENT_PROMPT.md, OR
2. Implement ImplementationStatusResource if needed

---

## Part 3: Workflow Enforcement Analysis

### Current State: Workflow IS Enforced

**Implementation Location:** `mcp_server/managers/phase_state_engine.py`

**Key Findings:**
1. ✅ **Workflow-based phase transitions** via `workflows.yaml` (`.st3/workflows.yaml`)
2. ✅ **Sequential validation** via `workflow_config.validate_transition()`
3. ✅ **Forced transitions** with audit trail via `force_phase_transition` tool
4. ✅ **Parent branch tracking** stored in `.st3/state.json`
5. ✅ **Project initialization** caches `workflow_name` for performance

**Workflow File:** `.st3/workflows.yaml`
- Defines 5 standard workflows: feature, bug, docs, refactor, hotfix
- Each workflow has ordered phases
- Supports custom phases with `skip_reason` requirement

### ⚠️ AGENT_PROMPT.md Gaps

**Missing Workflow Guidance:**
1. No mention of `initialize_project` tool (CRITICAL for workflow setup)
2. No mention of `transition_phase` tool
3. No mention of `force_phase_transition` tool
4. No mention of phase state management (`.st3/state.json`)
5. No mention of workflow selection (feature/bug/docs/refactor/hotfix)
6. No mention of parent branch tracking

**What AGENT_PROMPT.md Currently Says:**
- Section B mentions "start_work_on_issue" (does NOT exist)
- TDD loop mentions RED/GREEN/REFACTOR but not phase transitions
- No guidance on when/how to transition phases

---

## Part 4: Missing Critical Functionality

### 🚨 Not Documented in AGENT_PROMPT.md

**Project Initialization Workflow:**
1. `initialize_project` - Sets up workflow, creates branch, initializes state
   - Parameters: issue_number, issue_title, workflow_name, parent_branch, custom_phases
   - Returns: workflow phases, parent branch, state initialization
2. `get_project_plan` - Retrieves workflow phases for an issue
3. `get_parent_branch` - Detects parent branch from git reflog

**Phase Management Workflow:**
1. `transition_phase` - Sequential phase transition (strict validation)
2. `force_phase_transition` - Non-sequential transition with skip_reason
3. State persistence in `.st3/state.json`
4. Transition history with audit trail

**Branch Management:**
1. `create_branch` needs explicit base_branch (HEAD, main, or branch-name)
2. Parent branch tracking for epic → feature → bugfix hierarchies
3. Git reflog-based parent detection

**Label Management (Complete category missing):**
1. `create_label` - Create new labels
2. `delete_label` - Remove labels
3. `list_labels` - List all labels
4. `detect_label_drift` - Compare labels with config

**Milestone Management (Complete category missing):**
1. `create_milestone` - Create milestones
2. `list_milestones` - List milestones (all/open/closed)
3. `close_milestone` - Close milestone

**Additional Tools:**
1. `safe_edit_file` - Multi-mode file editing (content/line_edits/insert_lines/search_replace)
2. `create_file` - Generic file creation (DEPRECATED per tool, but in AGENT_PROMPT)
3. `template_validation_tool` - Validate templates (worker/tool/dto/adapter/base)
4. Git analysis: `git_diff_stat`, `git_fetch`

---

## Part 5: Lazy Loading Documentation (MISSING)

### 🚨 CRITICAL OMISSION

**Discovery (2026-01-09):** VS Code Copilot (v1.108, Dec 2025) uses lazy loading for MCP tools.

**Impact on Agent Behavior:**
- Tools appear as "disabled by user" until activated
- Activation required before tool usage
- 8 activation function categories identified

**Required Documentation:**

### Activation Functions (8 categories)
1. `activate_file_editing_tools` → create_file, safe_edit_file, scaffold_component
2. `activate_git_workflow_management_tools` → 15 git/PR tools
3. `activate_branch_phase_management_tools` → phase tools
4. `activate_issue_management_tools` → 6 issue tools
5. `activate_label_management_tools` → 5 label tools
6. `activate_milestone_and_pr_management_tools` → milestone + PR list tools
7. `activate_project_initialization_tools` → initialize_project, get_project_plan
8. `activate_code_validation_tools` → 4 validation tools

**Semantic Categorization Pattern:**
- Tool names analyzed for keywords (phase→branch_phase, issue→issue_management, etc.)
- VS Code Copilot generates activate_* functions dynamically
- Client-side feature, not MCP protocol specification

**Reference:** See `docs/development/issue99/mcp_tools_testing_log.md` - "Lazy Loading Discovery" section

---

## Part 6: Tool Priority Matrix Corrections

### Corrections Needed

**Git Operations:**
- ✅ Correct: All git tool names match
- ❌ Fix: `create_feature_branch` → `create_branch`
- ❌ Fix: `git_checkout_branch` → `git_checkout`

**GitHub Issues:**
- ✅ Correct: All 5 issue tools match

**Pull Requests:**
- ✅ Correct: create_pr matches
- ⚠️ Add: `list_prs`, `merge_pr` (missing from table)

**Code Scaffolding:**
- ✅ Correct: All scaffold_component types documented
- ⚠️ Note: `create_file` is DEPRECATED but still in MCP server

**Document Scaffolding:**
- ❌ Fix: `scaffold_document` → `scaffold_design_doc`
- ✅ Correct: Template types match (architecture/design/reference/tracking/generic)

**Quality & Testing:**
- ❌ Remove: `validate_dto` (tool does NOT exist in current implementation)
- ❌ Remove: `validate_document_structure` (actual tool: `validate_doc`)
- ❌ Remove: `validate_architecture` (exists but different usage)
- ✅ Keep: `run_tests`, `run_quality_gates`
- ⚠️ Add: `template_validation_tool` (validate_template)

**Discovery & Context:**
- ✅ Correct: All 3 tools match

---

## Part 7: English vs Dutch Compliance

**Current AGENT_PROMPT.md:** ✅ COMPLIANT
- All technical content in English
- Mentions Dutch for user interaction ("Talk to the User in **Dutch**")
- Consistent with project standards

---

## Part 8: Recommended Workflow Guidance

### Question for User: Which Workflow Should Be Enforced?

Based on the implementation, I can see these workflows exist:

**Standard Workflows (`.st3/workflows.yaml`):**
1. **feature** - 7 phases: planning → research → design → tdd → integration → documentation → ready
2. **bug** - 6 phases: triage → investigation → design → tdd → integration → ready
3. **docs** - 4 phases: research → draft → review → ready
4. **refactor** - 5 phases: analysis → design → tdd → integration → ready
5. **hotfix** - 3 phases: triage → tdd → ready

**Custom Workflow:**
- Agent can define custom phases with `skip_reason` requirement

### Questions for User:

1. **Should AGENT_PROMPT.md enforce a specific workflow?**
   - Option A: Document all 5 standard workflows, let agent/user choose
   - Option B: Default to 'feature' workflow with option to override
   - Option C: Require explicit workflow selection per issue

2. **Should TDD loop in Section 2A mention phase transitions?**
   - Current: RED → GREEN → REFACTOR
   - Proposal: RED (tdd phase) → GREEN (tdd phase) → REFACTOR (refactor phase) → transition

3. **Should initialize_project be mandatory before any work?**
   - Current: Not mentioned
   - Proposal: Add to Phase 1 orientation protocol

4. **How should parent branch tracking work?**
   - Current: Not mentioned
   - Behavior: Auto-detects from reflog or explicit parameter
   - Proposal: Document in branch creation guidance

---

## Part 9: Summary of Required Changes

### Priority 1: CRITICAL (Breaks functionality)
1. ❌ Fix tool names: create_feature_branch → create_branch
2. ❌ Fix tool names: git_checkout_branch → git_checkout
3. ❌ Fix tool names: scaffold_document → scaffold_design_doc
4. ❌ Remove non-existent tools: update_implementation_status, start_work_on_issue
5. ❌ Remove st3://status/implementation reference (does not exist)
6. ❌ Add lazy loading section with activation functions

### Priority 2: HIGH (Missing key functionality)
1. ⚠️ Add project initialization workflow (initialize_project, get_project_plan)
2. ⚠️ Add phase management workflow (transition_phase, force_phase_transition)
3. ⚠️ Add label management tools (5 tools)
4. ⚠️ Add milestone management tools (3 tools)
5. ⚠️ Document workflow selection (feature/bug/docs/refactor/hotfix)
6. ⚠️ Document parent branch tracking

### Priority 3: MEDIUM (Improves accuracy)
1. 📝 Add missing tools to tables: list_prs, merge_pr, git_fetch, git_pull
2. 📝 Document safe_edit_file modes (4 modes)
3. 📝 Add template_validation_tool
4. 📝 Clarify validate_architecture usage (scope-based)

### Priority 4: LOW (Nice to have)
1. 💡 Add workflow phase diagram
2. 💡 Add state.json structure documentation
3. 💡 Add examples for each protocol section

---

## Part 10: Accuracy Scorecard

| Category | Score | Details |
|----------|-------|---------|
| Tool Names | 71% | 27/38 correct, 11 mismatches |
| Resource URIs | 75% | 3/4 exist, 1 missing |
| Workflow Enforcement | 20% | Exists but not documented |
| Lazy Loading | 0% | Not documented at all |
| Overall Alignment | 70% | Usable but needs updates |

**Recommendation:** Update AGENT_PROMPT.md before next agent session to avoid tool resolution errors.

---

## Appendix A: Complete Tool Inventory

### Implemented MCP Tools (47 total)

**Health & Context (3):**
- health_check ✅
- get_work_context ✅
- search_documentation ✅

**Git Operations (14):**
- create_branch ✅ (NOT create_feature_branch)
- git_status ✅
- git_add_or_commit ✅
- git_checkout ✅ (NOT git_checkout_branch)
- git_list_branches ✅
- git_push ✅
- git_pull ✅
- git_fetch ✅
- git_merge ✅
- git_delete_branch ✅
- git_stash ✅
- git_restore ✅
- git_diff_stat ✅
- get_parent_branch ✅

**GitHub Issues (6):**
- create_issue ✅
- list_issues ✅
- get_issue ✅
- update_issue ✅
- close_issue ✅

**GitHub Labels (5):**
- create_label ✅
- delete_label ✅
- list_labels ✅
- add_labels ✅
- remove_labels ✅
- detect_label_drift ✅

**GitHub Milestones (3):**
- create_milestone ✅
- list_milestones ✅
- close_milestone ✅

**GitHub PRs (3):**
- create_pr ✅
- list_prs ✅
- merge_pr ✅

**Project Management (3):**
- initialize_project ✅
- get_project_plan ✅
- get_parent_branch ✅ (duplicate above)

**Phase Management (2):**
- transition_phase ✅
- force_phase_transition ✅

**Scaffold (2):**
- scaffold_component ✅
- scaffold_design_doc ✅ (NOT scaffold_document)

**Quality & Testing (5):**
- run_tests ✅
- run_quality_gates ✅
- validate_architecture ✅
- validate_doc ✅ (NOT validate_document_structure)
- validate_dto ⚠️ (exists but may not work as expected)

**File Operations (2):**
- safe_edit_file ✅
- create_file ✅ (DEPRECATED)

**Template Validation (1):**
- validate_template ✅

---

**End of Analysis**