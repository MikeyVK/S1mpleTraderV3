<!-- docs\development\issue283\research-ready-phase-enforcement.md -->
<!-- template=research version=8b7bb3ab created=2026-04-09T12:30Z updated= -->
# Ready Phase Enforcement — Preventing Branch-Local Artifacts from Reaching Main

**Status:** SUPERSEDED — See [research-submit-pr-impact-analysis.md](research-submit-pr-impact-analysis.md)
**Version:** 1.0
**Last Updated:** 2026-04-09

---

## Purpose

Establish the factual basis and architectural constraints that must govern the solution to issue #283,
and define the expected results that the design phase must achieve.

This document is **research only**. It does not prescribe designs, YAML structures, code patterns,
or implementation cycles. Those are the responsibility of the design and planning phases respectively.

## Scope

**In Scope:**
Root cause analysis of artifact contamination; assessment of alternative approaches and why they fail;
applicable architectural principles; flag-day scope definition; expected results framework.

**Out of Scope:**
Concrete YAML designs, implementation cycles, code-level decisions, tool internals, performance
concerns, workflows other than feature/bug/hotfix/refactor/docs/epic.

## Prerequisites

Read these first:
1. Issue #280 resolved and merged (PR #281)
2. PR #284 open but must NOT be merged (wrong .gitignore approach — see Investigated Alternatives)
3. `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — read in full before starting design

---

## Problem Statement

Branch-local MCP artifacts (`.st3/state.json`, `.st3/deliverables.json`) reach `main` during
PR merges. The artifacts are **intentionally git-tracked** for multi-machine workflow continuity:
machine A commits state, machine B pulls and continues work. This tracking requirement rules out
any solution that removes the files from git.

Additionally, ad-hoc debug scripts (`check_yaml.py`, `fix_yaml.py`, `revert_yaml.py`,
`show_yaml.py`) were committed to a feature branch and landed on `main` via PR merge. These were
never intended for main and represent a separate but related hygiene problem.

### Root Cause Analysis

Three independent root causes make the existing `.gitattributes merge=ours` strategy unreliable.
All three must be understood because any replacement solution must be immune to them.

**Root Cause 1 — Chicken-and-Egg `.gitattributes`:**
The `merge=ours` rule was introduced on a feature branch, not on `main` first. The rule was
therefore absent from `main` at the moment of the merge it was meant to protect against.
It protected nothing on its first use.

**Root Cause 2 — `merge=ours` does not fire on fresh file additions:**
`merge=ours` is a conflict-resolution driver. It activates only when a file exists on both sides
of a merge and conflicts. When `main` has no `state.json` and the branch adds it, git sees a clean
addition — no conflict, no merge driver, the file lands on `main` unconditionally.

**Root Cause 3 — GitHub server-side merges do not respect `.gitattributes` merge drivers:**
GitHub executes PR merges via its own infrastructure. Custom merge drivers are not reliably
honoured, even when the rule is correctly present on `main`. This makes `.gitattributes`
merge driver strategies fundamentally unreliable for GitHub-hosted repositories.

---

## Background

After the merge of PR #281 (issue #280 fix) `main` was found contaminated. Issue #283 was
created to fix this. A first attempt (branch `hotfix/283-...`, PR #284) resolved the problem by
adding `state.json` to `.gitignore` and removing it from git tracking. This was rejected:
removing tracking breaks the multi-machine use case.

The current branch (`refactor/283-ready-phase-enforcement`) implements the correct structural
approach, which was agreed upon in a design discussion after PR #284 was rejected.

The `hotfix/283-...` branch and PR #284 **must not be merged**. They will be closed.

---

## Research Questions

1. Why do none of the standard git-level approaches (`.gitattributes`, `.gitignore`, hooks) work
   for this problem without breaking the multi-machine constraint?
2. Which architectural principles define what a correct solution must look like?
3. What is the minimal required capability a solution must have?
4. What are the boundaries of a clean-break change — what is legacy, what must be removed?
5. What should be observably true after a correct implementation?

---

## Investigated Alternatives

### Alternative A — Remove from git tracking (`.gitignore`)

**Approach:** Add `state.json` and `deliverables.json` to `.gitignore`; `git rm --cached` to
stop tracking.

**Why it fails:** Multi-machine workflow continuity requires both files to be git-tracked.
User confirmed: *"Active simultaneous use — machine A commits, machine B picks up."*
Without tracking, state synchronisation between machines is impossible. This approach was
implemented in PR #284 and **rejected**.

### Alternative B — Git hooks (`pre-push` / `pre-merge-commit`)

**Approach:** A hook strips branch-local artifacts from the index before push or merge.

**Why it fails:**
- Requires `git config core.hooksPath` per machine; not automatic on clone
- Bypassed trivially by `git push --no-verify`
- Does not apply to server-side GitHub merges
- Not MCP-native; falls outside the enforced workflow

### Alternative C — `.gitattributes merge=ours`

**Approach:** Declare `state.json merge=ours` so git always keeps `main`'s version on merge.

**Why it fails:** See Root Cause 1, 2, and 3 above. This approach was already present in the
repository and demonstrably failed to protect `main`.

### Alternative D — Branch protection rules (GitHub)

**Approach:** Use GitHub required status checks or `CODEOWNERS` to block merges with these files.

**Why it fails:** Requires repository admin access and GitHub-specific configuration. Not
portable, not version-controlled, not MCP-native. Does not address ad-hoc debug scripts.

---

## Applicable Architectural Principles

The following principles from `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` are binding
constraints on any solution. The design phase must demonstrate compliance with each.

### Principle 2 — DRY + SSOT

> *Every fact in the system has exactly one authoritative location.*

The list of branch-local artifacts that must not reach `main` is a fact. It must live in
exactly one config location. Duplicating it as a hardcoded list in Python is a violation.

### Principle 3 — Config-First

> *Business knowledge needed in multiple places is always stored in config, never hardcoded.*

Phase-triggered behaviour (e.g., "exclude these files when committing in phase X") must be
declared in a YAML config file. An `if phase_name == "ready"` in Python production code is a
Config-First violation.

### Principle 4 — Fail-Fast

> *Configuration errors are detected at startup, not at runtime of a user action.*
> *Combination validations are checked in the Pydantic loader via `model_validator`, not in the consumer.*

Any new phase-related config constraint (e.g., "exactly one terminal phase") must be validated
at startup via Pydantic. The MCP server must not start with an inconsistent configuration.

### Principle 8 — Explicit over Implicit

> *No silent fallbacks, no implicit conventions that are not visible in code.*

The existence of a "terminal phase" must be explicitly declared in config, not inferred from
position in a list or derivable from a naming convention. Code that asks "is this the terminal
phase?" must read a declared flag, not compare a name.

### Principle 9 — YAGNI (Flag Day implication)

> *No backward-compat layer for deprecated parameters longer than one release cycle.*

Pre-existing behavior (no PR gate, no artifact exclusion) is being replaced entirely. No
gradual migration path is required or desired — see Flag Day Declaration below.

### Principle 10 — Cohesion

> *A method that exclusively needs domain X knowledge belongs in the class that models domain X.*

The question "is this phase the terminal phase?" belongs with the phase definition. The answer
must come from the phase config model, not from external registration or string comparison.

### Principle 13 — Enforcement is Config-First

> *Behavior that "triggers at phase X" is configured in a YAML enforcement file, not hardcoded in Python.*

The artifact exclusion behavior triggered in the terminal phase must be registered in an
enforcement config, not written as an `if` branch inside a tool.

---

## Flag Day Declaration

This change is a **clean break**. There is no backward compatibility layer, no gradual migration,
no legacy code path.

**What is removed entirely:**
- The `.gitattributes merge=ours` strategy for `state.json` (does not work — see Root Causes)
- Any code that allows `CreatePRTool` to run outside the terminal phase
- Any commit path that does not automatically exclude branch-local artifacts in the terminal phase

**What replaces it:**
A single, workflow-native mechanism where the branch is responsible for cleaning itself before
a PR can be created. The design phase will specify the mechanism.

**In-flight branches on deployment day:**
Branches that existed before this change and have not yet passed through the terminal phase will
need to transition manually. No automated migration is provided. `force_phase_transition` is the
escape hatch for human-approved exceptions.

**Schema flag day:**
The `workphases.yaml` schema will gain a boolean `terminal` field per phase entry. The config
loader enforces at startup that exactly one phase has `terminal: true`. Existing deployments
without any `terminal: true` entry will cause the MCP server to **fail to start**. Adding
`terminal: true` to the correct phase entry is the sole required migration step, and it ships
as part of this change.

---

## Open Questions

All questions resolved prior to design phase transition.

1. **Which config file is the authoritative source for enforcement behavior triggered at a specific
   phase?**
   `phase_contracts.yaml` — it is the existing home for exit-requirements and phase-triggered gates.
   A global `merge_policy` section at the top of that file follows the established convention and
   satisfies Principle 13.

2. **Which config loader file is responsible for injecting the terminal phase into workflow phase
   lists at load time?**
   `mcp_server/config/loader.py` — `ConfigLoader.load_workflow_config()` is the sole loader of
   `workflows.yaml` and constructs all workflow phase lists. Terminal phase injection belongs here
   (or in a dedicated enrichment step called from this method).

3. **What existing tests assert on workflow phase counts or phase ordering, and will they break?**
   A new `terminal` field with `False` as default does not break existing `PhaseDefinition` or
   `WorkphasesConfig` instantiations. However, tests that assert exact phase counts or phase order
   on loaded workflows will break when the loader injects the terminal phase. These must be updated
   as part of the implementation.

4. **How should in-flight branches (pre-terminal-phase) behave on the day of deployment?**
   `force_phase_transition` is sufficient. A release note in the PR description documents the
   required manual step. No automated migration is provided (YAGNI).

---

## Findings & Conclusions

1. No git-level mechanism (`.gitattributes`, `.gitignore`, hooks, branch protection) can solve this
   problem without either breaking the multi-machine constraint or being unreliable on GitHub.
2. The problem must be solved at the **workflow layer**, by making the branch responsible for
   excluding its own branch-local artifacts before a PR is possible.
3. The solution must be fully config-driven (Principles 2, 3, 13), fail-fast (Principle 4),
   explicit (Principle 8), and cohesive (Principle 10).
4. There is no justification for backward compatibility. A clean break is both correct and simpler.
5. The `workphases.yaml` and `phase_contracts.yaml` config files are the natural homes for the
   new declarations, consistent with the existing config hierarchy.

---

## Expected Results

The following must be observably true after a correct implementation. These are the success
criteria the design phase must achieve — not descriptions of how to achieve them.

### E1 — Terminal Phase Declared in Config

A phase exists in `workphases.yaml` that is explicitly marked as the terminal phase.
Exactly one such phase is permitted. The MCP server fails to start if zero or more than one
terminal phase is declared.

### E2 — Branch-Local Artifacts Registered in Config

A config-driven list exists that names which files are branch-local artifacts and documents why
they must not reach `main`. This list is the single authoritative source; no tool or code
duplicates it.

### E3 — PR Creation Gated on Terminal Phase

`CreatePRTool` (draft and non-draft) cannot be invoked outside the terminal phase. The error
message is actionable: it tells the developer what phase is required and how to get there.

### E4 — Artifact Auto-Exclusion on Commit in Terminal Phase

When `GitCommitTool` executes in the terminal phase, branch-local artifacts are automatically
removed from the commit index. The developer receives explicit output listing each excluded file
and the reason from config.

### E5 — Double-Check Gate in CreatePRTool

Even after E4, `CreatePRTool` verifies that no branch-local artifacts remain git-tracked before
creating the PR. If they do (e.g., due to manual `git add`), the tool blocks with an actionable
message.

### E6 — No Hardcoded Terminal Phase Name in Python

No Python file contains a hardcoded terminal phase name check. Phase identity is read from config.
All tests that verify terminal phase behavior are parameterized through the config, not through
string literals. (The candidate name "ready" appears in the branch name and illustrations only;
the design phase decides the final name.)

### E7 — Config Loader Injects Terminal Phase

Every workflow's active phase list contains the terminal phase as the last entry after loading,
regardless of whether it is explicitly listed in `workflows.yaml`.

### E8 — Server Fails Fast on Misconfiguration

Starting the MCP server with a `workphases.yaml` that contains zero or more than one terminal
phase raises a `ConfigError` with a clear message before any tool becomes callable.

### E9 — Main is Clean

After the first PR merged through the new enforcement:
- `.st3/state.json` and `.st3/deliverables.json` are absent from `main`
- `check_yaml.py`, `fix_yaml.py`, `revert_yaml.py`, `show_yaml.py` are absent from `main`
- `.gitattributes merge=ours` strategy is removed

---

## References

- `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — Principles 2, 3, 4, 8, 9, 10, 13
- PR #284 — rejected .gitignore approach (open, must NOT be merged)
- `.st3/config/workphases.yaml` — existing phase metadata config
- `.st3/config/phase_contracts.yaml` — existing phase enforcement config
- `mcp_server/tools/pr_tools.py` — CreatePRTool (to be modified)
- `mcp_server/tools/git_tools.py` — GitCommitTool (to be modified)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-09 | Agent | Initial — research only, English, with Expected Results framework |
