<!-- docs\development\issue422\design.md -->
<!-- template=design version=5827e841 created=2026-07-08T18:52Z updated= -->
# Design for fixing dirty worktree defect in git_add_or_commit

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-08

---

## Purpose

Define the technical design for fixing the dirty worktree defect in git_add_or_commit.

## Prerequisites

Read these first:
1. Issue #422 description
2. docs/development/issue422/research.md
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. docs/coding_standards/DOCUMENTATION_STANDARD.md
---

## 1. Context & Requirements

### 1.1. Problem Statement

The commit tool (git_add_or_commit) mutates .pgmcp/state.json after the Git commit transaction. This leaves the workspace dirty with a modified state.json. We must correct this while preventing domain leakage in GitAdapter, ensuring transaction safety (rollback), and resolving the state.json path dynamically to comply with SSOT.

### 1.2. Requirements

**Functional:**
- [ ] The workspace remains in a clean state after executing git_add_or_commit
- [ ] Metadata updates (sub_phase in state.json) are included in the same commit
- [ ] State changes are rolled back if the Git commit transaction fails

**Non-Functional:**
- [ ] Zero domain leakage: GitAdapter remains generic and unaware of state.json
- [ ] SSOT compliance: state.json path must be resolved dynamically via PhaseStateEngine.state_path relative to repository root
- [ ] Maintain full backwards-compatibility with existing unit and integration tests

### 1.3. Constraints

- Avoid hardcoding state.json path to comply with SSOT
- Do not add workflow-specific knowledge to GitAdapter
- Roll back state.json mutation on commit failure
---

## 2. Design Options

### 2.1. Option A: Option 1: Tool-layer orchestration with rollback and dynamic path resolution

Mutate state.json before the commit in GitCommitTool.execute(). If files are specified, append state.json's relative path. Implement a try-except rollback block. GitAdapter remains generic.

**Pros:**
- ✅ Clean separation of concerns
- ✅ No domain leakage in GitAdapter
- ✅ Transactional safety (rollback)
- ✅ Dynamic path resolution complies with SSOT.

**Cons:**
- ❌ Requires updating GitCommitTool unit tests because the mocked commit call will now include state.json in the files list.

### 2.2. Option B: Option 2: Implicit staging in GitAdapter.commit()

Stage state.json automatically in GitAdapter.commit() if it exists on disk. Mutate state.json before the commit in GitCommitTool.

**Pros:**
- ✅ Unit tests mocking GitManager in GitCommitTool would not need updates.

**Cons:**
- ❌ Violates 'Explicit over Implicit' and SRP.
- ❌ Introduces domain leakage (GitAdapter becomes aware of workflow state.json).
- ❌ Can cause side effects in other tools using GitAdapter (like SubmitPRTool).
---

## 3. Chosen Design

**Decision:** Update state.json before the Git commit in GitCommitTool.execute(). In the tool layer, dynamically resolve the relative path of state.json and explicitly append it to the files list if specific files are targeted. Add a try-except rollback block in the tool to restore state.json to its original sub_phase on commit failure.

**Rationale:** This design correctly resolves the dirty worktree issue while keeping the GitAdapter generic (no domain leakage). The rollback handler ensures transactional integrity. Resolving the path dynamically via PhaseStateEngine and GitAdapter.repo_path complies with SSOT and prevents hardcoding paths.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Orchestrate state.json mutation, file appending, and rollback in GitCommitTool.execute() instead of GitAdapter. | Adheres to SOLID (SRP) and prevents domain leakage. Ensures GitAdapter remains a generic infrastructure wrapper. |
| Resolve state.json path dynamically using self._state_engine.state_path relative to Path(self.manager.adapter.repo_path). | Complies with SSOT. Prevents hardcoding path to state.json, allowing it to adapt to custom settings configurations. |

## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/development/issue422/research.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/development/issue422/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-08 | Agent | Initial draft |