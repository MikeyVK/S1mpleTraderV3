<!-- docs\development\issue263\planning_sub_role_detection_v2.md -->
<!-- template=planning version=130ac5ea created=2026-03-21T21:26Z updated= -->
# Sub-Role Detection V2 — Bug-Fix Planning (C_V2.8–C_V2.11)

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-21

---

## Scope

**In Scope:**
_paths.py, detect_sub_role.py, stop_handover_guard.py, test_detect_sub_role.py, test_stop_handover_guard.py, integration smoke tests

**Out of Scope:**
Prompt body rewrites, acceptance tests (C_V2.7), reference documentation updates, sub-role-requirements.yaml schema changes

## Prerequisites

Read these first:
1. Research doc approved (research_sub_role_detection_v2.md, commit bdb0c49)
2. 63/63 tests green on branch feature/263-vscode-implementation-orchestration
3. Phase transitioned: research → planning
---

## Summary

Four TDD cycles to fix three confirmed bugs in the copilot orchestration hook system: (1) role-scoped state files replacing shared STATE_RELPATH, (2) first-word detection with slash-command prefix stripping replacing the broken idempotency lock, (3) exploration mode pass-through and ConfigError catch in the stop hook, and (4) test updates covering all new behaviours. The existing 63 tests remain green throughout.

---

## TDD Cycles


### Cycle 1: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 2: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 3: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 4: 

**Goal:** 

**Tests:**

**Success Criteria:**


## Related Documentation
- **[docs/development/issue263/research_sub_role_detection_v2.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/research_sub_role_detection_v2.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |