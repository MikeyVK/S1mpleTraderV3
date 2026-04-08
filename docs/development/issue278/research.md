<!-- docs\development\issue278\research.md -->
<!-- template=research version=8b7bb3ab created=2026-04-08T19:51Z updated= -->
# Gap Analysis: agent.md vs. Implementation

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-08

---

## Purpose

Document all verified gaps between agent.md claims and actual implementation, discovered via static QA analysis on 2026-04-08.

## Scope

**In Scope:**
agent.md instructional claims, workflow phase definitions, MCP tool signatures, scaffold_artifact behaviour, git_add_or_commit API

**Out of Scope:**
Fixes, implementation changes, test updates

## Prerequisites

Read these first:
1. agent.md read fully
2. workflows.yaml verified
3. workphases.yaml verified
4. artifacts.yaml verified
5. git_tools.py GitCommitInput verified
6. artifact_manager.py scaffold path resolution verified
---

## Problem Statement

agent.md contains multiple stale and incorrect claims that cause agent runtime failures. Gaps were found between documented behaviour and actual source code.

## Research Goals

- Identify all incorrect phase names and workflow orders in agent.md
- Verify git_add_or_commit API claims against GitCommitInput implementation
- Validate scaffold_artifact behaviour claims against ArtifactManager
- Check which MCP tools described in agent.md actually exist
- Produce a complete prioritised findings list for @imp to act on

---

## Findings

Ten verified gaps found across five categories: (A) Workflow phase names/order — 'tdd' and 'integration' used throughout but actual phase names are 'implementation' and 'validation'; bug workflow has design before planning (not planning before design); epic ends with coordination+documentation not tdd+integration; force_phase_transition example uses non-existent phase 'ready'. (B) git_add_or_commit API — legacy git_add_or_commit(phase='red') documented as working but crashes due to model_config extra='forbid' (no 'phase' field exists); cycle_number is required for implementation phase but completely absent from docs; workflow_phase field description in source still lists 'tdd|integration' instead of 'implementation|validation'. (C) introspect_template described as callable MCP tool but is an internal function only (introspect_template_with_inheritance in issue_tools.py). (D) restart_server() shown without args but requires reason: str (has default so does not crash, just misleading). (E) artifacts.yaml path documented as .st3/artifacts.yaml but actual path is .st3/config/artifacts.yaml. (F) Automatic test file generation claimed for scaffold_artifact but generate_test flag is never read by ArtifactManager — feature not implemented. (G) output_path claimed as required for file artifacts (raises ERR_VALIDATION if omitted) but ArtifactManager auto-resolves via DirectoryPolicyResolver when omitted. (H) Tool activation via activate_* commands documented in section 1.1 but those commands do not exist; actual mechanism is tool_search_tool_regex.

## Open Questions

- ❓ Is the legacy phase= parameter intentionally removed or is there a migration path?
- ❓ Is generate_test planned for a future issue or silently abandoned?
- ❓ Should the workflow_phase field description in git_tools.py be updated as part of this issue or separately?


## Related Documentation
- **[agent.md][related-1]**
- **[.st3/config/workflows.yaml][related-2]**
- **[.st3/config/workphases.yaml][related-3]**
- **[.st3/config/artifacts.yaml][related-4]**
- **[mcp_server/tools/git_tools.py][related-5]**
- **[mcp_server/managers/artifact_manager.py][related-6]**
- **[mcp_server/schemas/contexts/research.py][related-7]**

<!-- Link definitions -->

[related-1]: agent.md
[related-2]: .st3/config/workflows.yaml
[related-3]: .st3/config/workphases.yaml
[related-4]: .st3/config/artifacts.yaml
[related-5]: mcp_server/tools/git_tools.py
[related-6]: mcp_server/managers/artifact_manager.py
[related-7]: mcp_server/schemas/contexts/research.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |