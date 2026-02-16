<!-- docs/reference/mcp/migration_v2.0.md -->
<!-- template=generic_doc version=43c84181 created=2026-02-16T22:45:00Z updated= -->
# Migration Guide: v1.x → v2.0

**Status:** APPROVED  
**Version:** 2.0.0  
**Last Updated:** 2026-02-16

---

## Purpose

Guide teams to migrate from phase-first commit scopes to workflow-first commit scopes in ST3.

## Scope

**In Scope:**
Commit message format migration, workflow phase mapping, sub-phase usage, validation workflow.

**Out of Scope:**
Runtime trading logic, infrastructure changes, unrelated refactors.

## Prerequisites

Read these first:
1. Read agent.md workflow protocol
2. Ensure branch has initialized workflow state
3. Understand legacy phase parameter usage
---

## Summary

v2.0 replaces legacy phase-based commit metadata with workflow-phase aware scopes and keeps backward compatibility for existing history.

---

## Key Changes

- New scope format: P_{WORKFLOW_PHASE}_SP_{SUB_PHASE}
- New git_add_or_commit parameters: workflow_phase + sub_phase
- Legacy phase parameter deprecated (backward compatible)

---

## Migration Steps

1. Replace phase="red|green|refactor|docs" with workflow_phase/sub_phase.
2. Use transition_phase between workflow milestones.
3. Run run_quality_gates before PR creation.

---

## Validation Checklist

- [ ] No new commits use legacy phase parameter.
- [ ] All TDD commits include workflow sub-phase.
- [ ] File-specific quality gates pass for touched files.
- [ ] Migration guide rendered via scaffold_artifact generic_doc.

---

## FAQ

### Q: Do existing old-format commits break?

A: No. Existing history remains valid and readable.

### Q: Is workflow_phase always required?

A: Can be auto-detected from state, but explicit usage is recommended.


---

## Workflow Mapping

- research/planning/design/integration/documentation use phase-level scope
- tdd uses phase + sub-phase scope

- [ ] Mappings reviewed with team
- [ ] Examples verified in docs

## Rollback Strategy

If migration causes confusion, keep using v2.0 tooling and document old-to-new mapping in PR templates until adoption is complete.

## Related Documentation
- **[agent.md][related-1]**
- **[docs/development/issue138/planning.md][related-2]**

<!-- Link definitions -->

[related-1]: agent.md
[related-2]: docs/development/issue138/planning.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2026-02-16 | Agent | Initial draft |