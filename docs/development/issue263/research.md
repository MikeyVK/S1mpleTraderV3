# VS Code Agent Orchestration — Research Baseline

**Status:** PRELIMINARY RESEARCH  
**Version:** 1.0  
**Created:** 2026-03-17  
**Updated:** 2026-03-17  
**Author:** Research phase  
**Scope:** Preserve the broader orchestration exploration before narrowing to an implementation-only design.

---

## 1. Purpose

This document preserves the broader orchestration direction that was explored before the scope was deliberately reduced. It exists so the project does not lose the reasoning, patterns, and rejected options behind issue 263 when the active design is narrowed to an ultra-light implementation-only approach.

The previous document mixed several concerns:
- VS Code hooks
- custom agents
- prompt files
- instructions files
- workphase orchestration across the full development lifecycle
- MCP workflow integration
- `.st3` state usage
- role routing and tool gating

That broader exploration was useful as research, but too wide and too coupled to remain the active design for the current goal.

---

## 2. Research Goal

The original exploration tried to answer this question:

How far can VS Code Copilot native capabilities be used to create structured agent cooperation, compaction recovery, and phase-aware work guidance inside this repository?

The answer is: quite far technically, but not without architectural tradeoffs.

---

## 3. What Was Explored

### 3.1 Hooks as Lifecycle Bridges

The research confirmed that VS Code hook files are a viable primitive for:
- session-start context injection
- pre-compaction state capture
- optional pre-tool warnings or blocking

This is valuable because hooks are editor-native and require no custom UX layer.

### 3.2 Custom Agents as Role Containers

The research also confirmed that custom agents are a workable way to encode role behavior. The main explored role model was:
- `@researcher`
- `@imp`
- `@writer`
- `@qa`

This made the producer/verifier pattern explicit and reusable.

### 3.3 Prompt Files as Repeatable Workflows

Prompt files were explored as a way to standardize recurring tasks:
- recovery after compaction
- handover generation
- QA verification
- research/planning/design starts
- implementation and validation starts
- documentation and coordination starts

This is useful, but only if the surrounding workflow model is stable enough.

### 3.4 Instructions as Context Filters

The research explored `.instructions.md` files as a way to move domain rules out of a single large `.copilot-instructions.md` file and load them only when relevant.

That direction remains valid, but it is orthogonal to the immediate implementation-only orchestration goal.

---

## 4. Valuable Findings

### 4.1 Producer/Verifier Is the Strongest Reusable Pattern

The single strongest pattern from the broader exploration is the explicit producer/verifier split:
- one role produces change
- one role verifies claims
- handover is explicit
- approval authority stays outside implementation

This pattern maps cleanly onto the `.github/agents/imp.agent.md` and `.github/agents/qa.agent.md` guides.

### 4.2 Compaction Recovery Needs a Small Persistent Memory

The research strongly supports lightweight persistence across compaction. Without it, the agent loses:
- current user goal
- files in scope
- current role
- pending handover intent

That does not require MCP workflow state. It only requires a very small context snapshot.

### 4.3 Handover Quality Matters More Than Agent Count

The quality of the implementation handover and QA verification contract is more important than the number of roles. The strongest existing material in this repository is already centered on:
- startup discipline after compaction
- scope lock
- truthfulness rules
- explicit proof expectations
- read-only QA boundaries

Those principles should survive intact in a reduced design.

### 4.4 Native VS Code Features Are Sufficient for an Ultra-Light Model

The research indicates that a useful orchestration layer does not need:
- issue/phase awareness from MCP state
- branch naming rules
- planning-cycle state in `.st3`
- cross-phase routing
- repository-specific orchestration infrastructure

Hooks plus two custom agents can already cover the implementation scenario effectively.

---

## 5. Why the Broad Design Was Too Coupled

### 5.1 MCP Workflow Coupling

The broad design assumed `.st3/state.json`, `.st3/projects.json`, and related workflow state as runtime dependencies for hook behavior. That creates coupling to a specific server-side workflow engine.

That is a problem because the current objective is specifically to support hooks and custom agents even when no MCP workflow orchestration exists.

### 5.2 Hardcoded Workflow Knowledge

The broad design introduced explicit mappings such as:
- phase to agent
- phase to tool restrictions
- workflow type to role sequence

That violates the direction of the architecture contract when such knowledge is embedded directly into implementation code instead of remaining configurable or being removed from scope.

