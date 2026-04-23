# MCP Server Gap Analysis & Implementation Plan

**Status:** SUPERSEDED  
**Created:** 2025-12-09  
**Branch:** feature/git-tools-complete (historical)  
**Superseded By:** [docs/reference/mcp/MCP_TOOLS.md](../reference/mcp/MCP_TOOLS.md), [docs/reference/mcp/tools/README.md](../reference/mcp/tools/README.md)

> Historical implementation plan from the pre-public-tool-surface phase. It is retained for project history only.
> Do not use it as the current MCP tool contract. Public PR creation now uses `submit_pr`, not `create_pr`.

---

## 1. Gap Analysis

### 1.1 Current State Assessment

#### Implemented Tools (12)

| Tool | Category | Status | Notes |
|------|----------|--------|-------|
| `git_status` | Git | ✅ Working | |
| `create_feature_branch` | Git | ✅ Working | |
| `git_add_or_commit` | Git | ✅ Working | NEW - TDD phases |
| `git_checkout` | Git | ✅ Working | NEW |
| `git_push` | Git | ✅ Working | NEW |
| `git_merge` | Git | ✅ Working | NEW |
| `git_delete_branch` | Git | ✅ Working | NEW |
| `run_quality_gates` | Quality | ✅ Working | |
| `run_tests` | Quality | ⚠️ Hangs | Needs debugging |
| `validate_architecture` | Quality | ✅ Working | |
| `validate_dto` | Quality | ✅ Working | |
| `validate_document_structure` | Quality | ✅ Working | |
| `create_file` | Development | ⚠️ Inadequate | No template support |
| `create_issue` | GitHub | ✅ Working | Requires GITHUB_TOKEN |
| `create_pr` | GitHub | ✅ Working | Requires GITHUB_TOKEN |
| `add_labels` | GitHub | ✅ Working | Requires GITHUB_TOKEN |
| `health_check` | Utility | ✅ Working | |

#### Missing Tools (per TOOLS.md specification)

| Tool | Category | Priority | Documented In |
|------|----------|----------|---------------|
| `scaffold_component` | Implementation | 🔴 CRITICAL | TOOLS.md §4.1 |
| `scaffold_design_doc` | Implementation | 🟡 HIGH | TOOLS.md §4.2 |
| `scaffold_document` | Documentation | 🟡 HIGH | TOOLS.md §3.3 |
| `search_documentation` | Discovery | 🟡 HIGH | TOOLS.md §1.1 |
| `get_work_context` | Planning | 🟡 HIGH | TOOLS.md §1.2 |
| `update_issue` | GitHub | 🟢 MEDIUM | TOOLS.md §2.3 |
| `git_stash` | Git | 🟢 MEDIUM | Not documented |
| `fix_whitespace` | Quality | 🟢 MEDIUM | TOOLS.md §5.3 |

#### Missing Managers (per ARCHITECTURE.md)

| Manager | Status | Dependencies |
|---------|--------|--------------|
| `scaffold_manager.py` | ❌ Missing | Jinja2, Templates |
| `doc_manager.py` | ⚠️ Partial | FileSystem adapter |

### 1.2 Functional Gaps

#### GAP-1: Template-Driven Code Generation
**Current:** `create_file` accepts raw content
**Required:** `scaffold_component` generates from Jinja2 templates
**Impact:** No structure enforcement, boilerplate not standardized
**Source:** ARCHITECTURE.md §4, TOOLS.md §4.1

#### GAP-2: Test Runner Reliability
**Current:** `run_tests` hangs on execution
**Required:** Reliable pytest execution with output capture
**Impact:** Cannot automate TDD workflow
**Source:** TDD_WORKFLOW.md, PHASE_WORKFLOWS.md §7

#### GAP-3: Context-Aware Workflow
**Current:** No `get_work_context` or `search_documentation`
**Required:** AI can query project state and find relevant docs
**Impact:** AI cannot self-orient without manual file reads
**Source:** TOOLS.md §1.1, §1.2

#### GAP-4: Complete Git Workflow
**Current:** No `git_stash` tool
**Required:** Full git lifecycle support
**Impact:** Cannot handle dirty working directory gracefully
**Source:** Derived from usage patterns

---

## 2. Implementation Phases

### Phase 1: Stabilization (Priority: CRITICAL)
**Goal:** Fix broken functionality before adding new features

| Task | Type | Tests | Acceptance |
|------|------|-------|------------|
| 1.1 Debug `run_tests` hanging | Fix | Existing | Tool completes within 60s |
| 1.2 Add `git_stash` tool | Feature | 6 new | Stash/pop/list operations |
| 1.3 Verify all 17 tools work | Test | Integration | E2E test suite |

**Deliverables:**
- All tools operational
- Integration test for each tool
- Tool reliability documentation

### Phase 2: Scaffold Manager (Priority: HIGH)
**Goal:** Template-driven code generation

| Task | Type | Tests | Acceptance |
|------|------|-------|------------|
| 2.1 Create `ScaffoldManager` | Feature | 15 new | Manager handles templates |
| 2.2 Create Jinja2 templates | Feature | - | Templates in `mcp_server/templates/` |
| 2.3 Implement `scaffold_component` | Feature | 10 new | DTO/Worker/Adapter scaffolding |
| 2.4 Implement `scaffold_design_doc` | Feature | 5 new | Design doc scaffolding |
| 2.5 Deprecate raw `create_file` | Refactor | - | Warn on usage |

