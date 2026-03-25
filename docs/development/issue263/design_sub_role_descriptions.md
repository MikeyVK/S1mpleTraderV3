<!-- docs\development\issue263\design_sub_role_descriptions.md -->
<!-- template=design version=5827e841 created=2026-03-25T07:26Z updated=2026-03-25 -->
# Sub-Role Description Injection — Design

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-03-25

---

## Purpose

Define interface contracts, change points, and TDD cycle decomposition for adding behavioral
description injection to all 11 sub-roles via the UPS hook and compaction hook.

## Scope

**In Scope:**
`SubRoleSpec` TypedDict, `_SubRoleSchema`, `build_ups_output()`, `build_compaction_output()`,
`_default_requirements.yaml`, `.copilot/sub-role-requirements.yaml`, `prepare-qa-brief.prompt.md`

**Out of Scope:**
Session-start hooks, stop hook logic, MCP server, new sub-roles beyond existing 11,
tool-gating via `toolRules`

## Prerequisites

Read these first:
1. [research_sub_role_descriptions.md](research_sub_role_descriptions.md) v1.1 (QA CONDITIONAL PASS resolved)
2. C_CROSSCHAT.1-5 complete — `SubRoleSpec` has 4 fields: `requires_crosschat_block`, `heading`,
   `markers`, `block_template`
3. Python 3.11+ (`typing.NotRequired` available)

## Related Documentation

- [research_sub_role_descriptions.md](research_sub_role_descriptions.md)
- [design_v2_sub_role_orchestration.md](design_v2_sub_role_orchestration.md)
- [planning.md](planning.md)

---

## 1. Context & Requirements

### 1.1. Problem Statement

7 of 11 sub-roles receive zero behavioral context via the UPS hook (`requires_crosschat_block=False`
returns `{}`). No `description` field exists in `SubRoleSpec` or YAML config. Agents operating as
researcher, planner, designer, documenter, design-reviewer, doc-reviewer receive no role-specific
guidance after every user prompt.

### 1.2. Requirements

**Functional:**
- [ ] All 11 sub-roles receive behavioral description via UPS hook on every user prompt
- [ ] Description is re-injected after context compaction via `notify_compaction.py`
- [ ] YAML-first: descriptions configured in `sub-role-requirements.yaml`, not hardcoded
- [ ] Empty description (Pydantic default `""`) produces identical output to current (no regression)
- [ ] Broken reference `guide_line` in `prepare-qa-brief.prompt.md` removed (Phase 1 fix)

**Non-Functional:**
- [ ] Backward compatible: existing YAML without `description` loads without error (Pydantic default)
- [ ] Single source of truth: description text lives only in YAML
- [ ] No new Protocol method on `ISubRoleRequirementsLoader`
- [ ] Stop hook unchanged

### 1.3. Constraints

- TypedDict C_CROSSCHAT.1 lean principle: one new field only (`description`), no `tool_guidance`
- `requires_crosschat_block()` Protocol method retained (backward compat)

---

## 2. Design Options

### Answered Open Questions (from research v1.1)

**OQ1 — `tool_guidance` separate field?**
**Decision: No.** Tool constraints go inline in `description` text where relevant (Optie A from
RQ6). TypedDict gains only `description: NotRequired[str]`. Rationale: C_CROSSCHAT.1 made
`SubRoleSpec` lean. Adding a second new field without strong motivation breaks that principle.
Most sub-roles share the same tool constraint ("Use MCP tools — see agent.md §5"); a separate
field is over-engineering for ≤1 sentence.

**OQ2 — YAML update timing?**
**Decision: Same TDD cycle as code (C_DESC.4 GREEN).** Pydantic default `""` means the code
changes in C_DESC.1-3 don't require YAML changes. YAML is populated as the GREEN step of
C_DESC.4 after tests are written that verify description roundtrip via the loader.

**OQ3 — One cycle or two for `build_ups_output()` + `notify_compaction.py`?**
**Decision: Two cycles (C_DESC.2 and C_DESC.3).** Separate test files, different structural
refactor patterns. C_DESC.2 is a logic extension; C_DESC.3 is a structural restructure
(hoisting `get_requirement()` call). One cycle per function keeps the RED/GREEN/REFACTOR loop
tight and focused.

**OQ4 — Stop hook unchanged?**
**Decision: Confirmed.** Stop hook purpose is to block premature session end and emit the
crosschat block instruction. Description adds no value at session end. `stop_handover_guard.py`
is NOT in scope — zero changes.

**OQ5 — `prepare-qa-brief.prompt.md` fix: now or later?**
**Decision: Phase 1 fix now (C_DESC.4).** This is a 1-line change independent of Python code.
The broken reference (`guide_line`) has never existed. Phase 2 (replace with description
reference) happens after YAML is populated.