### 5.3 Repo-Specific Path Knowledge

The broad design assumed repository-specific folders and state conventions, especially around `.st3/`, issue folders, and workflow documents.

For an implementation-only orchestration layer, that is unnecessary and makes the solution less portable.

### 5.4 Too Many Responsibilities in One Layer

The broad design tried to solve at once:
- lifecycle recovery
- role routing
- workflow enforcement
- documentation orchestration
- issue coordination
- state persistence
- tool gating

That is not SRP-friendly. The current need is narrower and should be designed as such.

---

## 6. Patterns Worth Preserving

The following ideas from the broader exploration should be preserved in the compact design:

1. Session-start context injection.
2. Pre-compaction snapshotting.
3. Explicit implementation agent versus QA agent split.
4. Strong startup protocol after compaction.
5. Structured handover contract.
6. Skeptical read-only QA verification.
7. Minimal editor-native configuration through hooks, agents, and optional prompts.

The following ideas should be removed from the active design:

1. Full lifecycle orchestration beyond implementation.
2. Phase-aware routing.
3. MCP workflow state as an orchestration dependency.
4. `.st3` as a required runtime boundary.
5. Research, planning, writer, and coordination agents.
6. Tool gating based on repository workflow phases.

---

## 7. Research Conclusion

The broad orchestration concept was useful research, not the right active design.

Its main contribution is not the exact file layout or workflow coupling. Its contribution is the recognition that a small implementation cockpit can be built from native VS Code primitives if it keeps only the strongest invariants:
- implementation has scope and proof discipline
- QA is read-only and skeptical
- compaction must not erase the active task
- handover must be explicit and falsifiable

That conclusion directly informs the compact design in `design.md`.

---

---

## 10. V2 Research: Sub-Role Orchestration (2026-03-19 / 2026-03-20)

**Context:** After C_PKG.1–5 (coarse seam migration) were completed and verified, the decision was taken not to merge the v1 design but to refactor according to a v2 sub-role model. The branch phase was forced back to `research`. This section documents the findings from that research cycle.

**Reference:** `docs/development/issue263/design_v2_sub_role_orchestration.md`

---

### 10.1 V2 Design: What Holds

The v2 design document (`design_v2_sub_role_orchestration.md`) is architecturally sound on the following points:

- **Sub-role model**: 6 `@imp` sub-roles (researcher, planner, designer, implementer, validator, documenter) and 5 `@qa` sub-roles (plan-reviewer, design-reviewer, verifier, validation-reviewer, doc-reviewer) cover the full development lifecycle without coupling to any specific workflow engine.
- **Enforcement matrix**: only `implementer`, `validator` (imp) and `verifier` (qa) require a cross-chat handover block. All others pass through the stop hook without validation. This is correct: the handover block guards the role boundary, not phase completion.
- **Authority separation**: hook is the enforcement authority, role guide is the behavioral authority, prompts are the UX connection. No single file owns all three.
- **Implementation plan sequence** (§13, Steps 1–6): each step is independently deployable and backward compatible. The sequence is well-ordered.

---

### 10.2 V2 Design: What Needed Revision

**Handoffs rejected entirely**

The v2 design mentioned handoffs (VS Code 1.112 native feature) as a possible delivery mechanism for cross-chat handover blocks. Research showed two reasons to reject this:

1. _Context pollution_: handoffs switch roles within the same conversation, passing the full conversation history to `@qa`. The friction of copy-paste is a quality gate, not a UX problem — it forces `@imp` to curate what counts as evidence.
2. _Phase ≠ turn_: a phase is a multi-turn session. A handoff button appears after every turn. There is no mechanism for a handoff to know whether a phase is complete. The user is the sole phase-transition authority. This rejects handoffs for intra-role transitions (researcher→planner) as well as cross-role transitions.

**Sub-role detection: transcript parsing replaced by UserPromptSubmit hook**

The v2 design proposed `detect_sub_role()` in the Stop hook, parsing the transcript back to the first user message. VS Code 1.112 introduced the `UserPromptSubmit` hook which receives the prompt text directly as `{"prompt": "..."}` via stdin — no file I/O, no JSONL parsing, no first-message ambiguity.

The revised approach:
- `UserPromptSubmit` hook detects sub-role from prompt text → writes `.copilot/session-sub-role.json`
- Hook is idempotent: if state file exists for current session, skip
- Stop hook reads state file → validates per sub-role requirements

This eliminates ~70% of the transcript-parsing complexity and handles the resume-after-compaction scenario correctly (first prompt after compaction sets the sub-role, not a recovered snapshot message).

**NL detection without LLM**

Two-step detection:
1. `re.search(r'\b(researcher|planner|designer|implementer|validator|documenter|verifier)\b', prompt, re.IGNORECASE)` — covers canonical names and simple variations
2. `difflib.get_close_matches` on words ≥ 7 chars with cutoff 0.85 — covers typos (`"researher"` → `researcher`, `"plannner"` → `planner`) without loading a language model

Default on no match: `implementer` for `@imp`, `verifier` for `@qa` (strictest enforcement, safe default).

---

### 10.3 Hook Lifecycle: Precise Responsibility Allocation

Each hook fires at a specific moment with a specific capability set. Conflating these leads to design errors.

| Hook | Fires | Can inject into model | Knows sub-role |
|---|---|---|---|
| `SessionStart` | Once, before first user prompt | Yes (`additionalContext`) | No |
| `UserPromptSubmit` | Every prompt, before agent response | No (only `systemMessage` to UI) | Yes (reads from prompt) |
| `PreCompact` | Before compaction (may fire multiple times) | No | Yes (reads state file) |
| `Stop` | End of every agent turn | No | Yes (reads state file) |

**Critical constraint identified (Gap A):** The only hook that can inject context into the model (`SessionStart.additionalContext`) fires before the sub-role is known. The hook layer cannot inform the model of its sub-role. The model learns its sub-role exclusively from the user's prompt and static instructions (`imp_agent.md`). Hooks support detection and validation only — they do not instruct the model.

**State file as coordination mechanism:** `.copilot/session-sub-role.json` is the shared state between:
- `UserPromptSubmit` (writer on first prompt)
- `PreCompact` (saves sub-role to survive compaction)
- `Stop` (reader for enforcement decisions)

State file must include `session_id` to detect stale data from a previous session. Mismatch → ignore file, use role default.

---

### 10.4 Stop Hook: Corrected Semantics

**Gap B resolved:** The stop hook fires at the end of every agent turn, not when the user closes the chat. In a 30-turn research session it fires 30 times. For sub-roles with `requires_crosschat_block: false` the correct behavior is **pass-through** — no content validation. The hook guards the role-boundary handover, not phase completion. Phase completion is the user's decision.

**Gap B consequence:** Testing the stop hook against specific sub-role names is fragile. The test matrix must test the rule engine, not the rules:

- Tests use fixture configurations (inline dicts), not production `requirements.json`
- Tests assert behavior given `requires_crosschat_block=true/false` — no sub-role names
- If a project later makes `planner` require a block, no tests break

Approximately 12 behavior-condition cases replace the earlier 27 name-based cases.

---

### 10.5 Canonical Requirements File (OQ-4 resolved)

**Problem:** markers are currently hardcoded in `stop_handover_guard.py`. With 11 sub-roles, any marker change requires coordinated edits to hook code, prompt templates, and role guide — with no enforcement of consistency.

**Solution:** `.copilot/sub-role-requirements.json` becomes the single source of truth. Structure:

```json
{
  "version": "1",
  "roles": {
    "imp": {
      "default_sub_role": "implementer",
      "sub_roles": {
        "researcher":  { "requires_crosschat_block": false },
        "planner":     { "requires_crosschat_block": false },
        "designer":    { "requires_crosschat_block": false },
        "documenter":  { "requires_crosschat_block": false },
        "implementer": {
          "requires_crosschat_block": true,
          "heading": "### Copy-Paste Prompt For QA Chat",
          "block_prefix": "@qa Review the latest implementation work on this branch.",
          "guide_line": "Use qa_agent.md as the project-specific QA guide.",
          "markers": [
            "Review target:",
            "Implementation claim under review:",
            "Proof provided by implementation:",
            "QA focus:"
          ]
        },
        "validator": {
          "requires_crosschat_block": true,
          "heading": "### Copy-Paste Prompt For QA Chat",
          "markers": ["Validation target:", "Coverage claim:", "Proof provided:", "QA focus:"]
        }
      }
    },
    "qa": {
      "default_sub_role": "verifier",
      "sub_roles": {
        "plan-reviewer":       { "requires_crosschat_block": false },
        "design-reviewer":     { "requires_crosschat_block": false },
        "validation-reviewer": { "requires_crosschat_block": false },
        "doc-reviewer":        { "requires_crosschat_block": false },
        "verifier": {
          "requires_crosschat_block": true,
          "heading": "### Copy-Paste Prompt For Implementation Chat",
          "block_prefix": "@imp Address the latest QA findings on this branch.",
          "guide_line": "Use imp_agent.md as the project-specific implementation guide.",
          "markers": [
            "Task:",
            "Files likely in scope:",
            "Findings to resolve:",
            "Out of scope:",
            "Proof expected:"
          ]
        }
      }
    }
  }
}
```

The package ships a `_default_requirements.json` as fallback. At runtime the hook looks for `.copilot/sub-role-requirements.json` (project-specific override) first, falls back to the package default. This keeps the package standalone and lets projects customize without forking.

---

### 10.6 Atomic Marker Migration (OQ-2 resolved)

With the canonical requirements file, the migration from v1 hardcoded markers to v2 non-directive markers is a single atomic commit:

1. Create `.copilot/sub-role-requirements.json` with v2 markers
2. Rewrite hook to read markers from file instead of hardcoded dict — in the same commit
3. Update prompts to use v2 marker language — in the same commit
4. Remove `ROLE_REQUIREMENTS` dict from `stop_handover_guard.py`

The hook and prompt are only out of sync if they are committed separately. A single commit eliminates the partial-state window.

---

### 10.7 Prompt Set Revision (OQ-1 resolved)

From 7 current prompts to 6:

| Current | V2 | Change |
|---|---|---|
| `start-implementation` | `/start-work` | Rename + add sub-role list to argument-hint |
| `resume-implementation` | `/resume-work` | Rename + add state-file recovery step |
| `prepare-handover` | `/prepare-handover` | Update markers to reference requirements file |
| `request-qa-review` | `/request-review` | Rename + add sub-role context to startup protocol |
| `prepare-implementation-brief` | keep | Add sub-role context (implementer/validator) |
| `prepare-qa-brief` | keep | Add sub-role context (verifier) |
| `plan-executionDirectiveBatchCoordination` | **removed** | Outside orchestration scope |

The two brief prompts remain separate — merging loses role-specific structure for marginal gain.

No `/transition-phase` prompt: phase transitions are compact, directed operations that do not need a prompt template.

---

### 10.8 Coding Standards Review: Violations in the V2 Design

The v2 design as formulated in §10.2–10.6 was reviewed against `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md`. This review found four binding violations that must be corrected before planning. Each one is a law, not a suggestion.

---

**Violation 1: DRY + SSOT (§2) — no single reader for sub-role-requirements.json**

The research proposed that the Stop hook, the `UserPromptSubmit` hook, and potentially tests each read `.copilot/sub-role-requirements.json` directly. That is a DRY violation:

> *"Two classes independently reading the same config file without a shared interface is a DRY violation."*

The file has one shape, one schema, and one validation contract. There must be exactly one class that reads it: `SubRoleRequirementsLoader`. All consumers (hooks, tests, config validators) receive this class via dependency injection. No hook reads the file directly.

This also means every access to sub-role requirement data goes through a typed interface, not a raw `dict` key lookup. Unknown sub-role → explicit error from the loader, not `KeyError` at call site.

---

**Violation 2: Config-First (§3) — sub-role names hardcoded in detection logic**

The NL detection approach described in §10.2 used a hardcoded regex alternation:

```python
re.search(r'\b(researcher|planner|designer|implementer|validator|documenter|verifier)\b', ...)
```

And a hardcoded word list for `difflib.get_close_matches`. Both are Config-First violations:

> *"An `if phase_name == 'implementation'` in production code is a Config-First violation."*

The list of valid sub-role names is already defined in `sub-role-requirements.json` (§10.5). The detection logic must build its candidate set by reading that list from the loader at runtime. Adding a new sub-role to the requirements file must never require a code change in `detect_sub_role.py`.

---

**Violation 3: SSOT (§2) — sub-role names duplicated across locations**

As described in §10.2–10.5, sub-role names would appear in at minimum: the requirements JSON, the regex pattern, the difflib candidate list, the state-file writer, and tests. That is five locations for one piece of knowledge.

> *"Every fact in the system has exactly one authoritative location."*