**Templates to create:**
```
mcp_server/templates/
├── components/
│   ├── dto.py.jinja2
│   ├── dto_test.py.jinja2
│   ├── worker.py.jinja2
│   ├── worker_test.py.jinja2
│   ├── adapter.py.jinja2
│   ├── adapter_test.py.jinja2
│   ├── manager.py.jinja2
│   ├── manager_test.py.jinja2
│   └── tool.py.jinja2
└── documents/
    ├── design.md.jinja2
    ├── reference.md.jinja2
    └── architecture.md.jinja2
```

**Deliverables:**
- `ScaffoldManager` with template loading
- `scaffold_component` tool for DTO, Worker, Adapter, Manager, Tool
- `scaffold_design_doc` tool
- All templates tested

### Phase 3: Discovery Tools (Priority: HIGH)
**Goal:** AI can self-orient in the project

| Task | Type | Tests | Acceptance |
|------|------|-------|------------|
| 3.1 Implement `search_documentation` | Feature | 8 new | Fuzzy search in docs/ |
| 3.2 Implement `get_work_context` | Feature | 6 new | Aggregate issues + branch + phase |
| 3.3 Update `DocManager` | Refactor | - | Add search capabilities |

**Deliverables:**
- Semantic/fuzzy doc search
- Work context aggregation
- Phase detection from branch name

### Phase 4: Workflow Automation (Priority: MEDIUM)
**Goal:** Automated transitions and enforcement

| Task | Type | Tests | Acceptance |
|------|------|-------|------------|
| 4.1 Implement `update_issue` | Feature | 5 new | Label/state transitions |
| 4.2 Implement phase transition logic | Feature | 8 new | Auto-label on TDD phase |
| 4.3 Implement `fix_whitespace` | Feature | 4 new | Auto-fix common issues |

**Deliverables:**
- Issue updates with label transitions
- Phase-aware workflow automation
- Auto-fix for quality issues

---

## 3. Build Order (Dependency Graph)

```
Phase 1: Stabilization
├── 1.1 Fix run_tests (no deps)
├── 1.2 git_stash (depends on GitAdapter)
└── 1.3 Integration tests (depends on 1.1, 1.2)

Phase 2: Scaffold Manager
├── 2.1 ScaffoldManager (depends on Jinja2)
├── 2.2 Templates (no deps)
├── 2.3 scaffold_component (depends on 2.1, 2.2)
├── 2.4 scaffold_design_doc (depends on 2.1, 2.2)
└── 2.5 Deprecate create_file (depends on 2.3)

Phase 3: Discovery Tools
├── 3.1 search_documentation (depends on DocManager)
├── 3.2 get_work_context (depends on GitManager, GitHubManager)
└── 3.3 DocManager update (depends on 3.1)

Phase 4: Workflow Automation
├── 4.1 update_issue (depends on GitHubManager)
├── 4.2 Phase transitions (depends on 4.1)
└── 4.3 fix_whitespace (depends on QAManager)
```

---

## 4. TDD Workflow Per Task

Elke taak volgt strict TDD:

```
1. Create GitHub Issue (via create_issue tool)
2. Create feature branch (via create_feature_branch tool)
3. RED: Write failing tests (via scaffold_component when available)
4. GREEN: Implement minimal code
5. REFACTOR: Quality gates (via run_quality_gates tool)
6. Commit (via git_add_or_commit tool)
7. Push (via git_push tool)
8. Create PR (via create_pr tool)
9. Merge (via git_merge tool after review)
10. Delete branch (via git_delete_branch tool)
```

---

## 5. Success Criteria

### Phase 1 Complete When:
- [ ] `run_tests` completes within 60s for any test path
- [ ] `git_stash` can stash, pop, and list
- [ ] All 17+ tools have integration tests
- [ ] Zero tools hang or fail silently

### Phase 2 Complete When:
- [ ] `scaffold_component` generates DTO with tests
- [ ] `scaffold_component` generates Worker with tests
- [ ] `scaffold_component` generates Tool with tests
- [ ] Generated code passes quality gates
- [ ] Templates match project standards

### Phase 3 Complete When:
- [ ] `search_documentation` finds relevant docs
- [ ] `get_work_context` shows current issue + phase
- [ ] AI can self-orient without manual file reads

### Phase 4 Complete When:
- [ ] Issue labels update on TDD phase transition
- [ ] Workflow is fully automatable via MCP tools
- [ ] Zero CLI commands needed for standard workflow

---

## 6. Estimated Effort

| Phase | Tasks | New Tests | Days |
|-------|-------|-----------|------|
| 1. Stabilization | 3 | ~15 | 1-2 |
| 2. Scaffold Manager | 5 | ~35 | 3-4 |
| 3. Discovery Tools | 3 | ~15 | 2-3 |
| 4. Workflow Automation | 3 | ~15 | 2-3 |
| **Total** | **14** | **~80** | **8-12** |

---

## 7. Next Steps

1. **Merge current feature branch** to `mcp-server-foundation`
2. **Create Phase 1 issues** via `create_issue` tool
3. **Start with Task 1.1**: Debug `run_tests` hanging
4. **Update this document** after each phase completion

---

**Document maintained by:** AI Assistant + User  
**Last Updated:** 2025-12-09
