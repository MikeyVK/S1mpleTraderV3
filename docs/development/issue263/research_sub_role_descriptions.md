<!-- docs\development\issue263\research_sub_role_descriptions.md -->
<!-- template=research version=8b7bb3ab created=2026-03-25T06:40Z updated=2026-03-25 -->
# Sub-Role Description Injection — Research

**Status:** COMPLETE
**Version:** 1.0
**Last Updated:** 2026-03-25

---

## Purpose

Document the gap in behavioral description injection for sub-roles, evaluate implementation options, and provide a concrete recommendation for adding a `description` field to `SubRoleSpec` and the YAML config.

## Scope

**In Scope:**
Injection architecture (all hooks), `SubRoleSpec` extension, YAML-first description field, tool-usage injection strategy, broken reference in `prepare-qa-brief.prompt.md`, token-impact analysis.

**Out of Scope:**
Implementation code, TDD cycles, migration of existing YAML files beyond proposed additions.

## Prerequisites

Read these first:
1. QA-verifier findings on structural gap in orchestration system
2. Full read of `detect_sub_role.py`, `session_start_*.py`, `pre_compact_agent.py`, `notify_compaction.py`, `stop_handover_guard.py`, `interfaces.py`, `requirements_loader.py`

---

## Problem Statement

Sub-rollen in het copilot orchestration systeem missen een behavioral description die aan de agent
wordt geinjected. `SubRoleSpec` heeft 4 velden: `requires_crosschat_block`, `heading`, `markers`,
`block_template`. Er is geen `description`-veld. Sub-rollen zonder `requires_crosschat_block=True`
(researcher, planner, designer, documenter, design-reviewer, doc-reviewer) krijgen **niets**
geinjected via de UPS-hook. Daarnaast ontbreken sub-rol-specifieke tool-usage instructies.

## Research Goals

1. Breng de volledige huidige injectie-architectuur in kaart (alle hooks, triggers, condities)
2. Analyseer `SubRoleSpec` en `ISubRoleRequirementsLoader` op uitbreidbaarheid voor `description`
3. Evalueer en geef aanbeveling voor twee implementatie-opties (UPS vs. SessionStart)
4. Identificeer de broken reference in `prepare-qa-brief.prompt.md` en stel fix voor
5. Stel concrete `description`-teksten voor voor alle 11 sub-rollen
6. Bepaal de optimale strategie voor tool-usage injectie
7. Schat token-impact van description+tool-usage injectie per hook-moment

## Related Documentation

- [design_v2_sub_role_orchestration.md](design_v2_sub_role_orchestration.md)
- [design.md](design.md)
- [planning.md](planning.md)

---

## RQ1 — Huidige Injectie-Architectuur

### Hookoverzicht

| Hook | Trigger | Script | Wat wordt geinjected | Conditie |
|------|---------|--------|----------------------|----------|
| **SessionStart** | Begin nieuwe chat | `session_start_imp.py` / `session_start_qa.py` | `additionalContext`: branch-context, last_user_goal, files_in_scope, pending_handover, aanbevolen next step | Snapshot niet ouder dan 6u en changed_files-overlap. Fallback bij stale/absent snapshot. |
| **UserPromptSubmit** | Elke user-prompt | `detect_sub_role.py` → `build_ups_output()` | `systemMessage` met crosschat block instruction | **Alleen als `requires_crosschat_block=True`**. 7 van 11 sub-rollen krijgen `{}` terug — nul injectie. |
| **PreCompact (slot 1)** | Voor compactie | `pre_compact_agent.py` | Schrijft snapshot naar schijf (geen stdout naar agent) | Altijd — puur schijfoperatie |
| **PreCompact (slot 2)** | Voor compactie | `notify_compaction.py` → `build_compaction_output()` | `systemMessage`: sub-rol naam herinnering + optioneel crosschat block | sub_role aanwezig in state file. Block alleen als `requires_crosschat_block=True`. |
| **Stop** | Agent wil sessie beeindigen | `stop_handover_guard.py` → `evaluate_stop_hook()` | `decision=block` + `"Write NOW.\n\n" + crosschat_block` | Alleen `requires_crosschat_block=True` EN `stopHookActive=False`. Pass-through anders. |

### Gedetailleerde analyse per script

**`detect_sub_role.py` — `build_ups_output()`**

```
sub_role → loader.requires_crosschat_block(role, sub_role)
  False: return {}       ← researcher, planner, designer, documenter,
                            design-reviewer, doc-reviewer (project YAML)
  True:  return { hookSpecificOutput: { hookEventName: "UserPromptSubmit",
                    systemMessage: build_crosschat_block_instruction(sub_role, spec) }}
```

Sub-rollen die in de project YAML `requires_crosschat_block=True` hebben:
`implementer`, `validator` (imp); `plan-verifier`, `verifier`, `validation-reviewer` (qa).

**`session_start_imp.py` / `session_start_qa.py` — `main()`**

Injecteert `hookEventName: "SessionStart"` met `additionalContext`:
- `"Implementation context:"` / `"QA context:"` header
- Snapshot-data indien vers: active_role, last_user_goal (max 280 chars), files_in_scope,
  pending_handover_summary, handover_prompt_block (max 500/800 chars)
- Aanbevolen next step

**Geen sub-rol behavioral context geinjected** — de SessionStart weet niet welke sub-rol
de agent in deze sessie zal gebruiken (wordt pas bepaald bij de eerste UserPromptSubmit).

**`notify_compaction.py` — `build_compaction_output()`**

```
state.sub_role aanwezig?
  Nee: return {}
  Ja:  base = "Context was compacted. Active sub-role: **{sub_role}**. Use /resume-work..."
       requires_crosschat_block?
         Nee: return {systemMessage: base}          ← alleen naam, geen gedragscontext
         Ja:  return {systemMessage: base + "\n\n" + crosschat_block}
```

**`stop_handover_guard.py` — `evaluate_stop_hook()`**

Injecteert geen description. Blokkeert alleen voor `requires_crosschat_block=True`.
`build_stop_reason()` = `"Write NOW.\n\n" + crosschat_block`.

---

## RQ2 — `SubRoleSpec` en Loader-Interface Analyse

### `SubRoleSpec` (TypedDict, `interfaces.py`)

```python
class SubRoleSpec(TypedDict):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str
```

Geen `description`-veld. Geen `tool_usage`-veld. Er is geen schema-validatie die een nieuw
veld zou blokkeren — TypedDict is extensible.

### `_SubRoleSchema` (Pydantic, `requirements_loader.py`)

```python
class _SubRoleSchema(BaseModel):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str = ""
```

Uitbreiding met `description: str = ""` is triviaal. Default `""` vereist geen migratie van
bestaande YAML-bestanden. De bestaande `@model_validator` op `block_template` staat een
nieuw optioneel veld niet in de weg.

### `ISubRoleRequirementsLoader` (Protocol, `interfaces.py`)

Huidige methoden:
- `valid_sub_roles(role) → frozenset[str]`
- `default_sub_role(role) → str`
- `requires_crosschat_block(role, sub_role) → bool`
- `get_requirement(role, sub_role) → SubRoleSpec`
- `max_sub_role_name_len() → int`

**Geen nieuwe Protocol-methode nodig.** `get_requirement()` retourneert `SubRoleSpec` —
zodra `description` aan `SubRoleSpec` wordt toegevoegd, is het automatisch beschikbaar.

---

## RQ3 — Implementatie-Opties

### Optie A — Uitbreiden van `build_ups_output()`

Description altijd als systemMessage-prefix via UPS-hook. Crosschat block als suffix.
Sub-rollen zonder block krijgen alleen description.