The authoritative location is `sub-role-requirements.json`. Every other location must derive from it dynamically. The `SubRoleRequirementsLoader` exposes a method (e.g. `valid_sub_roles(role: str) -> frozenset[str]`) that all consumers call. The loader is the single point where the list is materialized.

---

**Violation 4: Fail-Fast (§4) — silent default on missing or malformed config**

The research described: "Default at no match: `implementer` for `@imp`, `verifier` for `@qa`." That default is correct as a *detection* fallback (no keyword found in the prompt). It is not correct as a *config* fallback.

The distinction:

| Situation | Correct behaviour |
|---|---|
| No sub-role keyword in user prompt | Default to role's `default_sub_role` from config |
| `sub-role-requirements.json` missing | `FileNotFoundError` with explicit path — never silent |
| `sub-role-requirements.json` malformed | `ConfigError` naming the missing/invalid field — never silent |
| Sub-role in state file not present in config | `ConfigError` at load time — not `KeyError` at hook execution |

> *"Missing config files → explicit `FileNotFoundError` with path, never `None` return."*
> *"An unknown action type in an enforcement config → `ConfigError` on startup. Never a `KeyError` at execution time."*

The package ships a `_default_requirements.json` as fallback (§10.5). The loader first checks `.copilot/sub-role-requirements.json`; if absent it loads the package default. If neither exists, it raises `FileNotFoundError`. It never silently returns `None` or an empty structure.

---

**Consequence for Dependency Injection (§11) — no inline dicts in tests**

The coding standards require:

> *"All production dependencies are injectable. Tests inject a fake/in-memory variant."*

The earlier test matrix description mentioned "fixture configurations (inline dicts)." That bypasses the injection contract. Correct test approach:

- `SubRoleRequirementsLoader` accepts a `Path` constructor argument
- Tests construct the loader with a temp-file or in-memory equivalent pointing to a known fixture JSON
- No test reaches into hook internals to swap out a `ROLE_REQUIREMENTS` dict — the dict does not exist in v2
- Test isolation is achieved by injecting a loader with controlled config, not by patching module-level state

---

**Summary: what these violations change in the implementation plan**

| Design element | As described in §10.x | Correction required |
|---|---|---|
| Config reading | Hook reads JSON file directly | `SubRoleRequirementsLoader` class; hooks receive via DI |
| Sub-role detection candidates | Hardcoded regex alternation + difflib word list | Candidates loaded from `SubRoleRequirementsLoader.valid_sub_roles()` |
| Sub-role name authority | Present in 5+ locations | Single authority: `sub-role-requirements.json`, exposed via loader |
| Missing config behaviour | Silent fallback to default | Explicit `FileNotFoundError` / `ConfigError` |
| Test isolation mechanism | Inline fixture dicts | Loader injected with fixture-path JSON |

These corrections do not change the architectural intent of §10.2–10.6. They make the implementation compliant with the binding standards before code is written.

---

### 10.9 Test Location and Technical Debt: Explicit Deletion Required

The current test suite contains two misplaced test files:

```
tests/mcp_server/unit/utils/test_stop_handover_guard.py
tests/mcp_server/unit/utils/test_pre_compact_agent.py
```

These files must be **deleted**, not relocated. Two reasons:

**1. Wrong namespace.** They live under `tests/mcp_server/` but test `copilot_orchestration` package code. There is no structural relationship between the MCP server and the orchestration package. Relocating them would carry the misclassification forward.

**2. Wrong abstraction.** `test_stop_handover_guard.py` tests the v1 hardcoded `ROLE_REQUIREMENTS` dict. `test_pre_compact_agent.py` tests `parse_transcript_content` in isolation. Both test v1 internals that the v2 refactor replaces entirely with a loader-based architecture. Moving these tests relocates technical debt instead of resolving it.

**Resolution:** Delete both files as an explicit pre-TDD cleanup step. The v2 TDD phase writes new tests under:

```
tests/copilot_orchestration/
└── unit/
    └── hooks/
        ├── __init__.py
        ├── test_stop_handover_guard.py       ← new: tests loader-based hook
        ├── test_detect_sub_role.py           ← new: tests UserPromptSubmit handler
        └── test_requirements_loader.py       ← new: tests SubRoleRequirementsLoader
```

This is technical debt resolution, not scope reduction. The coverage gap between deletion and the new tests is intentional: the v1 tests pass against v1 code and would fail against v2 code. They are not a safety net — they are a constraint that blocks the correct v2 implementation.

