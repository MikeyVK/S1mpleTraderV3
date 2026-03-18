<!-- docs\development\issue263\design_v2_sub_role_orchestration.md -->
<!-- template=design version=5827e841 created=2026-03-18T14:21Z updated= -->
# Sub-Role Orchestration — Phase-Aware Agent Cooperation Without MCP Coupling

**Status:** DRAFT  
**Version:** 2.0  
**Last Updated:** 2026-03-18

---

## Purpose

Define the evolved orchestration model for VS Code agent cooperation that extends the compact design (v1.0) with phase-aware sub-roles while maintaining zero runtime coupling to the MCP workflow server.

## Scope

**In Scope:**
Sub-role definitions for imp and qa agents across all 6 workflow phases; sub-role-specific output formats; stop hook sub-role detection and enforcement; slash prompt restructuring; argument-hint updates for .agent.md wrappers; cross-chat handover block redesign with neutral language; transition ownership model

**Out of Scope:**
MCP server changes; .st3 schema changes; runtime workflow state coupling; automatic phase detection; tool gating; new agent roles beyond imp and qa

## Prerequisites

Read these first:
1. Existing compact design v1.0 (docs/development/issue263/design.md) implemented and working
2. stop_handover_guard.py with TypedDict-based RoleRequirement already in place
3. Current hook infrastructure (SessionStart, PreCompact, Stop) operational

---

## 1. Context & Requirements

### 1.1. Problem Statement

The current imp_agent.md and qa_agent.md are monolithic — they mix identity, operational instructions, and output format templates into single documents. They provide no phase-specific differentiation: the agent behaves identically during research as during implementation. The imp-to-qa handover format is overly directive, and the qa-to-imp brief uses prescriptive tasking language. The stop hook enforces a single output format regardless of the workflow phase being worked on. These issues create unnecessary friction in multi-phase workflows and violate role sovereignty.

### 1.2. Requirements

**Functional:**
- [ ] Define sub-roles per workflow phase for both @imp (researcher, planner, designer, implementer, validator, documenter) and @qa (plan-reviewer, design-reviewer, verifier, validation-reviewer, doc-reviewer)
- [ ] Sub-role selection is driven by explicit user input via argument-hint, not by MCP server state
- [ ] Each sub-role has a dedicated output format with phase-relevant sections only — no n/a fields
- [ ] Stop hook enforcement is sub-role-aware: only implementer/validator (imp) and verifier/validation-reviewer (qa) require cross-chat handover blocks
- [ ] Cross-chat handover blocks use neutral non-directive language — role doctrine lives in the role guide, not in the prompt
- [ ] Phase transitions are executed by @imp via /transition-phase after explicit user instruction and QA GO
- [ ] Default sub-role when none specified: implementer (imp) / verifier (qa) for backward compatibility

**Non-Functional:**
- [ ] Complete decoupling from MCP server state — no runtime dependency on .st3/state.json or .st3/projects.json
- [ ] Backward compatible — unrecognized or missing sub-role falls back to current strict enforcement
- [ ] Sub-role detection via transcript parsing of first user message — no hidden state
- [ ] Graceful degradation when .st3 is unavailable
- [ ] Each implementation step is independently testable

### 1.3. Constraints

- No runtime dependency on MCP server or .st3 state files
- Must remain backward compatible with current handover enforcement
- Sub-role detection must work purely from transcript text — no hidden state files
- Stop hook must default to strictest enforcement when sub-role is undetectable

---

## 2. Design Principles

### 2.1. Strict Separation of Concerns

The design introduces three conceptually separated layers:

| Layer | Content | Location |
|---|---|---|
| **Identity** | Mission, boundaries, contracts, truthfulness, sub-role definitions | `imp_agent.md` / `qa_agent.md` (workspace root) |
| **Operations** | Output format requirements, startup steps, recovery protocol | `.github/prompts/*.prompt.md` |
| **Enforcement** | Structural validation of agent output per role × sub-role | `scripts/copilot_hooks/stop_handover_guard.py` |

