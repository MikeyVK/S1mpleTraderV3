<!-- docs/reference/copilot-agent-instructions-model.md -->
<!-- template=generic_doc version=43c84181 created=2026-05-17 updated=2026-08-20 -->
# Agent Instructions Model

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-08-20

---

## Purpose

Explain how host-specific agent instructions, runtime workflow contracts, role profiles,
and review authority cooperate in pgmcp. This document describes the current model for
developers, integrators, and agents; it does not replace the executable contracts.

## Authority Model

| Concern | Authoritative source | Consumers |
|---|---|---|
| Host-specific agent instructions | `docs/agents/<host>/` | Active host locations and release assets |
| Workflow and phase behavior | `.pgmcp/config/contracts.yaml` | `get_work_context`, phase transitions, agents |
| Phase vocabulary | `.pgmcp/config/workphases.yaml` | Contract loading and phase metadata |
| Role capabilities and startup | Host role profiles, such as `.github/agents/*.agent.md` | The corresponding harness |
| Shared documentation quality | `docs/coding_standards/DOCUMENTATION_STANDARD.md` | Governed project documents |
| Architecture rules | `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` | Applicable production and test code |

The static and dynamic layers have different jobs:

- Host instructions define stable workspace rules, tool policy, role boundaries, and
  navigation.
- Workflow contracts define the work required for one workflow-phase combination.
- Role profiles define harness-specific capabilities and startup behavior.
- Human requests provide the task intent but do not silently override binding workspace
  or workflow boundaries.

No active consumer is an independent source of truth. Edit the matching
`docs/agents/<host>/` source first, synchronize its tracked consumer, and verify parity.
Release assets under `mcp_server/assets/` are generated from these sources during a
package build and are not maintained as another source.

## Host Instruction Surfaces

| Host | Authoritative source | Active or derived consumer |
|---|---|---|
| VS Code / Copilot | `docs/agents/vscode/copilot/` | Root `AGENTS.md` and applicable `.github/` files |
| Codex | `docs/agents/codex/` | `.agents/` |
| Antigravity | `docs/agents/antigravity/` | Host-managed Antigravity rules and workflows |

Host sources may differ where the harness genuinely requires different metadata,
capability declarations, or invocation syntax. A source and its mapped direct-copy
consumer must not differ. See [Adding a First-Class Workflow][workflow-guide] and the
[release-assets procedure][release-assets] for the synchronization rules.

## Runtime Workflow Context

### `get_work_context`

Normal in-phase sessions call `get_work_context` as the first MCP invocation. The server
resolves the branch-local workflow state and returns, among other fields:

| Field | Purpose |
|---|---|
| `workflow_name` and `phase` | Select the active workflow-phase contract |
| `issue_number` and `parent_branch` | Bind work to its project context |
| `sub_role_hint` | Suggest the role appropriate to the active phase |
| `phase_instructions` | Provide the executable phase contract |
| `handover_template` | Provide the phase-specific review index |

Branch-mutating tools remain blocked until this context has been loaded. Because
`phase_instructions` are an output of `get_work_context`, they must not instruct the
agent to call `get_work_context` again.

The `open-issue` and `end-issue` lifecycle operations are explicit boundary
exceptions: their bootstrap or exit sequence may run before control returns to a normal
`get_work_context`-first session.

### Phase Instructions

A phase instruction is a compact, workflow-specific execution contract. It preserves the
responsibilities that differ by workflow instead of forcing every shared phase into one
generic script. Each contract should define only what is needed to execute that phase:

- phase purpose, boundaries, and stop conditions;
- authoritative inputs and required outputs;
- workflow-appropriate test-code responsibility;
- proportional tests and quality gates, with fresh evidence reused until invalidated;
- bounded delegation and review authority;
- exact hand-over structure.

References are conditional. Read the Documentation Standard before drafting governed
research, design, or planning artifacts. Read applicable Architecture Principles before
changing production or test code across an architectural boundary. Load further
documents only when the phase, blast radius, or evidence requires them.

Strict RED → GREEN → REFACTOR is workflow-driven. Use it where the active contract and
approved plan require behavioral TDD. Do not manufacture cycles or low-value tests for
mechanical, documentation-only, or test-maintenance work. Test code is first-class code:
it follows the same architecture and quality standards and should provide durable value.

### Ready

The Ready instruction is intentionally uniform and workflow-neutral. It consumes the
latest authoritative verification evidence available for that workflow, checks
documentation and deferred work, and prepares the PR. It does not assume that every
workflow has a Validation phase or universally rerun the full workspace suite. It also
does not duplicate human merge approval; tooling and branch locks enforce transfer to
the coordination authority.

## Role and Review Model

