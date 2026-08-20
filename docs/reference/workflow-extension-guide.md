<!-- docs\reference\workflow-extension-guide.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-18T15:15Z updated=2026-08-18T15:18Z -->
# Adding a First-Class Workflow

**Status:** DEFINITIVE  
**Version:** 1.0  
**Last Updated:** 2026-08-18

---

## Purpose

Provide a deterministic extension procedure for adding or changing a workflow
without rediscovering every configuration and runtime dependency.

The YAML configuration remains authoritative for workflow identity and
behavior. This guide explains how the separate configuration lenses connect to
issue creation, branch creation, project initialization, transitions, tests,
agent instructions, and current documentation.

## Scope

**In Scope:**

- Adding a configured first-class workflow.
- Adding an issue type or branch type that participates in the standard
  lifecycle.
- Extending current prompts, agent instructions, tests, and documentation to
  match the configured behavior.

**Out of Scope:**

- Arbitrary user-defined workflows.
- New phase-engine behavior.
- Cross-config startup validation.
- Changes to archived documentation.

## Authority Model

A workflow is a composition of related truths, not one duplicated registry.

| Concern | Authoritative source | Responsibility |
|---|---|---|
| Issue type | `.pgmcp/config/issues.yaml` | Issue input, workflow mapping, and type label |
| Label definition | `.pgmcp/config/labels.yaml` | Valid label metadata |
| Workflow metadata | `.pgmcp/config/workflows.yaml` | Name, description, and execution mode |
| Executable workflow contract | `.pgmcp/config/contracts.yaml` | Ordered phases, gates, cycle behavior, instructions, and handovers |
| Branch type | `.pgmcp/config/git.yaml` | Branch prefix and issue-number extraction namespace |
| Allowed base branches | `.pgmcp/config/enforcement.yaml` | Branch creation policy |
| Phase vocabulary | `.pgmcp/config/workphases.yaml` | Globally known phase metadata |
| Agent source assets | `docs/agents/<host>/` | Distributable host-specific instructions |
| Active lifecycle entry | Host workflow or prompt file | Daily start sequence |

These sets may intentionally differ. For example, an issue type may share a
reporting label with another type. Record every intentional divergence; do not
assume all names must be globally identical.

The supported standard lifecycle passes one workflow token to both
`create_branch(branch_type=...)` and
`initialize_project(workflow_name=...)`. A normal first-class route therefore
needs both branch and workflow support unless the lifecycle entry explicitly
documents a different mapping.

## Runtime Consumption

| Operation | Configuration consumed |
|---|---|
| `create_issue` | Issue mapping, label metadata, and the contract's first phase |
| `create_branch` | Branch types and enforcement policy |
| `initialize_project` | Configured contracts and their ordered phases |
| `transition_phase` | The active workflow contract |
| `get_work_context` | Branch state plus the active phase contract |
| Tool input schemas | Runtime enum injection from the relevant config |

The optional `custom_phases` initialization field does not create an
unconfigured workflow. The selected `workflow_name` still has to exist in the
configured contracts, and strict transitions continue to follow the configured
workflow contract.

## Extension Procedure

### 1. Classify the Identity

Decide which identities are actually required:

- issue type;
- workflow;
- branch type;
- label;
- new phase vocabulary.

Record intentional differences between issue, label, workflow, and branch
identities before editing configuration.

### 2. Add Issue Behavior

When the workflow has an issue type:

1. Add or update the entry in `issues.yaml`.
2. Point it to the intended configured workflow.
3. Reference an existing label from `labels.yaml`, or add the label there.
4. Confirm that the workflow's first contract phase yields the intended initial
   `phase:*` label.

### 3. Add Workflow Metadata

Add the workflow to `workflows.yaml` with a concise description and execution
mode. Do not define phase order there; `contracts.yaml` owns executable phase
membership and ordering.

### 4. Add the Executable Contract

Add the workflow under `contracts.yaml`:

1. Declare the ordered phases.
2. Reuse existing phase vocabulary where possible.
3. Define `cycle_based`, subphases, commit mappings, gates, instructions, and
   handovers only where applicable.
4. Keep `ready` terminal under the current PR policy.
5. Write compact, workflow-specific instructions instead of copying another
   workflow wholesale.

For every phase instruction, verify the semantic contract independently:

- purpose, workflow-specific responsibility, boundaries, and stop conditions;
- authoritative inputs, blast radius, and required outputs;
- first-time-right artifact commands with schema-required `context={...}`;
- conditional document reads selected by phase and affected boundary;
- durable test-code responsibility under the same standards as production code;
- proportional tests and gates at the phase that owns them, with fresh evidence reused;
- bounded, harness-agnostic delegation;
- objective review prompts that treat caller claims and hand-overs as non-binding;
- delegated preflight as findings-only and independent QA as the sole GO/NOGO authority;
- exact canonical hand-over headings: `### <Workflow> / <Phase> Hand-over`,
  then `#### Scope`, `#### Deliverables`, `#### Evidence`, `#### Open Work`,
  and `#### Review Request`.