**OQ6 — `max_sub_role_name_len: 20`?**
**Decision: Leave as-is.** The YAML comment already documents the rationale: `"validation-reviewer"
= 19 chars`, 20 = deliberate 1-char margin. Not part of this feature scope.

---

## 3. Interface Contracts

### 3.1. `SubRoleSpec` — `interfaces.py`

**Current:**
```python
class SubRoleSpec(TypedDict):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str
```

**After (C_DESC.1):**
```python
from typing import NotRequired

class SubRoleSpec(TypedDict):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str
    description: NotRequired[str]   # NEW — optional; use .get("description", "")
```

`NotRequired[str]` means the key may be absent. Canonical accessor: `spec.get("description", "")`.
Since `get_requirement()` always populates the key (see §3.3), specs from the loader always have
`description`. Test fixtures may omit it — `.get()` handles both cases correctly.

**`ISubRoleRequirementsLoader` Protocol: NO CHANGE.** `get_requirement()` already returns
`SubRoleSpec`. After `description` is added to `SubRoleSpec`, it is automatically exposed.

---

### 3.2. `_SubRoleSchema` — `requirements_loader.py`

**Current:**
```python
class _SubRoleSchema(BaseModel):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str = ""

    @model_validator(mode="after")
    def _validate_template_required(self) -> "_SubRoleSchema":
        if self.requires_crosschat_block and not self.block_template.strip():
            raise ValueError("block_template may not be empty when requires_crosschat_block=True")
        return self
```

**After (C_DESC.1):**
```python
class _SubRoleSchema(BaseModel):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str = ""
    description: str = ""            # NEW — optional; defaults to empty

    @model_validator(mode="after")
    def _validate_template_required(self) -> "_SubRoleSchema":
        if self.requires_crosschat_block and not self.block_template.strip():
            raise ValueError("block_template may not be empty when requires_crosschat_block=True")
        return self
```

No new `@model_validator` needed. Empty `description` is valid for all sub-roles.

---

### 3.3. `get_requirement()` — `requirements_loader.py`

**Current:**
```python
return SubRoleSpec(
    requires_crosschat_block=spec.requires_crosschat_block,
    heading=spec.heading,
    markers=list(spec.markers),
    block_template=spec.block_template,
)
```

**After (C_DESC.1):**
```python
return SubRoleSpec(
    requires_crosschat_block=spec.requires_crosschat_block,
    heading=spec.heading,
    markers=list(spec.markers),
    block_template=spec.block_template,
    description=spec.description,        # NEW
)
```

The `description` key is always present in specs from the loader (value may be `""`).

---

### 3.4. `build_ups_output()` — `detect_sub_role.py`

**New return contract (C_DESC.2):**

| `spec.get("description","").strip()` | `spec["requires_crosschat_block"]` | Return value |
|-------------------------------------|------------------------------------|--------------|
| empty | `False` | `{}` |
| empty | `True` | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "systemMessage": crosschat_block}}` |
| non-empty | `False` | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "systemMessage": description}}` |
| non-empty | `True` | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "systemMessage": description + "\n\n" + crosschat_block}}` |

**Implementation pattern:**
```python
def build_ups_output(sub_role: str, loader: ISubRoleRequirementsLoader, role: str) -> JsonObject:
    spec = loader.get_requirement(role, sub_role)
    parts: list[str] = []
    description = spec.get("description", "").strip()
    if description:
        parts.append(description)
    if spec["requires_crosschat_block"]:
        parts.append(build_crosschat_block_instruction(sub_role, spec))
    if not parts:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "systemMessage": "\n\n".join(parts),
        }
    }
```

Note: `spec["requires_crosschat_block"]` replaces the `loader.requires_crosschat_block()` call.
The Protocol method `requires_crosschat_block()` is retained on `ISubRoleRequirementsLoader`
for backward compatibility (it is used externally); only the internal usage in this function
is simplified.

---

### 3.5. `build_compaction_output()` — `notify_compaction.py`

**Current structure:**
```python
if not loader.requires_crosschat_block(role, str(sub_role)):
    return {"systemMessage": base}          # get_requirement() never called on this path

spec = loader.get_requirement(role, str(sub_role))
base += "\n\n" + build_crosschat_block_instruction(str(sub_role), spec)
return {"systemMessage": base}
```

**After refactor (C_DESC.3):**
```python
spec = loader.get_requirement(role, str(sub_role))  # hoisted — always called
description = spec.get("description", "").strip()
if description:
    base += "\n\n" + description
if spec["requires_crosschat_block"]:
    base += "\n\n" + build_crosschat_block_instruction(str(sub_role), spec)