Each layer references the one above it but never duplicates it.

### 2.2. No Workflow Coupling

Phase context comes from explicit user input (sub-role name), not from `.st3/state.json`, `.st3/projects.json`, or any MCP tool call. The system works identically whether the MCP server is running, stopped, or uninstalled.

### 2.3. Safe Defaults

When the sub-role is not specified or not detectable, the system defaults to the strictest enforcement: `implementer` for @imp, `verifier` for @qa. This preserves backward compatibility with all existing handover workflows.

---

## 3. Design Options

### Option A: Universal Format With Contextual Fields

Every sub-role uses the same handover format (Scope, Files, Proof, etc.). Sections not relevant to the current sub-role contain "n/a". The stop hook enforces the same structure for all sub-roles.

**Pros:** Simple, one format to maintain, backward compatible by default.
**Cons:** Agent produces templating noise ("Proof: n/a for planning sub-role"), user must mentally filter irrelevant sections, stop hook cannot differentiate meaningful output.

### Option B: Sub-Role-Specific Formats (Chosen)

Each sub-role has a dedicated output format with only phase-relevant sections. The stop hook knows which markers to expect per sub-role. Only sub-roles that produce code changes require cross-chat handover blocks.

**Pros:** Zero noise per interaction, precise enforcement, enables progressively sharper agent behavior.
**Cons:** More initial definitions to maintain (one TypedDict entry per sub-role in the hook).

---

## 4. Chosen Design

**Decision:** Implement Option B — sub-role-specific output formats per workflow phase with transcript-based sub-role detection in the stop hook, explicit user-driven sub-role selection via argument-hint, strict separation of role identity from operational prompts, and non-directive cross-chat language.

**Rationale:** Option B was chosen because: (1) it eliminates per-interaction friction; (2) the stop hook can enforce precisely the right structure per phase; (3) it enables progressively sharper agent behavior as sub-role definitions mature; (4) the extra maintenance cost is bounded and predictable. Full MCP decoupling was chosen because the MCP server is not yet stable enough to serve as an orchestration dependency.

---

## 5. Sub-Role Definitions

### 5.1. @imp Sub-Roles

The active sub-role is determined by the user's invocation text. If the user does not specify a sub-role, the default is **implementer**.

| Sub-Role | Phase | Focus | Output Type | Hand-Over Required |
|---|---|---|---|---|
| `researcher` | research | Problem analysis, requirements, technical exploration | Research document | No |
| `planner` | planning | Cycle breakdown, deliverables, dependency analysis | Planning sections | No |
| `designer` | design | Interface contracts, data flows, architecture decisions | Design document | No |
| `implementer` | implementation | Code, tests, targeted verification | Code changes + hand-over | **Yes (stop hook enforced)** |
| `validator` | validation | E2E tests, acceptance tests, system integration | Validation tests + report | **Yes (stop hook enforced)** |
| `documenter` | documentation | Reference docs, guides, agent instructions | Documentation files | No |

### 5.2. @qa Sub-Roles

The active sub-role is determined by the user's invocation text. If the user does not specify a sub-role, the default is **verifier**.

| Sub-Role | Phase | Focus | Output Type | Hand-Over Required |
|---|---|---|---|---|
| `plan-reviewer` | planning | Planning coherence, testability, dependencies | Planning review + verdict | No |
| `design-reviewer` | design | Architecture compliance, SOLID, layer boundaries | Design review + verdict | No |
| `verifier` | implementation | Correctness, proof verification, architecture compliance | Verification review + hand-over | **Yes (stop hook enforced)** |
| `validation-reviewer` | validation | Test coverage, critical path assessment | Validation review + verdict | No |
| `doc-reviewer` | documentation | Accuracy, completeness, code-reference correctness | Documentation review + verdict | No |

### 5.3. Core Identity vs Sub-Role

The sub-role defines **focus and output format**, not identity. The core doctrine in each `_agent.md` remains active regardless of sub-role:
- Architecture Contract always applies
- Truthfulness Rules always apply
- Scope Lock always applies
- QA Boundary (for imp) always applies
- Role Boundaries (for qa) always apply

The sub-role narrows what the agent is expected to produce, not what standards it follows.

---

## 6. Sub-Role Output Formats

### 6.1. @imp Formats

#### `researcher`

```
### Research Output

#### Problem Statement
- [core question investigated]

#### Findings
- [finding with source reference]

#### Technical Constraints
- [constraint discovered during research]

#### Open Questions
- [question still to be answered]

#### Recommendation
- [advice for planning phase]
```

**Stop hook markers:** `Problem Statement`, `Findings`, `Open Questions`
**Cross-chat block:** not required

---

#### `planner`

```
### Planning Output

#### Cycle Breakdown
- [cycle: name + scope in one line]

#### Deliverables Per Cycle
- Cycle N: [concrete deliverables]

#### Dependencies
- [dependency between cycles or external factors]

#### Stop-Go Criteria
- [per cycle: exact verification condition]

#### Risks
- [risk + mitigation]
```

**Stop hook markers:** `Cycle Breakdown`, `Deliverables Per Cycle`, `Stop-Go Criteria`
**Cross-chat block:** not required

---

#### `designer`

```
### Design Output

#### Interface Contracts
- [interface/protocol + responsibility]

#### Data Flow
- [from → to, with transformation]

#### Schema Changes
- [model/schema + what changes]

#### Architecture Decisions
- [decision + rationale]

#### Deferred
- [what is deliberately deferred to implementation]
```

**Stop hook markers:** `Interface Contracts`, `Architecture Decisions`
**Cross-chat block:** not required

---

#### `implementer`

```
### Implementation Hand-Over

#### Scope
- [cycle/task executed]
- [deliberately kept out of scope]

#### Files Changed
- [files grouped by role]

#### Deliverables Satisfied
- [which deliverables are now met]

#### Proof
- Tests run: [exact]
- Checks run: [exact]
- Outcomes: [exact]

#### Out-of-Scope
- [not changed, and why]

#### Open Blockers
- [none or specific]

#### Ready-for-QA
- yes / no

### Copy-Paste Prompt For QA Chat

(fenced text block with neutral language — see Section 7)
```

**Stop hook markers:** `Scope`, `Files Changed`, `Proof`, `Ready-for-QA`, plus cross-chat block markers
**Cross-chat block:** **required**

---

#### `validator`

```
### Validation Hand-Over

#### Test Surface
- [E2E/acceptance tests written or executed]

#### Coverage
- [what is covered, what is not]

#### Results
- Tests run: [exact]
- Pass/fail: [exact]
- Regressions: [none or specific]

#### Gaps
- [untested scenarios]

#### Ready-for-QA
- yes / no

### Copy-Paste Prompt For QA Chat

(fenced text block — see Section 7)
```

**Stop hook markers:** `Test Surface`, `Results`, `Ready-for-QA`, plus cross-chat block markers
**Cross-chat block:** **required**

---

#### `documenter`

```
### Documentation Output

#### Documents Changed
- [path + what changed/added]

#### Accuracy Check
- [which code references verified]

#### Gaps
- [missing documentation outside scope]
```

**Stop hook markers:** `Documents Changed`
**Cross-chat block:** not required

---

### 6.2. @qa Formats

#### `plan-reviewer`

```
### Planning Review

#### Findings
1. [finding with severity + reference]

#### Plan Coherence
- Cycles consistent: [yes/no + explanation]
- Deliverables testable: [yes/no + explanation]
- Dependencies realistic: [yes/no + explanation]

#### Verdict
- GO / NOGO / CONDITIONAL GO
```

**Stop hook markers:** `Findings`, `Plan Coherence`, `Verdict`
**Cross-chat block:** not required (optional on NOGO)

---

#### `design-reviewer`

```
### Design Review

#### Findings
1. [finding against ARCHITECTURE_PRINCIPLES.md]

#### Architecture Compliance
- SOLID: [findings or "no violations"]
- Layer boundaries: [findings or "respected"]
- Config purity: [findings or "maintained"]

#### Verdict
- GO / NOGO / CONDITIONAL GO
```

**Stop hook markers:** `Findings`, `Architecture Compliance`, `Verdict`
**Cross-chat block:** not required

---

#### `verifier`

```
### Verification Review

#### Findings
1. [finding with severity + file reference]

#### Proof Verification
- Claimed tests: [confirmed/refuted]
- Claimed checks: [confirmed/refuted]
- Architecture compliance: [findings]

#### Verdict
- GO / NOGO / CONDITIONAL GO

### Copy-Paste Prompt For Implementation Chat

(fenced text block with neutral language — see Section 7)
```

**Stop hook markers:** `Findings`, `Proof Verification`, `Verdict`, plus cross-chat block markers
**Cross-chat block:** **required**

---

#### `validation-reviewer`

```
### Validation Review

#### Findings
1. [finding about test coverage or quality]

#### Coverage Assessment
- Claimed coverage: [confirmed/refuted]
- Critical paths tested: [yes/no + which missing]

#### Verdict
- GO / NOGO / CONDITIONAL GO
```

**Stop hook markers:** `Findings`, `Coverage Assessment`, `Verdict`
**Cross-chat block:** not required (optional on NOGO)

---

#### `doc-reviewer`

```
### Documentation Review

#### Findings
1. [inaccuracy or missing piece]

#### Accuracy
- Code references correct: [yes/no]
- Outdated sections: [none or specific]

#### Verdict
- GO / NOGO / CONDITIONAL GO
```

**Stop hook markers:** `Findings`, `Verdict`
**Cross-chat block:** not required

---

## 7. Cross-Chat Block Language

### 7.1. Design Principle — Non-Directive

The cross-chat block carries **facts**, not instructions. The receiving agent's role guide already defines how to respond. The block must not contain imperatives like "Verify…", "Check whether…", "Return findings first…", "Required fixes:", or "Return requirement:".

### 7.2. imp → qa (implementer/validator sub-roles)

```text
@qa verifier: Review the latest implementation work on this branch.

Review target:
- Branch: [branch name]
- Files in scope:
  1. [file path]

Implementation claim:
- [what was changed and what is claimed complete]

Proof provided:
- Tests: [exact tests run]
- Checks: [exact checks run]
- Outcomes: [exact outcomes]
- Gaps: [explicit list or none]
```

### 7.3. qa → imp (verifier sub-role)

```text
@imp implementer: Latest QA review produced findings for this branch.

Findings to resolve:
1. [finding]

Files in scope:
1. [file path]

Out of scope:
- [what must not be touched]

Proof expected:
- [what evidence QA expects on re-review]
```

---

## 8. Agent Wrapper Updates

### 8.1. argument-hint in imp.agent.md

```yaml
argument-hint: >
  Sub-role + task. Available sub-roles: researcher, planner, designer,
  implementer (default), validator, documenter.
  Example: "implementer: start cycle C_LOADER.5 for issue 257"
```

### 8.2. argument-hint in qa.agent.md

```yaml
argument-hint: >
  Sub-role + review target. Available sub-roles: plan-reviewer,
  design-reviewer, verifier (default), validation-reviewer, doc-reviewer.
  Example: "verifier: review latest implementation handover for cycle C_LOADER.5"
```

---

## 9. Stop Hook Design

### 9.1. Sub-Role Detection

The hook detects the sub-role by parsing the first user message in the transcript for known sub-role keywords. No MCP state is read.

