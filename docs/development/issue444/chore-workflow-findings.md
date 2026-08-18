<!-- docs/development/issue444/chore-workflow-findings.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-18T00:00Z updated=2026-08-18T00:00Z -->
# Findings: Chore Workflow Formalization

**Status:** PRELIMINARY  
**Version:** 1.0  
**Last Updated:** 2026-08-18

---

## Purpose

Record the workflow-model findings discovered while completing issue #444 and preserve them
as explicitly deferred work for coordination after this branch is merged.

## Prerequisites

Read these first:
1. Issue #444.
2. [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md).
3. [Architecture](../../manuals/architecture.md).
4. [Configuration Loading Architecture](../../reference/config-loading-architecture.md).

---

## Summary

Issue #444 was completed as a deliberately lightweight chore without formalizing a new
workflow. The investigation showed that `chore` already exists as an issue label and commit
type, but not as a first-class branch type or executable workflow. Adding it currently requires
coordinated changes across several configuration lenses, while the documentation does not
describe those dependencies as one extension procedure.

This is valid follow-up work, but it is outside the reviewed asset-reconciliation scope of
issue #444. No chore-workflow implementation or configuration change is approved by this
report. After the issue #444 branch is merged, `@co` should use these findings to create and
coordinate a dedicated issue.

## Scope

### In Scope

- Current chore-related configuration coverage.
- The complete workflow-type dependency chain found during investigation.
- Documentation and validation gaps that make workflow extension error-prone.
- Constraints and questions for a dedicated follow-up issue.
- A concrete coordination hand-off for `@co`.

### Out of Scope

- Adding `chore` to any runtime configuration.
- Changing Python production code.
- Choosing the final chore phase sequence or enforcement policy.
- Creating the follow-up issue before the issue #444 branch is merged.
- Folding workflow-model redesign into issue #444.

---

## Evidence

### Current Chore Coverage

| Concern | Current source | Observed state |
|---|---|---|
| Issue type | `.pgmcp/config/issues.yaml` | `chore` exists but maps to the `feature` workflow |
| GitHub label | `.pgmcp/config/labels.yaml` | `type:chore` exists |
| Commit type | `.pgmcp/config/git.yaml` | `chore` exists as a conventional commit type |
| Branch type | `.pgmcp/config/git.yaml` | `chore` is absent from `branch_types` |
| Branch-base policy | `.pgmcp/config/enforcement.yaml` | No explicit `chore` rule exists |
| Workflow catalog | `.pgmcp/config/workflows.yaml` | No `chore` metadata entry exists |
| Workflow contract | `.pgmcp/config/contracts.yaml` | No `chore` phase contract exists |
| Tool schemas | Runtime config injection | Branch and workflow enums are derived dynamically from config |

The current behavior is therefore internally consistent with its configuration: a chore issue
is treated as a feature, `create_branch(branch_type="chore")` is rejected, and
`initialize_project(workflow_name="chore")` is unavailable.

### Workflow-Type Dependency Chain

A first-class workflow type currently spans multiple orthogonal configuration lenses:

| Configuration | Owned truth | Required relationship for a workflow type |
|---|---|---|
| `workflows.yaml` | Workflow catalog metadata | Declares the workflow identity and execution metadata |
| `contracts.yaml` | Phase order, gates, instructions, and merge lifecycle | Supplies the executable workflow contract |
| `issues.yaml` | Issue classification | Maps one or more issue types to a workflow identity |
| `git.yaml` | Git naming and commit conventions | Declares the branch prefix when the workflow has a dedicated branch type |
| `enforcement.yaml` | Tool execution policy | Declares allowed base branches for that branch type |
| `workphases.yaml` | Phase and subphase vocabulary | Must contain every phase or subphase referenced by the contract |

These files do not necessarily duplicate the same truth. The gap is that workflow identity and
the relationships between these lenses are repeated as strings without one documented
extension contract or complete startup cross-validation.

### Documentation Findings

| Document | What it explains | Missing information |
|---|---|---|
| `docs/manuals/architecture.md` | Supported workflows and phase sequences | No procedure for adding a workflow |
| `docs/reference/tools/project.md` | Metadata in `workflows.yaml`; lifecycle in `contracts.yaml` | No issue-type, branch-type, or enforcement dependencies |
| `docs/reference/mcp_vision_reference.md` | Responsibilities of individual config files | Claims adding a workflow is an unspecified YAML-only change |
| `docs/reference/config-loading-architecture.md` | Config loading, validation, and consumers | No workflow-extension checklist |
| `docs/manuals/architectural_diagrams/10_config_consumers.md` | Consumer matrix | Contains stale paths and incomplete current relationships |

