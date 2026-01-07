# Issue #39 Planning: Dual-Mode State Management Implementation

**Status:** DRAFT  
**Phase:** Planning  
**Date:** 2025-12-30

---

## Purpose

Plan the implementation of dual-mode state management to fix two infrastructure gaps:
1. **Mode 1:** Atomic initialization (InitializeProjectTool creates both files)
2. **Mode 2:** Auto-recovery (PhaseStateEngine reconstructs missing state)

This document defines **what to build, acceptance criteria, risks, and sequencing** - NOT technical design details.

---

## Scope

**In Scope:**
- Enhancement of InitializeProjectTool to create state.json atomically
- Auto-recovery logic in PhaseStateEngine.get_state()
- Phase detection utility for git commit parsing
- .gitignore update to exclude state.json
- Test strategy for both modes

**Out of Scope:**
- Epic #18 enforcement logic (tool permissions, quality gates)
- GetWorkContextTool enhancement (future issue)
- PhaseDetector refactoring as separate utility (may be inline in PhaseStateEngine)
- Multi-machine conflict resolution (git remains SSOT, no state merging)

---

## Implementation Goals

### Goal 1: Atomic Initialization (Mode 1)
**Objective:** InitializeProjectTool creates both projects.json AND state.json in single operation

**Success Criteria:**
- ✅ Single tool call initializes complete project state
- ✅ Both files created or neither (atomic operation)
- ✅ Branch name auto-detected from git
- ✅ First phase auto-determined from workflow
- ✅ No manual file editing required