`phase_instructions` are returned by `get_work_context`; they must not instruct the
agent to call `get_work_context` again. Keep the Ready instruction identical and
workflow-neutral: consume the latest authoritative verification evidence for the
selected workflow without assuming a Validation phase, a universal full-suite rerun,
or a duplicate human merge-approval check.

Do not introduce YAML anchors, aliases, merge keys, or instruction composition
as a routine extension step. Those mechanisms require a separate,
evidence-backed decision that the consumers should share identical semantics;
visual similarity alone is insufficient.

### 5. Add Git Support When Applicable

For a workflow that uses the standard branch lifecycle:

1. Add its branch prefix to `git.yaml`.
2. Add an explicit base-branch policy to `enforcement.yaml`.
3. Confirm issue-number extraction accepts the new prefix.
4. Do not change conventional commit types merely because a branch type was
   added; they are a separate taxonomy.

Not every workflow must have a branch type and not every branch type must have
a workflow. Explain intentional exceptions in the relevant current reference.

### 6. Update Lifecycle Entry and Agent Instructions

Update current start workflows or prompts that enumerate supported workflow
types.

Edit authoritative agent sources first:

| Host | Authoritative source | Derived or active consumer |
|---|---|---|
| VS Code/Copilot | `docs/agents/vscode/copilot/` | `AGENTS.md` and applicable `.github/` files |
| Codex | `docs/agents/codex/` | `.agents/` |
| Antigravity | `docs/agents/antigravity/` | Active Antigravity rules and workflows |

Synchronize tracked consumers after the source edit and verify that corresponding
files are byte-equivalent where the host layout is a direct copy. Do not edit a
derived consumer first. Local MCP connection settings, credentials, runtime
state, and absolute paths are never part of the agent-source SSOT.

See [Release Assets Procedure][release-assets] for packaging and host deployment
boundaries.

### 7. Verify Runtime-Derived Surfaces

Before changing Python, prove whether the existing config-driven paths already
provide the required behavior:

- `create_branch` input schema exposes the new branch type;
- `initialize_project` input schema exposes the configured workflow;
- issue creation resolves the workflow and its first phase;
- project initialization persists the expected phase order;
- strict transitions follow the new contract;
- cycle behavior matches the contract;
- enforcement accepts only the declared bases.

Production code should change only when one of these required behaviors is
demonstrably not configuration-driven. Do not add hardcoded workflow dispatch.

Restart the MCP server after changing startup-loaded configuration before using
live tool behavior as evidence.

### 8. Update Tests

Use configuration-driven assertions and shared fixtures. Cover, as applicable:

- issue-to-workflow and label mapping;
- branch enum acceptance and removed values;
- workflow and contract loading;
- initialization and initial phase;
- exact transition order;
- cycle or non-cycle behavior;
- branch enforcement;
- current prompt and agent-source enumerations;
- unchanged behavior for existing workflows.

Run focused tests first. Run branch- or workspace-wide verification at the phase
that owns it for the selected workflow. Ready reuses fresh authoritative evidence and
reruns only checks invalidated by later changes. Inspect cached structured results for
every MCP-run test or quality command.

### 9. Update Current Documentation

Update current workflow tables, Git and project tool references, lifecycle
examples, prompts, agent sources, and navigation.

Describe the resulting present state. Do not add a migration diary to reference
pages and do not rewrite archived research or historical issue artifacts merely
to make them resemble the current configuration.

### 10. Final Alignment Check

Confirm these relationships explicitly:

| Check | Expected result |
|---|---|
| Issue mapping | References a configured workflow and valid label |
| First phase | Matches the initial phase label and initialization result |
| Standard lifecycle | Branch and workflow tokens are both accepted |
| Phase order | Comes only from `contracts.yaml` |
| Enforcement | Contains an explicit policy for a new branch type |
| Agent instructions | Sources and tracked consumers agree |
| Documentation | Current tables and examples match configuration |
| Verification | Focused and workflow-owned broad test/gate evidence is current; Ready reuses it unless invalidated |
| Deferred work | Listed explicitly for ready-phase PR handover |

## Related Documentation

- [Project and Phase Management Tools][project-tools]
- [Git Tools][git-tools]
- [GitHub Tools][github-tools]
- [Configuration Loading Architecture][config-loading]
- [Release Assets Procedure][release-assets]
- [Agent Instructions Model][agent-model]

[project-tools]: tools/project.md
[git-tools]: tools/git.md
[github-tools]: tools/github.md
[config-loading]: config-loading-architecture.md
[release-assets]: release-assets-procedure.md
[agent-model]: copilot-agent-instructions-model.md

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-18 | Agent | Initial deterministic workflow-extension procedure |