```python
def build_ups_output(sub_role, loader, role) -> JsonObject:
    spec = loader.get_requirement(role, sub_role)
    parts = []
    if spec.get("description"):
        parts.append(spec["description"])
    if loader.requires_crosschat_block(role, sub_role):
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

Consequenties:
- Architectuurconsistentie: UPS-hook is het aangewezen kanaal voor per-prompt gedragscontext
- Alle sub-rollen krijgen description bij elke prompt
- `notify_compaction.py` moet ook worden uitgebreid (description herinjecteren na compactie)
- Bestaande tests voor `build_ups_output()` moeten worden bijgewerkt (`{}` is niet
  langer de return bij sub-rollen zonder crosschat block als description aanwezig)
- Token-kosten: ca. 100 tokens per prompt (aanvaardbaar — zie RQ7)

### Optie B — Injectie in SessionStart-hooks

Description eenmalig bij SessionStart als extra contextlijn.

Consequenties:
- Timing-probleem: SessionStart loopt **voor** de eerste UserPromptSubmit. De sub-rol van
  de huidige sessie is nog niet gedetecteerd. Injectie op basis van vorige sessie-state
  kan incorrect zijn.
- Na compactie: `notify_compaction.py` herinjecteert niet — agent verliest gedragscontext.
- Twee injectie-paden moeten afzonderlijk worden uitgebreid.

### Aanbeveling: **Optie A**

1. **Architectuurconsistentie**: UPS-hook is al het kanaal voor gedragscontext; geen
   nieuwe injectie-paden nodig.
2. **Compaction-correctheid**: `notify_compaction.py` kan dezelfde `spec.description`
   herinjecteren via hetzelfde pad.
3. **Eenvoud**: een aanpassingspunt (`build_ups_output()`) vs. drie (SessionStart-imp,
   SessionStart-qa, notify_compaction).
4. **Timing**: UPS loopt na sub-rol detectie — de description die geinjected wordt is
   altijd die van de correct gedetecteerde sub-rol.

---

## RQ4 — Broken Reference in `prepare-qa-brief.prompt.md`

### Gevonden broken reference

```markdown
- opening line: `@qa verifier [guide_line from sub-role-requirements.yaml for verifier]`
```

**Het veld `guide_line` bestaat niet en heeft nooit bestaan.** `SubRoleSpec` heeft
`requires_crosschat_block`, `heading`, `markers`, `block_template` — geen `guide_line`.

### Intended behavior

De auteur bedoelde waarschijnlijk een instructieregel die de verifier zijn gedragscontext
geeft. Dit is exact wat het nieuwe `description`-veld invult.

### Correcte fix

**Fase 1 (Intermediate — nu):** Verwijder de broken reference; vervang door generieke regel:
```markdown
- opening line: `@qa verifier: Review the implementation handover for [branch/cycle]`
```

**Fase 2 (Na description-implementatie):** Vervang door:
```markdown
- opening line: `@qa verifier [description for verifier from sub-role-requirements.yaml]`
```

Aanbeveling: Fase 1 nu uitvoeren als aparte minimale fix, onafhankelijk van description-impl.

---

## RQ5 — Voorgestelde Description-Teksten per Sub-Rol

Criterium: max 400 tekens (ca. 100 tokens), normatief.

### `imp` rol

**`researcher`**
> You are in research mode. Investigate, read, and document — never implement. All output goes to `docs/development/issueXX/` via `scaffold_artifact`. Do not write production code, do not modify tests, do not commit. Findings and open questions are your only deliverables.

**`planner`**
> You are in planning mode. Break down the work into TDD cycles with clear deliverables and stop-go criteria. Do not write code. Each cycle must be independently verifiable. A plan without measurable exit criteria is not a valid plan.

**`designer`**
> You are in design mode. Define interface contracts, architecture decisions, and component boundaries. Do not write implementation code. Designs go to `docs/development/issueXX/` via `scaffold_artifact`. All designs must comply with `ARCHITECTURE_PRINCIPLES.md`.

**`implementer`**
> You are in implementation mode. TDD is non-negotiable: failing test first, minimum code to pass, then refactor. Use `scaffold_artifact` for all new files. Use MCP tools — never `run_in_terminal` for git, tests, or file ops. Coding standards in `ARCHITECTURE_PRINCIPLES.md` are the authority.

**`validator`**
> You are in validation mode. Verify test coverage and validate implementation claims — do not add features or refactor. Run `run_tests` and `run_quality_gates` and report results. Write missing tests if coverage is insufficient. Do not modify production code unless a clear bug is found.

**`documenter`**
> You are in documentation mode. Produce or update reference documentation only. Do not modify production code or tests. Use `scaffold_artifact` for new documents. Document only implemented behavior — never planned behavior as if it were already done.

### `qa` rol

**`verifier`**
> You are the read-only QA authority. Verify implementation claims against direct evidence: code, tests, quality gate output. No code edits, no commits. Findings must cite specific file and line. Coding standards are the authority: when code violates a standard, the code must be fixed — never the standard. Verdict: PASS, CONDITIONAL PASS, or FAIL.

**`plan-verifier`**
> You are reviewing a planning deliverable. Assess coherence, completeness, and measurability of exit criteria. Do not modify files. A plan that cannot be falsified has no valid stop-go criteria.

**`design-reviewer`**
> You are reviewing a design deliverable. Assess architecture compliance with `ARCHITECTURE_PRINCIPLES.md`, interface contract completeness, and correctness of component boundaries. Do not modify files. Flag deviations from the architecture contract explicitly.

**`validation-reviewer`**
> You are reviewing validation work (test coverage, quality gate results). Assess whether the test surface is adequate and all claims are backed by proof. Do not modify files. Document exactly what is missing.

**`doc-reviewer`**
> You are reviewing documentation for completeness and accuracy. Verify that documented behavior matches implementation. Do not modify files. Flag any documentation that describes planned behavior as if it were implemented.

---

## RQ6 — Tool-Usage Definitie en Injectie-Strategie

### Drie opties geanalyseerd

**Optie A — Volledige tool-lijst per sub-rol inline in YAML**
11 sub-rollen × 15–20 tools = 165–220 regels extra config. Veel overlap.
Moeilijk te onderhouden. **Niet aanbevolen.**

**Optie B — Compacte constraint-zin in `description`, verwijzing naar `agent.md`**
`description` bevat: `"Use MCP tools only — see agent.md §5 Tool Priority Matrix."` plus
sub-rol-specifieke uitzonderingen waar van toepassing.
`agent.md` is al de SSOT voor het Tool Priority Matrix en wordt al als `.copilot-instructions.md`
auto-gelaed door VS Code. **Aanbevolen.**

**Optie C — Dedicated `tool_usage.md` of `.copilot/tool-usage.md`**
Goed voor documentatie, maar agent leest het niet automatisch tenzij geinjected.
Kan nuttig zijn als aanvulling op Optie B.

### Wat zeggen LLM-leveranciers en VS Code?

- **Claude/Anthropic**: system-prompts zo compact mogelijk. Verwijs naar externe documenten
  alleen als de agent die actief kan ophalen.
- **OpenAI**: stijl-instructies beknopt; tool-definitions naast system-prompt meegegeven.
- **Google/Gemini**: bondig en klaar. Referenties naar externe docs alleen effectief als
  agent die kan lezen.
- **VS Code/Copilot**: compact systemMessage is de norm. Er is een experimenteel
  `toolRules`-veld in hook output (VS Code 1.108+) voor tool-restricties buiten de
  systemMessage-token-budget.

### Aanbeveling

Gebruik Optie B. Voeg eventueel een optioneel `tool_guidance: str = ""` veld toe aan
`SubRoleSpec` voor sub-rol-specifieke tool-constraints (1–2 zinnen). Volledige Tool Priority
Matrix blijft in `agent.md`.

---

## RQ7 — Token-Impact Schatting

### Grootte-schattingen

| Component | Chars | Tokens (approx) |
|-----------|-------|-----------------|
| `description` (3–4 zinnen) | 300–400 | 75–100 |
| `tool_guidance` (1–2 zinnen, optioneel) | 100–200 | 25–50 |
| Crosschat block (volledige template) | 300–600 | 75–150 |
| Compaction base message | 80–120 | 20–30 |

### Token-impact per injectie-moment

| Hook | Huidig | Na uitbreiding | Delta |
|------|--------|---------------|-------|
| UPS — met crosschat block | ~100 | ~200–250 | +100–150 |
| UPS — zonder crosschat block | 0 | ~100–150 | +100–150 |
| PreCompact notify — met block | ~120 | ~220–270 | +100–150 |
| PreCompact notify — zonder block | ~25 | ~125–175 | +100–150 |
| Stop hook | ~100 | geen wijziging | 0 |
| SessionStart | ~150–500 | geen wijziging | 0 |

### Nut van herhaling per hook

| Hook | Description herhalen? | Motivatie |
|------|-----------------------|-----------|
| **UPS** | Ja | Gedragscontext verdwijnt na enkele beurten. Sub-rollen zonder block krijgen nu nul. |
| **PreCompact notify** | Ja | Essentiele herinjectie na compactie — exact het doel van deze hook. |
| **Stop hook** | Nee | Sessie eindigt toch. Only de block-instruction is relevant. |
| **SessionStart** | Nee | Sub-rol niet bekend bij SessionStart (timing-probleem). |

### VS Code `toolRules`-veld

VS Code 1.108+ heeft een experimenteel `toolRules`-veld gereserveerd in PreCompact
hook-output. Als dit stabiel wordt: ideale plek voor tool-restricties buiten de
systemMessage-token-budget.

### Advies maximale lengte `description`

**Max 400 tekens (~100 tokens).** Korter dan 200: te weinig voor betekenisvolle context.
200–400: optimale balans. Langer dan 500: diminishing returns; informatie thuishorend in
`agent.md` of `ARCHITECTURE_PRINCIPLES.md`.

---

## Open Vragen voor de Designer

1. **`tool_guidance`-veld**: apart optioneel YAML-veld voor tool-constraints, of volstaat
   een compacte zin in `description`? Grenscase: welke sub-rollen wijken af van de
   standaard tool-matrix?

2. **Backward compatibility**: bestaande YAML zonder `description` produces empty-string
   via Pydantic default. Lege description wordt niet geinjected. Worden de YAML-bestanden
   uitgebreid voor of tijdens de code-implementatie?

3. **`notify_compaction.py` uitbreiding**: UPS + notify in één cyclus of twee?
   Aanbeveling: one cycle — beide functies delen `spec.description`.

4. **Stop-hook uitsluiting**: description niet injecteren bij Stop is de aanbeveling.
   Bevestiging gewenst van de designer.

5. **`prepare-qa-brief.prompt.md` broken reference**: intermediate fix (verwijder
   `guide_line`) uitvoeren los van description-implementatie, of wachten?

6. **`max_sub_role_name_len` = 20 in project YAML**: de langste naam is
   `validation-reviewer` (19 chars). Als sub-rollen worden uitgebreid moet dit mee.
   Is dit bewust exact op de grens gezet?

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-25 | Agent (researcher) | Initial complete draft covering RQ1–RQ7 |