```python
ALL_SUB_ROLES: dict[str, list[str]] = {
    "imp": ["researcher", "planner", "designer", "implementer", "validator", "documenter"],
    "qa": ["plan-reviewer", "design-reviewer", "verifier", "validation-reviewer", "doc-reviewer"],
}

DEFAULT_SUB_ROLE: dict[str, str] = {"imp": "implementer", "qa": "verifier"}

def detect_sub_role(records: list[dict[str, str]], role: str) -> str:
    """Detect sub-role from first user message. Returns default if undetectable."""
    for record in records:
        if record["role"] == "user":
            text_lower = record["text"].lower()
            for sub_role in ALL_SUB_ROLES.get(role, []):
                if sub_role.replace("-", " ") in text_lower or sub_role in text_lower:
                    return sub_role
            break  # only check first user message
    return DEFAULT_SUB_ROLE.get(role, "implementer")
```

### 9.2. Sub-Role Requirements Matrix

```python
class SubRoleRequirement(TypedDict):
    heading: str
    markers: list[str]
    requires_crosschat_block: bool
    crosschat_heading: str
    crosschat_prefix: str
    crosschat_markers: list[str]
```

Each `(role, sub_role)` pair has a `SubRoleRequirement` entry. When `requires_crosschat_block` is `False`, the hook only checks for the heading and markers. When `True`, it additionally validates the cross-chat block structure.

### 9.3. Enforcement Matrix Summary

| Role | Sub-Role | Output Heading | Cross-Chat Block | Default |
|---|---|---|---|---|
| imp | researcher | Research Output | no | no |
| imp | planner | Planning Output | no | no |
| imp | designer | Design Output | no | no |
| imp | **implementer** | Implementation Hand-Over | **yes** | **yes** |
| imp | validator | Validation Hand-Over | **yes** | no |
| imp | documenter | Documentation Output | no | no |
| qa | plan-reviewer | Planning Review | no | no |
| qa | design-reviewer | Design Review | no | no |
| qa | **verifier** | Verification Review | **yes** | **yes** |
| qa | validation-reviewer | Validation Review | no | no |
| qa | doc-reviewer | Documentation Review | no | no |

### 9.4. Backward Compatibility

When sub-role is not detected (default), the hook behaves identically to the current implementation: it enforces the `implementer` / `verifier` format including cross-chat blocks. No existing workflow breaks.

---

## 10. Slash Prompt Design

### 10.1. Proposed Prompt Set

| Prompt | Agent | Purpose |
|---|---|---|
| `/start-work` | imp | Begin session with active sub-role |
| `/resume-work` | imp | Rebuild context after compaction |
| `/prepare-handover` | imp | Produce cross-chat block (required for implementer/validator, optional for others) |
| `/transition-phase` | imp | Check exit gates and execute phase transition |
| `/request-review` | qa | Start review with active sub-role |
| `/prepare-brief` | qa | Produce implementation brief for @imp chat |

### 10.2. How Prompts Reference Role Definitions

Every prompt contains a standard Role Activation section:

```markdown
## Role Activation
1. Read [imp_agent.md](../../imp_agent.md) (or qa_agent.md for qa prompts).
2. Identify the sub-role from the user's argument.
3. Follow the sub-role definition in the role guide.
4. If no sub-role is specified, default to implementer / verifier.
```

The prompt contains **only operational instructions** (what to do, what format). The prompt does **not** contain identity, boundaries, or doctrine — those live in the role guide.

---

## 11. Phase Transition Ownership

### 11.1. Rule

@imp executes all state mutations. @qa remains read-only.

Transitions are write operations (`transition_phase`, `transition_cycle`). If QA executed them, it would breach the read-only boundary. QA functions as a gate — the transition may only happen after QA has given GO.

### 11.2. Transition Flow

```
1. @imp works in current phase (user specifies sub-role)
2. @imp produces output → optional copy-paste to QA chat
3. @qa reviews → gives GO/NOGO for the phase
4. On GO: user triggers /transition-phase in @imp chat
5. @imp checks exit gates, executes transition_phase (if MCP available)
   OR: @imp documents the transition textually (if MCP unavailable)
6. @imp activates new sub-role for the next phase
```

### 11.3. Double Decoupling

- From MCP: if the transition tool doesn't work, the transition is not blocking
- From QA: QA advises GO but does not execute

---

## 12. Flow Overview