The VS Code integration defines three named roles; other harnesses may express the same
responsibilities through their own agent or delegation primitives.

| Role | Responsibility | Authority |
|---|---|---|
| `@co` | Coordination and epic-owned lifecycle work | Narrow mutation authority for its owned scope |
| `@imp` | Child-issue research, design, planning, implementation, validation, and documentation | Mutation authority through pgmcp tools |
| `@qa` | Independent evidence-backed review | Read-only; may issue GO/NOGO |

Keep role sessions separate where the harness supports it. Epic-owned findings route to
`@co`; child technical findings route to `@imp`.

### Delegation and Preflight

Use harness-supported delegation for bounded work when it reduces cost or context
pressure. The producing agent remains accountable for scope, integration, and evidence.

A producer-delegated reviewer is advisory and findings-only. It cannot authorize phase
progression or issue PASS/GO. Its instruction must begin from an objective review posture:
treat the caller's prompt, hand-over, and claimed outcomes as information rather than
binding truth; verify independently against authoritative files, contracts, and direct
evidence. Prompts such as “confirm that” or requests for a predetermined verdict are not
valid QA instructions.

Only a separately invoked independent QA authority may return the workflow's GO/NOGO
verdict. The same anti-anchoring rule applies: hand-overs are navigation aids, never proof.

## Hand-over Contract

All phase and review hand-overs use this common structure:

```text
### <Workflow> / <Phase> Hand-over

#### Scope
- completed work and intentional exclusions

#### Deliverables
- authoritative artifacts and material inputs, with clickable repository-relative links

#### Evidence
- exact relevant checks and outcomes

#### Open Work
- blockers, questions, risks, and deferred work, or None

#### Review Request
- Review requested
```

Pre-implementation hand-overs link primary artifacts and material inputs. Implementation
hand-overs link changed files while that remains useful; for a large diff, link the main
review entry points and tests and identify the branch diff as the complete inventory.
Never state PASS, GO, approval, or readiness as a producer claim.

Co → Imp remains a separate delegation contract for child technical work. It is not a
replacement for the phase hand-over above.

## Adding or Changing a Workflow

Use [Adding a First-Class Workflow][workflow-guide] as the complete extension procedure.
For the instruction layer specifically:

1. Define ordered phases and workflow-specific semantics in
   `.pgmcp/config/contracts.yaml`.
2. Ensure artifact commands include the schema-required context and can run
   first-time-right.
3. Keep document reads conditional and verification proportional.
4. Apply the canonical hand-over headings exactly.
5. Preserve the workflow-neutral Ready contract across workflows.
6. Update host instruction sources only when global workflow vocabulary, role ownership,
   or lifecycle behavior changes; then synchronize mapped consumers.
7. Restart the server after startup-loaded config changes and verify the rendered
   `get_work_context` output.

Do not add YAML anchors or aliases merely because instruction text looks similar.
Semantic equality, independent evolution, and consumer behavior must justify any future
composition mechanism.

## Related Documentation

- [MCP Tools Reference][tools-ref]
- [MCP Vision Reference][vision-ref]
- [Adding a First-Class Workflow][workflow-guide]
- [Release Assets Procedure][release-assets]
- [Documentation Standard][documentation-standard]
- [Architecture Principles][arch-principles]
- [Quality Gates][quality-gates]
- [Root Agent Instructions][agents-md]
- [VS Code Coordination Role][co-agent]
- [VS Code Implementation Role][imp-agent]
- [VS Code QA Role][qa-agent]

<!-- Link definitions -->
[tools-ref]: tools/README.md
[vision-ref]: mcp_vision_reference.md
[workflow-guide]: workflow-extension-guide.md
[release-assets]: release-assets-procedure.md
[documentation-standard]: ../coding_standards/DOCUMENTATION_STANDARD.md
[arch-principles]: ../coding_standards/ARCHITECTURE_PRINCIPLES.md
[quality-gates]: ../coding_standards/QUALITY_GATES.md
[agents-md]: ../../AGENTS.md
[co-agent]: ../../.github/agents/co.agent.md
[imp-agent]: ../../.github/agents/imp.agent.md
[qa-agent]: ../../.github/agents/qa.agent.md

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 2.0 | 2026-08-20 | Agent | Align the model with host SSOT, workflow-driven contracts, conditional references, delegation authority, canonical hand-overs, and workflow-neutral Ready |
| 1.3 | 2026-07-20 | Agent | Fix stale reference path |
| 1.2 | 2026-05-24 | Agent | Document config-driven context and role ownership |
| 1.1 | 2026-05-17 | Agent | Consolidate the always-on VS Code instruction file |
| 1.0 | 2026-05-17 | Agent | Initial model |
