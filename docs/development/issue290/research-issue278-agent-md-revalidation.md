<!-- c:\temp\st3\docs\development\issue290\research-issue278-agent-md-revalidation.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T13:03Z updated=2026-04-26 -->
# Research — Issue #278 agent.md Revalidation

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Revalidate whether issue #278 still reflects the current agent.md content or has been substantially fixed already.

## Scope

**In Scope:**
agent.md claims called out explicitly in issue #278 and their correspondence with current config/tool behavior.

**Out of Scope:**
Broader documentation quality outside agent.md and implementation work unrelated to the listed stale claims.

## Prerequisites

Read these first:
1. Issue #278 description
2. agent.md
3. .st3/config/workflows.yaml
4. mcp_server/tools/git_tools.py
5. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Problem Statement

Issue #278 reported a cluster of stale and incorrect claims in agent.md that allegedly caused agent failures in practice.

## Research Goals

- Check the current agent.md against the original issue claims.
- Determine which claims are fixed, which remain, and whether the issue should be narrowed or closed.
- Capture the current root problem if the original issue statement is stale.
- Define expected results for either closure or a narrower follow-up.

---

## Background

Issue #278 was raised as a documentation-correctness issue covering phase names, git_add_or_commit examples, scaffolding guidance, artifact paths, and workflow ordering.

The current agent.md has already been updated in several of the exact areas named by the issue, so the revalidation question is whether the old checklist still describes active defects or merely historical ones.

---

## Findings

### Finding 1 — Most of the originally listed stale claims have been corrected

The current agent.md now reflects the corrected implementation in the major areas called out by issue #278, including:

- `implementation` and `validation` terminology in workflow tables
- explicit `cycle_number` requirement for implementation commits
- warning that `phase` is not a valid `git_add_or_commit` parameter
- `output_path` documented as optional for scaffolding
- artifacts registry path documented as `.st3/config/artifacts.yaml`
- `generate_test` documented as not yet implemented
- `introspect_template` documented as an internal Python function, not a callable MCP tool
- bug and epic workflow phase order matching the current workflows config

That means the bulk of the issue's original checklist is now stale.

### Finding 2 — The specific "ready is non-existent" claim is no longer valid

The old issue claimed that `ready` was a non-existent phase used incorrectly in examples.

Current evidence shows that `ready` is a valid terminal workflow phase in the broader phase model and is referenced consistently in enforcement/tests. So this claim no longer holds.

### Finding 3 — The issue is now too broad to remain useful in its original form

Because most of the named claims are already fixed, the issue no longer points to one coherent unresolved problem. As written, it mixes historical defects that have been corrected with any possible residual documentation drift.

That makes it a poor planning unit in its current form.

### Finding 4 — Residual concerns, if any, are now narrow maintenance concerns

One possible remaining nuance is that some summary tables describe workflow-specific phases while terminal readiness behavior is described elsewhere, which can be mildly confusing on first read.

But that is not the same severity or shape as the original issue's large stale-claims bundle.

---

## Architecture Check

### Alignment with Explicit over Implicit

The current agent.md is materially more explicit than the version described in issue #278. It now documents several implementation constraints that previously caused failures.

### Alignment with SSOT

The current document appears much closer to the actual tool/config surfaces it references, especially for workflow phases and scaffolding behavior.

### Alignment with YAGNI

The right next step is not another broad sweep issue repeating historical claims. If a residual problem remains, it should be captured as a narrow documentation drift issue with one concrete mismatch.

---

## Solution Directions

### Direction A — Close or narrow issue #278

The current issue should not remain open unchanged because most of its original claims have already been corrected.

### Direction B — If follow-up work is desired, file a smaller documentation issue

Any replacement issue should name one currently verifiable mismatch instead of carrying forward the old ten-point bundle.

### Direction C — Keep documentation drift checks tied to implementation evidence

Future agent.md maintenance issues should reference the exact config or code surface they claim is out of sync.

---

## Expected Results

This research supports the following expected outcomes for issue #278:

- The issue should be treated as largely stale in its current broad form.
- Most of the original stale claims should not be used as active planning inputs anymore.
- Any remaining documentation work should be captured as one or more narrower, evidence-backed follow-up issues.

## Open Questions

- Do we want to close #278 outright, or keep it open only long enough to split out any genuinely remaining narrow doc mismatches?
- Should agent.md gain an explicit note explaining that workflow tables list workflow phases while `ready` is the terminal phase used for PR submission?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[agent.md][related-2]**
- **[.st3/config/workflows.yaml][related-3]**
- **[mcp_server/tools/git_tools.py][related-4]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: agent.md
[related-3]: .st3/config/workflows.yaml
[related-4]: mcp_server/tools/git_tools.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Revalidated issue #278 and concluded that most originally reported stale claims have already been corrected |