```
                    @imp                              @qa
                    ────                              ───
research    ┌─ researcher ──────────────────────────────────────┐
            │  output: research doc                             │
            │  hand-over: optional                              │
            └───────────────────────────────────────────────────┘

planning    ┌─ planner ───────────────┐  ┌─ plan-reviewer ─────┐
            │  output: planning.md     │→│  review: coherence   │
            │  hand-over: optional     │  │  verdict: GO/NOGO   │
            └──────────────────────────┘  └─────────────────────┘

design      ┌─ designer ──────────────┐  ┌─ design-reviewer ───┐
            │  output: design.md       │→│  review: architecture│
            │  hand-over: optional     │  │  verdict: GO/NOGO   │
            └──────────────────────────┘  └─────────────────────┘

implement.  ┌─ implementer ───────────┐  ┌─ verifier ──────────┐
            │  output: code + tests    │→│  review: correctness │
            │  hand-over: REQUIRED     │  │  verdict: GO/NOGO   │
            │  (stop hook enforced)    │  │  hand-over: REQUIRED│
            └──────────────────────────┘  └─────────────────────┘

validation  ┌─ validator ─────────────┐  ┌─ validation-reviewer┐
            │  output: E2E tests       │→│  review: coverage    │
            │  hand-over: REQUIRED     │  │  verdict: GO/NOGO   │
            └──────────────────────────┘  └─────────────────────┘

document.   ┌─ documenter ────────────┐  ┌─ doc-reviewer ──────┐
            │  output: reference docs  │→│  review: accuracy    │
            │  hand-over: optional     │  │  verdict: GO/NOGO   │
            └──────────────────────────┘  └─────────────────────┘

transitions: always @imp via /transition-phase, after QA GO
```

---

## 13. Implementation Plan

### Step 1 — Sub-Role Sections in Role Guides (textual only)
Add sub-role definitions and output format expectations to `imp_agent.md` and `qa_agent.md`. No code changes.

### Step 2 — argument-hint Updates
Update `argument-hint` in both `.github/agents/imp.agent.md` and `.github/agents/qa.agent.md` to list available sub-roles. No code changes.

### Step 3 — Stop Hook Extension
Extend `stop_handover_guard.py` with `SubRoleRequirement` matrix, transcript-based sub-role detection, and per-sub-role enforcement logic. Update tests.

### Step 4 — Slash Prompt Restructuring
Create `/start-work`, `/resume-work`, `/prepare-handover`, `/transition-phase`, `/request-review`, `/prepare-brief` prompts. Remove or rename deprecated prompts.

### Step 5 — Template Extraction
Move hand-over templates and cross-chat block templates from role guides into prompts.

### Step 6 — Cleanup
Remove old formats from `_agent.md` files. Verify backward compatibility.

Each step is independently testable and backward compatible.

---

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| User forgets to specify sub-role | Hook defaults to strictest enforcement (implementer/verifier) — may block unnecessarily | argument-hint in agent wrapper reminds user of available sub-roles |
| Sub-role keyword appears in task description but is not the intended sub-role | Wrong enforcement profile applied | Detection uses only the first user message and exact keyword match |
| Sub-role definitions in role guide drift from hook requirements | Inconsistent behavior | Hook is the enforcement authority; role guide is the behavioral authority — prompts connect them |
| Prompt proliferation | Maintenance burden | Set is deliberately minimal (6 prompts, down from current 7) |
| MCP transition tools unavailable | Phase transition cannot be recorded in .st3 | @imp documents transition textually; state can be reconstructed later |

---

## Related Documentation

- [Compact Orchestration Design v1.0](docs/development/issue263/design.md)
- [Research Baseline](docs/development/issue263/research.md)
- [imp_agent.md](imp_agent.md) — implementation role guide
- [qa_agent.md](qa_agent.md) — QA role guide
- [ARCHITECTURE_PRINCIPLES.md](docs/coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-03-18 | QA analysis session | Initial draft based on QA/user collaborative design session |
