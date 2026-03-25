<!-- docs\development\issue263\design_sub_role_descriptions.md -->
<!-- template=design version=5827e841 created=2026-03-25T07:26Z updated=2026-03-25 -->
# Sub-Role Description Injection — Design

**Status:** DRAFT
**Version:** 1.1
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
- [ ] **No backward compatibility**: YAML without `description` raises `ValidationError` (Pydantic required field)
- [ ] Single source of truth: description text lives only in YAML
- [ ] No new Protocol method on `ISubRoleRequirementsLoader`
- [ ] Stop hook unchanged

### 1.3. Constraints

- **No backward compatibility.** The package has never been released. All existing fixtures
  that construct `SubRoleSpec` directly MUST be updated to include `description` in the same
  cycle as the schema change (C_DESC.1).
- `requires_crosschat_block()` Protocol method retained — **verified external consumer**:
  `stop_handover_guard.py:60` calls `loader.requires_crosschat_block(role, sub_role)` directly.
  YAGNI does NOT apply — this is live production code. Protocol surface unchanged.

---

## 2. Design Options

### Answered Open Questions (from research v1.1)

**OQ1 — `tool_guidance` separate field?**
**Decision: No.** Tool constraints go inline in `description` text where relevant (Optie A from
RQ6). TypedDict gains only `description: str` (required key). Rationale: C_CROSSCHAT.1 made
`SubRoleSpec` lean. Adding a second new field without strong motivation breaks that principle.
Most sub-roles share the same tool constraint ("Use MCP tools — see agent.md §5"); a separate
field is over-engineering for ≤1 sentence.

**OQ2 — YAML update timing?**
**Decision: C_DESC.1 GREEN — atomically required.** `_SubRoleSchema` has no Pydantic default
for `description`, so a YAML entry without it raises `ValidationError`. Both YAML files MUST be
updated in the same cycle as the schema change. YAML cannot wait until C_DESC.4.

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
class SubRoleSpec(TypedDict):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str
    description: str   # NEW — required; may be empty string ""
```

No `NotRequired`. No `typing.NotRequired` import needed. `description: str` is a required key —
absent constructions are a type error (Pyright/mypy). The empty string `""` is the valid
"no description" value. Canonical accessor: `spec["description"].strip()`.

**`ISubRoleRequirementsLoader` Protocol: NO CHANGE.** `get_requirement()` already returns
`SubRoleSpec`. After `description` is added to `SubRoleSpec`, it is automatically exposed.

**Test fixture impact:** All 10 `SubRoleSpec(...)` constructions across 4 test files MUST
receive `description=<str>` in C_DESC.1. Files affected:
- `tests/copilot_orchestration/unit/contracts/test_interfaces.py` (lines 43, 63)
- `tests/copilot_orchestration/unit/hooks/test_notify_compaction.py` (line 32)
- `tests/copilot_orchestration/unit/hooks/test_detect_sub_role.py` (lines 64, 196, 266, 277, 329, 342)
- `tests/copilot_orchestration/unit/hooks/test_stop_handover_guard.py` (line 39)

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
    description: str             # NEW — required; no default; YAML must provide it

    @model_validator(mode="after")
    def _validate_template_required(self) -> "_SubRoleSchema":
        if self.requires_crosschat_block and not self.block_template.strip():
            raise ValueError("block_template may not be empty when requires_crosschat_block=True")
        return self
```

No `= ""` default. A YAML entry without `description` triggers Pydantic `ValidationError`.
This enforces that both YAML files are updated atomically with this Pydantic change (C_DESC.1 GREEN).

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

| `spec["description"].strip()` | `spec["requires_crosschat_block"]` | Return value |
|-------------------------------|------------------------------------|--------------|
| empty `""` | `False` | `{}` |
| empty `""` | `True` | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "systemMessage": crosschat_block}}` |
| non-empty | `False` | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "systemMessage": description}}` |
| non-empty | `True` | `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "systemMessage": description + "\n\n" + crosschat_block}}` |

**Implementation pattern:**
```python
def build_ups_output(sub_role: str, loader: ISubRoleRequirementsLoader, role: str) -> JsonObject:
    spec = loader.get_requirement(role, sub_role)
    parts: list[str] = []
    description = spec["description"].strip()
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

Note: `spec["requires_crosschat_block"]` replaces the `loader.requires_crosschat_block()` call
inside this function. The Protocol method `requires_crosschat_block()` is retained on
`ISubRoleRequirementsLoader` because `stop_handover_guard.py:60` is a verified live consumer —
this is a functional dependency, not a backward compatibility concern.

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
description = spec["description"].strip()
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
| **C_DESC.1** | `SubRoleSpec` + `_SubRoleSchema` + `get_requirement()` + both YAMLs + fixture updates | `interfaces.py`, `requirements_loader.py`, `_default_requirements.yaml`, `.copilot/sub-role-requirements.yaml`, 4 test fixture files | `test_interfaces.py`, `test_requirements_loader.py` |
| **C_DESC.2** | `build_ups_output()` | `detect_sub_role.py` | `test_detect_sub_role.py` |
| **C_DESC.3** | `build_compaction_output()` | `notify_compaction.py` | `test_notify_compaction.py` |
| **C_DESC.4** | Integration tests + prompt fix | `prepare-qa-brief.prompt.md` | `test_detect_sub_role.py` (integration), `test_notify_compaction.py` (integration) |

### Break-State Overzicht

| Na cycle | ✅ Verwacht GROEN | 🔴 Verwacht tijdelijk ROOD |
|----------|-------------------|---------------------------|
| **C_DESC.1** | Alle bestaande + nieuwe `test_interfaces.py` + `test_requirements_loader.py` | — |
| **C_DESC.2** | Alle bestaande + nieuwe `test_detect_sub_role.py` | — |
| **C_DESC.3** | Alle bestaande + nieuwe `test_notify_compaction.py` | — |
| **C_DESC.4** | **Alle testbestanden** | Integration tests die echte YAML gebruiken en `{}` verwachten voor non-crosschat sub-rollen (update in C_DESC.4 RED) |

### Dependencies

- C_DESC.2 afhankelijk van C_DESC.1 — `spec["description"].strip()` vereist `SubRoleSpec` update
- C_DESC.3 afhankelijk van C_DESC.1 — zelfde reden
- C_DESC.4 afhankelijk van C_DESC.2 + C_DESC.3 — YAML populatie triggert nieuw gedrag in beide functies

### C_DESC.1 — Focus

RED: tests voor `SubRoleSpec` met `description: str` key (required); test dat
`_SubRoleSchema.model_validate({"...", "description": "foo"}).description == "foo"`;
test dat `_SubRoleSchema` zonder `description` raises `ValidationError`; test dat
`get_requirement()` output de `description` key bevat; test dat `spec["description"]`
de waarde geeft uit YAML.

GREEN: add `description: str` naar `SubRoleSpec`; add `description: str` (no default)
naar `_SubRoleSchema`; add `description=spec.description` naar `get_requirement()` return;
**update beide YAML-bestanden** (`_default_requirements.yaml` + `.copilot/sub-role-requirements.yaml`)
met alle 11 sub-rol descriptions (teksten uit §4.2) — atomisch vereist, anders raises Pydantic
`ValidationError`; update alle 10 bestaande `SubRoleSpec(...)` test-fixture-constructies
in 4 test-bestanden met `description=""` of een geschikte test-string.

REFACTOR: docstring updates, type annotation verificatie met Pyright; verifieer geen
`.get("description", "")` patronen in productiecode — gebruik uitsluitend `spec["description"]`.

### C_DESC.2 — Focus

RED: tests voor alle 4 cases in de return-contract tabel (§3.4); tests voor whitespace-only
description (behandeld als leeg); tests voor description + crosschat block (joined met `"\n\n"`).

GREEN: refactor `build_ups_output()` exact per §3.4 implementation pattern.

REFACTOR: docstring update; verwijder vermelding van `loader.requires_crosschat_block()` als
primaire guard.

### C_DESC.3 — Focus

RED: gedragstests voor `build_compaction_output()` na refactoring:
- sub-rol met `requires_crosschat_block=False` én non-empty `description` → output bevat
  description-tekst (bewijst dat `get_requirement()` nu ook wordt aangeroepen voor dit pad)
- sub-rol met `requires_crosschat_block=True` én non-empty `description` → output bevat
  description én crosschat block, in die volgorde
- sub-rol met `requires_crosschat_block=False` én `description=""` → output bevat alleen
  de base message (naam herinnering), geen extra tekst
- sub-rol met `requires_crosschat_block=True` én `description=""` → output bevat alleen
  base + crosschat block (identiek aan huidig gedrag)

GREEN: refactor `build_compaction_output()` exact per §3.5 implementation pattern.

REFACTOR: update docstring; elimineer dubbele loader-aanroep.

### C_DESC.4 — Focus

RED: integration tests die via echte YAML laden en beschrijvingen controleren voor alle 11
sub-rollen via `build_ups_output()` en `build_compaction_output()`; controleer dat
`prepare-qa-brief.prompt.md` niet meer het woord `guide_line` bevat.

GREEN: fix `prepare-qa-brief.prompt.md` (Phase 1 fix — verwijder broken `guide_line` reference);
integration test-waarden aansluiten op echte YAML-teksten uit §4.2.

REFACTOR: verify char count ≤ 400 per description; run quality gates scope="branch".

---

## 6. Design Key Decisions Table

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | `description: str` (required) in `SubRoleSpec` | No backward compat (package unreleased). Explicit required key enforces completeness without hidden fallbacks. All fixture constructions updated in C_DESC.1 — no dead weight in TypedDict surface. |
| D2 | `description: str` (no default) in `_SubRoleSchema` | Pydantic required field: YAML without `description` raises `ValidationError` — forces both YAML files to be updated atomically with C_DESC.1 GREEN. No silent empty-string default hiding missing config. |
| D3 | `get_requirement()` always emits `description` key | `spec["description"]` is the only accessor — no `.get()` fallback needed; no key-absence ambiguity |
| D4 | `spec["description"].strip()` as guard | Whitespace-only description treated as empty (explicit, not implicit). With required `str`, `.get()` is never needed. |
| D5 | `spec["requires_crosschat_block"]` replaces loader call inside `build_ups_output()` + `build_compaction_output()` | Eliminates redundant loader lookup; spec already in hand. `requires_crosschat_block()` Protocol method **retained** — verified external consumer: `stop_handover_guard.py:60` calls it directly. |
| D6 | Hoist `get_requirement()` in `build_compaction_output()` | Eliminates dead-code path for sub-roles without crosschat block; description and crosschat block both read from same spec |
| D7 | No `tool_guidance` field | C_CROSSCHAT.1 lean principle; inline in description sufficient; no evidence VS Code `toolRules` is stable |
| D8 | Stop hook: NO CHANGE | Purpose is prevent premature end + emit crosschat block; description at session end has no behavioural value |
| D9 | `prepare-qa-brief.prompt.md` Phase 1 fix in C_DESC.4 | `guide_line` field never existed; independent 1-line fix; don't block on description implementation |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-25 | Agent (designer) | Initial design: interface contracts, 4 TDD cycles, 9 design decisions, YAML content for all 11 sub-roles, open questions answered |
| 1.1 | 2026-03-25 | Agent (designer) | F1: verified `stop_handover_guard.py:60` as external consumer of `requires_crosschat_block()` — YAGNI does not apply, Protocol retained. F2: replaced C_DESC.3 structural test with 4 behavior tests covering all output variants. F3: D1→`description: str` (required, no NotRequired); D2→no Pydantic default; YAML update moved from C_DESC.4 to C_DESC.1 atomical GREEN; all 10 existing fixture constructions identified for update; accessor changed to `spec["description"].strip()` throughout. F4 resolved by F3. F5: §1.2 Non-Functional backward-compat requirement replaced with explicit no-backward-compat statement. F6: OQ1 updated NotRequired[str]→str (required key). F7: OQ2 updated YAML timing from C_DESC.4→C_DESC.1 atomically required. F8: Dependencies accessor corrected to spec["description"].strip(). F9: Version header corrected to 1.1. |