---

### 10.9 Remaining Deferred Questions

- **OQ-1 final prompt content**: prompt body changes depend on the wider workflow model being stable. Bodies are deferred to planning/design phase.
- **Gap D (extension point)**: content validation beyond marker presence (e.g. "is research.md present after a researcher session?") is project-specific and must not be in the package. If needed, it requires a declared extension point. Not in scope for v2.

---

### 10.10 Target Package Structure

> **This is the authoritative target structure for all v2 new modules.**
> Reference: `copilot_orchestration_packaging_research.md §2.1` (origin of the decision; this section states the conclusion self-contained so `research.md` is independently readable).

**Design principle — hooks/ contains ONLY VS Code stdin/stdout adapter entry-points.**
Contracts, config, and shared utilities belong in dedicated submodules. Placing them under `hooks/` would make the adapter layer responsible for schema definition, file I/O logic, and path resolution — a direct SRP violation.

**Extraction readiness.** The structure below is designed so that moving the package to its own git repository after v2 validation requires no further file reorganisation: `src/copilot_orchestration/` and `tests/copilot_orchestration/` copy as-is; a minimal `pyproject.toml` is the only addition needed.

#### Full target tree (v2 deliverables only — existing hooks/ scripts are not moved)

```
src/copilot_orchestration/
├── __init__.py                          (existing)
├── contracts/
│   ├── __init__.py                      (new)
│   └── interfaces.py                    (new) — ISubRoleRequirementsLoader Protocol,
│                                                  SubRoleSpec, SessionSubRoleState TypedDicts
├── config/
│   ├── __init__.py                      (new)
│   ├── requirements_loader.py           (new) — SubRoleRequirementsLoader (YAML + Pydantic)
│   └── _default_requirements.yaml      (new) — package fallback config
├── utils/
│   ├── __init__.py                      (new)
│   └── _paths.py                        (new) — find_workspace_root(), STATE_RELPATH constant
└── hooks/                               (existing namespace — entry-points only)
    ├── __init__.py                      (existing)
    ├── detect_sub_role.py               (new) — __main__ adapter: reads argv/stdin, calls
    │                                             package, writes state file
    ├── notify_compaction.py             (new) — __main__ adapter: reads stdin, calls
    │                                             package, writes stdout
    ├── stop_handover_guard.py           (existing — refactored to use DI, not moved)
    └── [session_start*, pre_compact*]   (existing — untouched in v2)

tests/copilot_orchestration/unit/
├── config/
│   ├── __init__.py
│   └── test_requirements_loader.py
├── hooks/
│   ├── __init__.py
│   ├── test_detect_sub_role.py
│   └── test_stop_handover_guard.py
└── utils/
    ├── __init__.py
    └── test_paths.py
```

#### Submodule responsibilities (one sentence each)

| Submodule | Responsibility |
|-----------|---------------|
| `contracts/` | Defines the `ISubRoleRequirementsLoader` Protocol and all shared TypedDicts; owns zero runtime I/O. |
| `config/` | Owns the `SubRoleRequirementsLoader` implementation (YAML + Pydantic) and the package fallback YAML; the sole entry point for all config reads. |
| `utils/` | Provides `find_workspace_root()` and the `STATE_RELPATH` constant; imported by all hook entry-points so path discovery is never duplicated. |
| `hooks/` | Contains only VS Code hook adapter entry-points (`__main__` blocks + thin wrappers); adapters import from `contracts/`, `config/`, and `utils/` but define no domain logic themselves. |

---

## 8. Inputs for the Compact Design

The compact design should now optimize for these constraints:
- implementation scenario only
- no MCP workflow dependency
- no `.st3` dependency
- no hardcoded project workflow model
- no path-bound domain logic
- minimal persistence only for compaction recovery
- high-quality role guidance at the level of `agent.md`, `.github/agents/imp.agent.md`, `.github/agents/qa.agent.md`, `.github/.copilot-instructions.md`, and `role_reset_snippets.md`

---

## 9. Deferred Ideas

The following ideas are intentionally deferred and not part of the compact design:
- multi-phase lifecycle orchestration
- documentation/research/writer role family
- client-side phase gating for tools
- issue-aware routing
- MCP resource-backed orchestration state
- broad prompt library for all workphases
- repo-specific orchestration packages

If those are ever revisited, they should return as a new design iteration after the lightweight implementation-only model has proven itself useful.