There is no authoritative "Adding a Workflow Type" section that covers the complete dependency
chain.

### Validation Findings

Startup validation currently verifies important local relationships, including contract workflow
names against the workflow catalog and contract phase names against `workphases.yaml`.
The investigation did not find complete validation for all workflow-type relationships, such as:

- every issue-to-workflow mapping resolving to an executable contract;
- every dedicated workflow branch type existing in `git.yaml`;
- every dedicated workflow branch type having an explicit enforcement rule;
- every executable catalog workflow having the intended contract coverage.

A missing enforcement rule currently fails open for branch-base policy, which makes accidental
omissions harder to detect.

---

## Constraints for Follow-Up

The follow-up should prefer configuration and documentation changes. Python changes should be
avoided unless a narrowly scoped validation gap cannot be solved declaratively.

The dedicated issue must preserve these boundaries:

- Do not make `chore` a disguised `feature` or `hotfix` workflow.
- Do not impose RED/GREEN/REFACTOR on maintenance work that changes no executable behavior.
- Do not weaken TDD requirements for chores that do change executable behavior.
- Keep Git, issue classification, lifecycle contracts, and enforcement as separate
  responsibilities.
- Avoid introducing another manually synchronized workflow-name list.
- Treat configuration reload/restart behavior and client-side schema caching as acceptance
  concerns.
- Update documentation and tests together with the configuration model.

---

## Open Decisions

The dedicated issue must research and obtain approval for these decisions before implementation:

| Decision | Questions to resolve |
|---|---|
| Chore lifecycle | Which phases are mandatory, optional, or intentionally absent? |
| Implementation semantics | How does the workflow distinguish behavioral code changes from configuration, metadata, documentation, or repository maintenance? |
| Branch relationship | Must every workflow have a same-named branch type, or should the mapping be explicit? |
| Catalog authority | Is `workflows.yaml` the authoritative workflow-identity catalog, or is a more explicit registry needed? |
| Cross-validation | Which missing relationships must fail at startup? |
| Enforcement | Which base branches may create chore branches, and should missing policies fail closed? |
| Documentation | Where should the authoritative workflow-extension procedure live? |
| Compatibility | How are existing `type:chore` issues that currently map to `feature` handled? |

No option is approved by this findings report.

---

## Deferred Work

**Deferred reason:** formalizing the chore workflow changes lifecycle configuration, branch
semantics, validation behavior, tests, and documentation. That scope is materially different
from issue #444, whose accepted purpose is reconciling generated workspace assets.

**Deferred owner:** `@co`, after merge of the issue #444 branch.

**Expected follow-up form:** a dedicated issue, likely under the workflow or MCP-server scope,
with research and an explicit strategy decision before implementation.

### Candidate Follow-Up Scope

The follow-up issue should at minimum:

1. Confirm the workflow-identity authority and dependency model.
2. Define the approved chore lifecycle and behavioral-code/TDD boundary.
3. Add or align the necessary configuration entries.
4. Add targeted cross-validation only where configuration alone cannot prevent drift.
5. Add config, schema, branch, issue, initialization, transition, and enforcement tests.
6. Add an authoritative "Adding a Workflow Type" procedure.
7. Update stale workflow lists and consumer documentation.
8. Verify restart and client schema-refresh behavior.

---

## Co Follow-Up

### Issue #444 → Co Deferred-Work Hand-over

**Directive:** After the issue #444 branch is merged, create and coordinate a dedicated issue
for first-class chore workflow and branch support using this report as discovery evidence.

**Source issue:** #444.

**Trigger:** Merge of `refactor/444-review-reconcile-generated-workspace-assets`.

**Recommended next sub-role:** `@co triager`, followed by `@imp researcher` for the new issue.

**Required issue framing:**
- problem: workflow identity is distributed across configuration lenses without a complete
  extension contract;
- user outcome: create and initialize a dedicated chore branch/workflow predictably;
- implementation preference: configuration/documentation first, Python only for narrow
  cross-validation gaps;
- strategy gate: approve lifecycle, mapping, enforcement, compatibility, and validation
  behavior before design or implementation.

**Out of scope for #444:** all chore-workflow configuration and runtime changes.

---

## Related Documentation

- [Architecture](../../manuals/architecture.md)
- [Configuration Loading Architecture](../../reference/config-loading-architecture.md)
- [MCP Vision Reference](../../reference/mcp_vision_reference.md)
- [Project Tools](../../reference/tools/project.md)
- [Configuration Consumers](../../manuals/architectural_diagrams/10_config_consumers.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-18 | Agent | Record chore-workflow findings and deferred coordination hand-off |