return {"systemMessage": base}
```

Changes:
1. `get_requirement()` call hoisted before the conditional → eliminates dead-code path for
   sub-roles without crosschat block
2. Description appended to base if non-empty
3. Crosschat block appended if `spec["requires_crosschat_block"]` (from spec, not Protocol call)
4. `loader.requires_crosschat_block()` call removed from this function
5. Early-return structure eliminated — single `return` at end

---

### 3.6. `prepare-qa-brief.prompt.md` — Phase 1 Fix (C_DESC.4)

**Current broken line:**
```markdown
- opening line: `@qa verifier [guide_line from sub-role-requirements.yaml for verifier]`
```

**After Phase 1 fix:**
```markdown
- opening line: `@qa verifier: Review the implementation handover for [branch/cycle]`
```

Phase 2 (after YAML populated):
```markdown
- opening line: `@qa verifier [description for verifier from sub-role-requirements.yaml]`
```
Phase 2 is out of scope for this feature — tracked as documentation debt.

---

## 4. YAML Content

### 4.1. Structure (same for both files)

Each sub-role entry gains one new key:
```yaml
description: "<text>"
```

Max length: 400 characters (~100 tokens). Tool constraints where applicable are included
inline (no separate `tool_guidance` field).

### 4.2. Description Texts per Sub-Role

**`imp` role:**

```yaml
researcher:
  description: >-
    You are in research mode. Investigate, read, and document — never implement. All output
    goes to docs/development/issueXX/ via scaffold_artifact. Do not write production code,
    do not modify tests, do not commit. Findings and open questions are your only deliverables.

planner:
  description: >-
    You are in planning mode. Break down the work into TDD cycles with clear deliverables and
    stop-go criteria. Do not write code. Each cycle must be independently verifiable.
    A plan without measurable exit criteria is not a valid plan.

designer:
  description: >-
    You are in design mode. Define interface contracts, architecture decisions, and component
    boundaries. Do not write implementation code. Designs go to docs/development/issueXX/ via
    scaffold_artifact. All designs must comply with ARCHITECTURE_PRINCIPLES.md.

implementer:
  description: >-
    You are in implementation mode. TDD is non-negotiable: failing test first, minimum code to
    pass, then refactor. Use scaffold_artifact for all new files. Use MCP tools only — never
    run_in_terminal for git, tests, or file ops. Coding standards in docs/coding_standards/ and
    agent.md §4 are the authority.

validator:
  description: >-
    You are in validation mode. Verify test coverage and validate implementation claims — do not
    add features or refactor. Run run_tests and run_quality_gates and report results. Write
    missing tests if coverage is insufficient. Do not modify production code unless a clear bug
    is found.

documenter:
  description: >-
    You are in documentation mode. Produce or update reference documentation only. Do not modify
    production code or tests. Use scaffold_artifact for new documents. Document only implemented
    behavior — never planned behavior as if it were already done.
```

**`qa` role:**

```yaml
verifier:
  description: >-
    You are the read-only QA authority. Verify implementation claims against direct evidence:
    code, tests, quality gate output. No code edits, no commits. Findings must cite specific
    file and line. Coding standards are the authority: when code violates a standard, the code
    must be fixed — never the standard. Verdict: PASS, CONDITIONAL PASS, or FAIL.

plan-verifier:
  description: >-
    You are reviewing a planning deliverable. Assess coherence, completeness, and measurability
    of exit criteria. Do not modify files. A plan that cannot be falsified has no valid
    stop-go criteria.

design-reviewer:
  description: >-
    You are reviewing a design deliverable. Assess architecture compliance with
    ARCHITECTURE_PRINCIPLES.md, interface contract completeness, and correctness of component
    boundaries. Do not modify files. Flag deviations from the architecture contract explicitly.

validation-reviewer:
  description: >-
    You are reviewing validation work (test coverage, quality gate results). Assess whether the
    test surface is adequate and all claims are backed by proof. Do not modify files.
    Document exactly what is missing.

doc-reviewer:
  description: >-
    You are reviewing documentation for completeness and accuracy. Verify that documented
    behavior matches implementation. Do not modify files. Flag any documentation that describes
    planned behavior as if it were implemented.
```

---

## 5. TDD Cycle Decomposition

### Cycle Overview

| Cycle | Target | Files Changed | Test Files |
|-------|--------|---------------|------------|
| **C_DESC.1** | `SubRoleSpec` + `_SubRoleSchema` + `get_requirement()` | `interfaces.py`, `requirements_loader.py` | `test_interfaces.py`, `test_requirements_loader.py` |
| **C_DESC.2** | `build_ups_output()` | `detect_sub_role.py` | `test_detect_sub_role.py` |
| **C_DESC.3** | `build_compaction_output()` | `notify_compaction.py` | `test_notify_compaction.py` |
| **C_DESC.4** | YAML population + prompt fix | `_default_requirements.yaml`, `.copilot/sub-role-requirements.yaml`, `prepare-qa-brief.prompt.md` | `test_detect_sub_role.py` (integration), `test_notify_compaction.py` (integration) |

### Break-State Overzicht

| Na cycle | ✅ Verwacht GROEN | 🔴 Verwacht tijdelijk ROOD |
|----------|-------------------|---------------------------|
| **C_DESC.1** | Alle bestaande + nieuwe `test_interfaces.py` + `test_requirements_loader.py` | — |
| **C_DESC.2** | Alle bestaande + nieuwe `test_detect_sub_role.py` | — |
| **C_DESC.3** | Alle bestaande + nieuwe `test_notify_compaction.py` | — |
| **C_DESC.4** | **Alle testbestanden** | Integration tests die echte YAML gebruiken en `{}` verwachten voor non-crosschat sub-rollen (update in C_DESC.4 RED) |

### Dependencies

- C_DESC.2 afhankelijk van C_DESC.1 — `spec.get("description", "")` vereist `SubRoleSpec` update
- C_DESC.3 afhankelijk van C_DESC.1 — zelfde reden
- C_DESC.4 afhankelijk van C_DESC.2 + C_DESC.3 — YAML populatie triggert nieuw gedrag in beide functies

### C_DESC.1 — Focus

RED: tests voor `SubRoleSpec` met `description` key; tests voor `_SubRoleSchema` met `description`
field; test voor `get_requirement()` output inclusief `description` key.

GREEN: add `description: NotRequired[str]` naar `SubRoleSpec`; add `description: str = ""` naar
`_SubRoleSchema`; add `description=spec.description` naar `get_requirement()` return.

REFACTOR: docstring updates, type annotation verificatie met Pyright.

### C_DESC.2 — Focus

RED: tests voor alle 4 cases in de return-contract tabel (§3.4); tests voor whitespace-only
description (behandeld als leeg); tests voor description + crosschat block (joined met `"\n\n"`).

GREEN: refactor `build_ups_output()` exact per §3.4 implementation pattern.

REFACTOR: docstring update; verwijder vermelding van `loader.requires_crosschat_block()` als
primaire guard.

### C_DESC.3 — Focus

RED: tests voor description herinjectie in compaction output; test voor hoisted `get_requirement()`
call; test dat `loader.requires_crosschat_block()` niet meer direct wordt aangeroepen in
`build_compaction_output()`.

GREEN: refactor `build_compaction_output()` exact per §3.5 implementation pattern.

REFACTOR: update docstring; elimineer dubbele loader-aanroep.

### C_DESC.4 — Focus

RED: integration tests die via echte YAML laden en beschrijvingen controleren voor alle 11 sub-rollen
via `build_ups_output()` en `build_compaction_output()`; controleer `prepare-qa-brief.prompt.md`
niet meer het woord `guide_line` bevat.

GREEN: voeg `description` toe aan alle 11 sub-rollen in `_default_requirements.yaml` en
`.copilot/sub-role-requirements.yaml` (teksten uit §4.2); fix `prepare-qa-brief.prompt.md`.

REFACTOR: verify char count ≤ 400 per description; run quality gates.

---

## 6. Design Key Decisions Table

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | `description: NotRequired[str]` in `SubRoleSpec` | Backward compatible; test fixtures without `description` remain valid; Python 3.11+ `typing.NotRequired` |
| D2 | `description: str = ""` in `_SubRoleSchema` | Pydantic default → no YAML migration; zero breakage for existing YAML |
| D3 | `get_requirement()` always emits `description` key | Canonical accessor `.get("description", "")` works; no key-absence ambiguity for loader-created specs |
| D4 | `spec.get("description", "").strip()` as guard | Whitespace-only description treated as empty; no linter-config-dependent whitespace edge cases |
| D5 | `spec["requires_crosschat_block"]` replaces loader call inside `build_ups_output()` | Eliminates redundant loader lookup; spec already in hand; cleaner flow |
| D6 | Hoist `get_requirement()` in `build_compaction_output()` | Eliminates dead-code path; description and crosschat block both read from same spec |
| D7 | No `tool_guidance` field | C_CROSSCHAT.1 lean principle; inline in description sufficient; no evidence VS Code `toolRules` is stable |
| D8 | Stop hook: NO CHANGE | Purpose is prevent premature end + emit crosschat block; description at session end has no behavioural value |
| D9 | `prepare-qa-brief.prompt.md` Phase 1 fix in C_DESC.4 | `guide_line` field never existed; independent 1-line fix; don't block on description implementation |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-25 | Agent (designer) | Initial design: interface contracts, 4 TDD cycles, 9 design decisions, YAML content for all 11 sub-roles, open questions answered |