**What Changes:**
- InitializeProjectTool gains dependencies: GitManager, PhaseStateEngine
- Execute method calls PhaseStateEngine.initialize_branch() after creating projects.json
- Error handling: If state creation fails, report error (don't rollback projects.json)

### Goal 2: Auto-Recovery (Mode 2)
**Objective:** PhaseStateEngine reconstructs missing state automatically and transparently

**Success Criteria:**
- ✅ Missing state.json detected on get_state() call
- ✅ State reconstructed from projects.json + git commits
- ✅ User experiences transparent recovery (no manual steps)
- ✅ Safe fallback to first phase if inference fails
- ✅ Reconstruction logged for audit

**What Changes:**
- PhaseStateEngine.get_state() checks for missing state
- New reconstruction logic: Extract issue → Load project → Infer phase from git
- Phase detection from commit messages (explicit keywords + conventional commits)
- State flagged as `reconstructed: true` for audit

### Goal 3: Phase Detection Utility
**Objective:** Reliable phase inference from git commit messages

**Success Criteria:**
- ✅ Detects explicit phase keywords ("Complete research phase", "Planning phase #67")
- ✅ Falls back to conventional commits (test: → red, feat: → green, refactor: → refactor)
- ✅ Works for ALL workflow phases (not just TDD cycle)
- ✅ Safe fallback to first phase of workflow

**What Changes:**
- Shared detection logic (may be methods on PhaseStateEngine, not separate utility)
- Multi-strategy detection: explicit keywords → conventional commits → fallback
- Workflow-aware (uses projects.json for valid phase list)

---

## Component Changes

### 1. InitializeProjectTool (mcp_server/tools/project_tools.py)
**Current Behavior:** Creates projects.json only  
**Planned Behavior:** Creates projects.json + state.json atomically

**Changes:**
- Add GitManager import and instantiation
- Add PhaseStateEngine import and instantiation  
- Call PhaseStateEngine.initialize_branch() after ProjectManager.initialize_project()
- Update success message to confirm both files created

**No changes needed:** ProjectManager, GitManager (already have required methods)

### 2. PhaseStateEngine (mcp_server/managers/phase_state_engine.py)
**Current Behavior:** Fails hard if state.json missing  
**Planned Behavior:** Auto-recovers missing state transparently

**Changes:**
- Enhance get_state() to detect missing branch state
- Add reconstruction methods (extract issue, infer phase from git)
- Add phase detection logic (explicit keywords, conventional commits, fallback)
- Set `reconstructed: true` flag in recovered state
- Add logging for reconstruction events

**Methods to Add:**
- `_reconstruct_branch_state(branch)` - Main recovery orchestration
- `_extract_issue_from_branch(branch)` - Parse branch name for issue number
- `_infer_phase_from_git(branch, workflow_phases)` - Phase detection from commits
- `_detect_explicit_phase_keywords(commits, phases)` - Strategy 1
- `_detect_conventional_commits(commits)` - Strategy 2

### 3. .gitignore
**Changes:**
- Add `.st3/state.json` to ensure runtime state not committed

---

## Acceptance Criteria

### Mode 1 (Initialization)
- [ ] InitializeProjectTool creates both projects.json and state.json
- [ ] Branch name auto-detected from GitManager
- [ ] First phase set to workflow's first phase
- [ ] Works for all workflow types (feature, bug, docs, refactor, hotfix, custom)
- [ ] Error message clear if initialization fails
- [ ] No breaking changes to existing projects.json format

### Mode 2 (Recovery)
- [ ] Missing state.json triggers auto-recovery (not hard error)
- [ ] State reconstructed from projects.json + git commits
- [ ] Phase inferred correctly from commit messages
- [ ] Defaults to first phase if no commits found
- [ ] `reconstructed: true` flag set in state
- [ ] Reconstruction logged at INFO level
- [ ] Works across machines (git pull scenario)

### Both Modes
- [ ] No manual JSON editing required
- [ ] state.json in .gitignore
- [ ] JSON format consistent (Python-to-Python)
- [ ] TransitionPhaseTool works after initialization
- [ ] TransitionPhaseTool works after recovery
- [ ] GetWorkContextTool still functions (uses separate git parsing)

### Edge Cases Handled
- [ ] Invalid branch name format (error, not crash)
- [ ] Missing projects.json (error with guidance)
- [ ] Git command failures (fallback to first phase, log warning)
- [ ] Mid-phase uncommitted work (recovers to last committed phase)
- [ ] No phase-related commits yet (defaults to first phase)

---

## Risk Assessment

### Risk 1: Transition History Lost on Recovery
**Impact:** HIGH - Users lose audit trail after machine switch  
**Likelihood:** CERTAIN - Cannot reconstruct transitions from git  
**Mitigation:** 
- Document limitation clearly
- `reconstructed: true` flag alerts users
- Acceptable trade-off for cross-machine DX

### Risk 2: Phase Inference Accuracy
**Impact:** MEDIUM - Wrong phase inferred from commits  
**Likelihood:** LOW - Multi-strategy detection + safe fallback  
**Mitigation:**
- Require commit message conventions (already documented practice)
- Safe fallback to first phase
- User can manually transition if needed

### Risk 3: Backward Compatibility
**Impact:** LOW - Existing projects may need re-initialization  
**Likelihood:** MEDIUM - Projects created before this fix  
**Mitigation:**
- Auto-recovery handles missing state.json
- Existing projects work automatically via Mode 2
- No breaking changes to projects.json format

### Risk 4: Git Dependency for Recovery
**Impact:** LOW - Recovery fails if git unavailable  
**Likelihood:** LOW - Git always present in development workflow  
**Mitigation:**
- Fallback to first phase on git errors
- Log warning for debugging
- Graceful degradation

---

## Implementation Sequence

### Phase 1: Preparation
1. Add state.json to .gitignore
2. Verify GitManager has get_recent_commits() method (or add it)
3. Review PhaseStateEngine.initialize_branch() (ensure ready for use)

### Phase 2: Mode 1 Implementation (TDD)
1. Write tests for InitializeProjectTool enhancement
2. Implement GitManager integration
3. Implement PhaseStateEngine.initialize_branch() call
4. Verify atomic creation of both files
5. Test all workflow types

### Phase 3: Mode 2 Implementation (TDD)
1. Write tests for auto-recovery scenarios
2. Implement get_state() enhancement (detect missing state)
3. Implement reconstruction orchestration
4. Implement phase detection logic (multi-strategy)
5. Verify cross-machine scenario

### Phase 4: Integration Testing
1. Test full workflow: initialize → work → push → pull → transition
2. Test edge cases (invalid branch, missing project, git errors)
3. Verify existing tools (TransitionPhaseTool, GetWorkContextTool) unaffected
4. Performance check (recovery should be fast)

### Phase 5: Documentation
1. Update InitializeProjectTool documentation
2. Document auto-recovery behavior for users
3. Add troubleshooting guide
4. Update commit message conventions guide

---

## Success Metrics

**Primary Metrics:**
- InitializeProjectTool creates both files in 100% of cases
- Auto-recovery succeeds in 95%+ of cross-machine scenarios
- 0 breaking changes to existing tools

**Secondary Metrics:**
- Phase inference accuracy >90% (when commits present)
- Safe fallback occurs <10% of time (commits usually have phase info)
- User intervention required: 0 times for normal workflows

---

## Dependencies

**Blocked By:**
- None (all required components exist)

**Blocks:**
- Epic #18 child issues (tool permission enforcement, quality gates)
- Future GetWorkContextTool enhancement issue

**Related:**
- Issue #42 (8-phase model) - Defines phase sequences we track
- Issue #48 (Git as SSOT) - Our recovery approach provides implementation pattern
- Issue #45 (state.json structure) - We ensure consistent creation

---

## Open Questions

1. **Q:** Should PhaseDetector be separate utility class or inline methods on PhaseStateEngine?  
   **Decision:** Start inline, extract if needed later (YAGNI)

2. **Q:** Should reconstruction create empty transitions array or attempt to parse git log?  
   **Decision:** Empty array - cannot reliably reconstruct history

3. **Q:** Should recovery log at INFO or DEBUG level?  
   **Decision:** INFO - important for user awareness, not too noisy

4. **Q:** Should InitializeProjectTool rollback projects.json if state.json creation fails?  
   **Decision:** No - report error, let user retry. Avoid complex rollback logic.

---

## Next Phase

After planning approval, proceed to **Design Phase** for:
- Detailed method signatures
- Class diagrams
- Sequence diagrams for both modes
- Error handling flowcharts
- Git commit parsing algorithm details
- Test case specifications

---

**Status:** Ready for review and approval  
**Planning Complete:** Waiting for transition to design phase
