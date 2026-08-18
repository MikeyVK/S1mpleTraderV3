<!-- docs\development\issue446\research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-18T11:24Z updated=2026-08-18T11:40Z -->
# Issue #446 Research: Chore Workflow and Contract Maintainability

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-18

---

## Purpose

Capture the reproducible evidence, approved boundaries, implementation inventory, and verification baseline for adding `chore` as the lightest first-class workflow.

## Scope

**In Scope:**

- Remove the legacy `fix` branch type from current configuration, tests, prompts, and current documentation.
- Remove `custom` from current workflow suggestions and current documentation.
- Add `chore` as a first-class issue, branch, enforcement, workflow, and contract identity.
- Use the lightweight phase sequence `implementation → validation → documentation → ready`.
- Keep chore implementation non-cycle-based.
- Record a reproducible assessment of YAML anchors and aliases in `contracts.yaml`.
- Add one workflow-extension guide that describes the complete addition contract across configuration, runtime-derived schemas, tests, prompts, agent-instruction sources, and documentation.

**Out of Scope:**

- Cross-config startup validation or a new alignment service.
- A custom workflow implementation or arbitrary phase composition.
- Behavioral production-code changes.
- Migration or renaming of existing or historical `fix/*` branches.
- Rewriting archived research or historical documentation to reflect the new present state.
- YAML anchors, aliases, merge keys, instruction composition, or broad contract normalization.
- Unrelated workflow, phase, gate, or role redesign.

## Prerequisites

Read these first:

1. [Issue #444 chore workflow findings][issue444-findings]
2. [Architecture Principles][architecture-principles]
3. [Documentation Standard][documentation-standard]
4. `.pgmcp/config/issues.yaml`
5. `.pgmcp/config/git.yaml`
6. `.pgmcp/config/enforcement.yaml`
7. `.pgmcp/config/workflows.yaml`
8. `.pgmcp/config/contracts.yaml`
9. `.github/prompts/start-issue.prompt.md`

---

## Problem Statement

Issue creation already accepts `chore`, but the issue type maps to the full `feature` workflow and no `chore` branch type exists. Daily lifecycle bootstrap assumes that the selected start type can be used both as `create_branch.branch_type` and `initialize_project.workflow_name`, so chore work cannot use a coherent dedicated route.

The same surfaces retain two misleading concepts:

- `fix` remains a valid branch type without a corresponding issue type or workflow.
- `custom` remains suggested in current documentation and descriptive surfaces although the contracts-driven runtime schema does not offer it as a configured workflow.

Adding chore also increases pressure on the already large `contracts.yaml`. The maintainability value and risk of YAML anchors or aliases therefore had to be measured rather than assumed.

## Research Goals

- Explain the operational distinction and relationship between issue types, labels, workflows, branch types, enforcement, and daily issue startup.
- Identify the smallest coherent first-class chore lifecycle.
- Determine whether `fix` and `custom` represent supported present-day concepts.
- Identify all current surfaces that must agree after the change.
- Measure the source of `contracts.yaml` size and exact repetition.
- Determine whether native YAML anchors or aliases produce meaningful maintainability gains.
- Define one extension guide so a future workflow addition does not require a new repository-wide rediscovery exercise.

---

## Background

Issue #444 established the configuration lenses involved in workflow support but intentionally deferred chore workflow implementation. Issue #446 follows that finding.

The relevant concepts own different truths:

| Concept | Owned truth | Current source |
|---|---|---|
| Issue type | Work classification selected at issue creation | `issues.yaml` |
| GitHub type label | Reporting and issue taxonomy | `issues.yaml` mapping to `labels.yaml` |
| Workflow catalog | Workflow identity and execution metadata | `workflows.yaml` |
| Workflow contract | Ordered phases, instructions, gates, cycle semantics, and readiness | `contracts.yaml` |
| Branch type | Valid Git prefix and issue-number extraction namespace | `git.yaml` |
| Branch policy | Allowed bases for branch creation | `enforcement.yaml` |
| Phase vocabulary | Globally known phase metadata and commit hints | `workphases.yaml` |

These truths need not be globally identical. For example, hotfix is intentionally labelled `type:bug` while using a dedicated hotfix workflow and branch route. However, the standard daily start prompt currently uses one `WORKFLOW_TYPE` value for both branch creation and project initialization. A first-class standard route therefore requires a matching branch and workflow identity.

---

## Findings

### 1. Current operational mapping

| Issue input | Type label | Workflow | Standard branch type | Assessment |
|---|---|---|---|---|
| `feature` | `type:feature` | `feature` | `feature` | Coherent |
| `bug` | `type:bug` | `bug` | `bug` | Coherent |
| `hotfix` | `type:bug` | `hotfix` | `hotfix` | Intentional label divergence |
| `refactor` | `type:refactor` | `refactor` | `refactor` | Coherent |
| `docs` | `type:docs` | `docs` | `docs` | Coherent |
| `chore` | `type:chore` | `feature` | Missing | Temporary fallback, not first-class |
| `epic` | `type:epic` | `epic` | `epic` | Coherent |
| None | None | None | `fix` | Legacy branch-only concept |

`CreateIssueTool` reads the label and workflow from `IssueConfig`, then reads the first phase from `ContractsConfig` to assemble the initial `phase:*` label. `CreateBranchTool` derives its accepted enum from `GitConfig.branch_types`. `InitializeProjectTool` derives its accepted enum from the configured contract workflows.

The daily `start-issue` sequence then calls:

```text
create_branch(branch_type=WORKFLOW_TYPE, ...)
initialize_project(workflow_name=WORKFLOW_TYPE, ...)
```

Chore must consequently exist in both branch and workflow configuration for the supported standard route.

### 2. Rationale for the remaining divergences

The hotfix label divergence is valid: hotfix work is classified as a bug for issue reporting while using a shorter, urgent execution route.

The chore-to-feature mapping is not a desirable domain distinction. It is a compatibility fallback created because chore classification existed before a dedicated chore lifecycle.

No current authoritative rationale was found for retaining `fix` alongside `bug`. Repository history preserved in archived issue #55 research shows that `fix` was part of the original Git branch convention before the present issue/workflow taxonomy. Current configuration subsequently gained `bug` without removing `fix`. Because `fix` has no issue type or workflow and the supported start prompt does not route to it, it is legacy compatibility rather than a current first-class workflow identity.

### 3. Custom is not a working universal fallback

Current documentation and descriptive strings mention `custom`, and `InitializeProjectInput` retains a `custom_phases` field. The active runtime path nevertheless requires `workflow_name` to exist in `ContractsConfig.workflows`, while the dynamically exposed schema is populated from those configured workflow keys. No custom workflow exists there.

More importantly, strict transitions validate the fixed sequence in `contracts.yaml`, not the branch-local `required_phases` override. A genuinely arbitrary custom workflow would therefore require lifecycle code and contract-resolution changes. It is not a config-only fallback.

The approved decision is not to design or implement custom. Current suggestions that present it as supported are removed. Chore becomes the lightest supported normal workflow. Exceptional movement remains possible through explicitly approved force transitions, including movement to a phase outside the configured strict workflow sequence.

### 4. Chore is the lightest first-class workflow

Approved phase order:

```text
implementation → validation → documentation → ready
```

Contract characteristics:

- `implementation.cycle_based: false`;
- no planning deliverables or TDD-cycle requirement;
- no research or design phase;
- proportionate validation remains explicit;
- documentation remains available for affected current references;
- ready remains the terminal PR-readiness phase;
- phase instructions are compact and chore-specific rather than copied wholesale from feature;
- no new workphase vocabulary is required.

This makes chore lighter than hotfix in process overhead because it does not impose cycle semantics, while retaining the shared validation, documentation, and readiness boundaries.

### 5. No cross-config validation is added

Research considered extending `ConfigValidator` to validate issue, workflow, branch, and enforcement alignment. That would require injecting additional configuration objects into startup validation and expanding test fixtures and bootstrap composition.

The approved scope rejects that change. Issue #446 corrects the checked-in configuration mechanically and documents the complete extension contract. No new validator, mapping field, manager behavior, or startup dependency is introduced.

### 6. Reproducible contracts.yaml size measurement

Measurement was performed against the issue #446 research branch before chore was added.

| Metric | Observed value |
|---|---:|
| Total file length | 3,482 lines |
| File size | 216,157 bytes |
| Workflow-phase instruction blocks | 33 |
| Lines inside `phase_instructions` blocks | approximately 2,604 |
| Characters inside `phase_instructions` blocks | approximately 175,436 |
| Exact duplicate `phase_instructions` groups | 0 |
| Exact duplicate handover groups | 1 |
| Members of exact handover group | feature/ready, bug/ready, hotfix/ready, refactor/ready |
| Potential saving from that handover alias | approximately 66 lines |

The measurement can be reproduced by:

1. Counting total lines and bytes in `.pgmcp/config/contracts.yaml`.
2. Scanning each `phase_instructions: |` scalar until the next sibling key.
3. Hashing the complete normalized scalar contents and grouping identical hashes.
4. Repeating the scan for `handover_template: |` scalars.

The large file is primarily caused by long phase instructions. The repetition is mostly semantic or near-identical, not byte-identical.

### 7. YAML anchors and aliases are technically supported

`ConfigLoader` uses `yaml.safe_load`. Native YAML anchors and aliases therefore resolve before Pydantic validates the resulting object. Reusing an exact scalar or mapping would not require production-code changes.

However, native YAML cannot concatenate scalar fragments. It can alias an entire instruction string, but cannot express a common instruction body plus a workflow-specific suffix while still producing the single string required by `PhaseInstructionsSpec.phase_instructions`.

Mapping merge keys can combine mappings but do not solve text composition. Introducing a separate template catalog at the contracts root would also fail the current `extra="forbid"` root schema unless schema or loader behavior changed.

### 8. Anchors and aliases are explicitly rejected

The decision is based on current evidence, not a general prohibition against YAML features:

1. No exact duplicate `phase_instructions` blocks currently exist.
2. The only exact repeated handover group yields a small saving relative to the 3,482-line file.
3. Meaningful savings would require first rewriting near-identical instructions into identical generic contracts.
4. That rewrite would be a behavioral and governance decision, not a mechanical deduplication.
5. Anchoring a canonical block under one workflow makes other workflows depend on text physically owned elsewhere.
6. A change to an anchor affects all consumers without producing local diffs at those consumers.
7. Nested merge keys and overrides reduce source length while increasing review indirection.
8. YAML aliases cannot parameterize workflow names, deliverables, boundaries, or role-specific differences.
9. Adding chore does not justify broad normalization of existing workflow behavior.

Therefore issue #446 adds no anchors, aliases, merge keys, loader composition, or schema-level instruction templates. Future research may reconsider the decision only after remeasuring exact duplication and explicitly deciding that multiple workflows should share one semantic contract. It must not infer maintainability benefit from visual similarity alone.

### 9. Implementation inventory

No behavioral Python change is required for chore. Runtime schemas and managers already consume the relevant configuration dynamically.

#### Configuration

| File | Required change |
|---|---|
| `.pgmcp/config/issues.yaml` | Map `chore` to workflow `chore` |
| `.pgmcp/config/git.yaml` | Remove `fix`; add `chore` |
| `.pgmcp/config/enforcement.yaml` | Remove `fix` branch policy; add `chore` policy |
| `.pgmcp/config/workflows.yaml` | Add chore catalog metadata |
| `.pgmcp/config/contracts.yaml` | Add compact non-cycle chore contract |
| `.pgmcp/config/workphases.yaml` | No semantic change; existing phases suffice |

#### Current operational and instruction surfaces

- Add chore and remove custom/fix suggestions from `.github/prompts/start-issue.prompt.md`.
- Update the authoritative agent-instruction source or sources that enumerate workflow types, then regenerate or synchronize derived instruction files using the documented SSOT process.
- Update any user-facing tool description text that statically suggests `custom`; this is descriptive metadata only and must not change behavior.
- Do not edit generated consumers independently of their authoritative source.

#### Tests

Tests must cover configuration-driven public behavior rather than introduce hardcoded production dispatch:

- `create_branch` schema accepts chore and rejects removed fix;
- Git config fixtures match the new branch set;
- branch enforcement contains chore and no fix;
- issue config maps chore to chore;
- workflow and contracts loaders expose chore;
- project initialization accepts chore and starts in implementation;
- chore phase order is exactly implementation, validation, documentation, ready;
- chore implementation is not cycle-based;
- static test fixtures and expected enums no longer advertise fix or custom;
- existing feature, bug, hotfix, refactor, docs, and epic behavior remains unchanged.

#### Documentation

Current documentation is updated to describe only the new present state. Archived documents remain historical evidence and are not rewritten. Documentation must not add a migration diary or historical trace to user-facing reference pages.

### 10. Workflow-extension documentation contract

A single current reference guide must be created for future workflow additions. Its purpose is to replace repository-wide rediscovery with a deterministic extension procedure.

The guide must cover:

1. **Classify the identity**
   - Decide whether the addition is an issue type, workflow, branch type, or some combination.
   - Record any intentional divergences in label, workflow, or branch identity.

2. **Declare issue behavior**
   - Add or update `issues.yaml`.
   - Confirm the label exists in `labels.yaml`.
   - Confirm the first workflow phase produces the intended initial phase label.

3. **Declare workflow metadata**
   - Add the workflow to `workflows.yaml`.
   - Choose execution mode and concise description.

4. **Declare the executable contract**
   - Add ordered phases to `contracts.yaml`.
   - Reuse existing phase vocabulary where possible.
   - Define cycle behavior, subphases, commit mappings, gates, instructions, and handover only where applicable.
   - Keep `ready` terminal under the current merge policy.
   - Prefer compact purpose-specific instructions over copying another workflow wholesale.

5. **Declare Git support when applicable**
   - Add the branch prefix to `git.yaml`.
   - Add an explicit allowed-base policy to `enforcement.yaml`.
   - Do not assume every workflow requires a branch type or every branch type requires a workflow; explain intentional exceptions.

6. **Update lifecycle entry**
   - Update current start prompts and supported-workflow enumerations.
   - Update authoritative agent-instruction sources and synchronize generated consumers.
   - Verify role ownership and epic/non-epic handoff behavior.

7. **Verify runtime-derived surfaces**
   - Confirm `create_branch` input schema derives the branch enum from `git.yaml`.
   - Confirm `initialize_project` input schema derives the workflow enum from `contracts.yaml`.
   - Confirm issue creation resolves the workflow's first phase.

8. **Update tests**
   - Update shared fixtures and enum expectations.
   - Add loader/schema, initialization, transition-order, cycle-mode, and enforcement coverage proportional to the workflow.
   - Avoid production-code changes unless a required behavior is demonstrably not config-driven.

9. **Update current documentation**
   - Update workflow tables and Git/project tool references.
   - Keep current reference pages state-based, not historical.
   - Leave archives unchanged.

10. **Run verification**
    - Validate YAML loading and Pydantic parsing.
    - Run the focused config, tool-schema, project initialization, transition, and enforcement tests.
    - Run branch-scoped quality gates before lifecycle transition or PR submission.

This guide becomes the documented extension contract, not a new source of workflow values. The YAML configuration remains authoritative for actual identities, phase order, and policies.

### 11. Compatibility and migration boundaries

| Boundary | Approved strategy |
|---|---|
| Existing historical `fix/*` branches | No migration or rename; removal applies to new branch creation after merge |
| Existing persisted branch state | No schema migration |
| Chore issues created before #446 | No automatic relabelling or workflow-state conversion |
| Current issue type `chore` | Clean switch from feature workflow mapping to chore workflow |
| Tool schemas | Change dynamically with configuration |
| Fix/custom documentation | Remove from current docs; leave archives intact |
| Agent instructions | Update authoritative sources and synchronize derived outputs |
| Contracts aliases | Do not introduce |
| Cross-config validation | Deferred indefinitely; not part of #446 |

---

## Approved Strategy

Implement a config-driven clean break for new work:

1. Remove `fix` from current branch configuration, enforcement, schemas derived from configuration, fixtures, prompts, and current documentation.
2. Remove `custom` from current supported-workflow suggestions and descriptive surfaces; do not implement it.
3. Add `chore` as a first-class issue, branch, enforcement, workflow, and contract identity.
4. Use `implementation → validation → documentation → ready` with non-cycle-based implementation.
5. Make no behavioral Python changes and add no cross-config validator. A narrowly targeted edit to user-facing descriptive metadata is permitted only when necessary to stop advertising custom.
6. Add no YAML anchors, aliases, merge keys, or instruction-template mechanism.
7. Keep chore instructions compact and purpose-specific.
8. Add a single workflow-extension reference guide covering the complete addition contract.
9. Update current documentation to the new state without adding a historical migration narrative.
10. Preserve archived documentation and existing historical branches unchanged.

---

## Expected Results

- `create_branch(branch_type="chore")` is accepted.
- `create_branch(branch_type="fix")` is no longer offered or accepted for new branches.
- `initialize_project(workflow_name="chore")` is accepted.
- Chore initializes in `implementation`.
- Strict chore transitions follow implementation, validation, documentation, ready.
- Chore implementation is not cycle-based.
- Issue creation maps chore to the chore workflow and initial implementation phase.
- Chore branch creation has an explicit allowed-base policy.
- Current prompts, authoritative agent-instruction sources, generated consumers, tool references, and tests agree.
- Current supported-workflow descriptions no longer advertise custom.
- Existing workflows retain their current phases, gates, and behavior.
- `contracts.yaml` remains free of anchors and aliases.
- The workflow-extension guide makes future additions deterministic without duplicating workflow values as a second source of truth.
- Focused tests and branch-scoped quality gates pass.

## Open Questions

None. Strategy, compatibility boundaries, and expected results are approved.

## Related Documentation

- **[Issue #444 chore workflow findings][issue444-findings]**
- **[Configuration loading architecture][config-loading]**
- **[Git tools reference][git-tools]**
- **[Project tools reference][project-tools]**
- **[Issue #271 contracts SSOT research][issue271-research]**

<!-- Link definitions -->

[issue444-findings]: ../issue444/chore-workflow-findings.md
[architecture-principles]: ../../coding_standards/ARCHITECTURE_PRINCIPLES.md
[documentation-standard]: ../../coding_standards/DOCUMENTATION_STANDARD.md
[config-loading]: ../../reference/config-loading-architecture.md
[git-tools]: ../../reference/tools/git.md
[project-tools]: ../../reference/tools/project.md
[issue271-research]: ../archive/issue271/research.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-18 | Agent | Approved research baseline for chore workflow, fix/custom cleanup, contracts alias decision, and workflow-extension documentation |
