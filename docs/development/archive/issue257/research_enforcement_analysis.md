<!-- docs\development\issue257\research_enforcement_analysis.md -->
<!-- template=research version=8b7bb3ab created=2026-03-27T18:50Z updated= -->
# Architectuuranalyse: EnforcementRunner & PhaseContractResolver vs ARCHITECTURE_PRINCIPLES.md

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-27

---

## Purpose

Research voor architectuurbeslissing over PSE-refactoring: volledige analyse voor aanvang van implementatiecycles

## Scope

**In Scope:**
EnforcementRunner (194 regels), PhaseContractResolver (190 regels), PhaseStateEngine.transition() + force_transition() + alle on_exit_*/on_enter_* methods, enforcement.yaml, phase_contracts.yaml, ARCHITECTURE_PRINCIPLES.md §1-13

**Out of Scope:**
DeliverableChecker implementatiedetails, GitManager internals, QA manager, tests

## Prerequisites

Read these first:
1. enforcement_runner.py volledig gelezen (194 regels)
2. phase_contract_resolver.py volledig gelezen (190 regels)
3. phase_state_engine.py transition(), force_transition() en on_exit_* hooks gelezen
4. enforcement.yaml gelezen (3 regels, 2 tool-level rules)
5. phase_contracts.yaml gelezen (feature.planning, feature.implementation, docs.documentation)
6. ARCHITECTURE_PRINCIPLES.md alle 13 principes volledig gelezen
---

## Problem Statement

De SESSIE_OVERDRACHT_20260327.md benoemt dat EnforcementRunner en PhaseContractResolver bestaan maar NIET zijn ingebed in PSE's phase-transition logica. PSE is een God Class (801 regels, 7 hardcoded on_exit_* hooks). Vraag: zijn deze twee componenten functioneel compleet en voldoen ze aan de 13 bindende architectuurprincipes?

## Research Goals

- Beoordeel of EnforcementRunner compleet is en voldoet aan ARCHITECTURE_PRINCIPLES.md §1-13
- Beoordeel of PhaseContractResolver compleet is en voldoet aan ARCHITECTURE_PRINCIPLES.md §1-13
- Analyseer de wiring-gap: wat verbindt EnforcementRunner/PCR wél versus wat ontbreekt
- Identificeer concrete OCP/SRP-schendingen in PSE.transition() met on_exit_* if-keten
- Formuleer aanbevelingen voor de scope van nieuw werk op deze branch of een nieuw issue

## Related Documentation
- **[docs/development/issue257/SESSIE_OVERDRACHT_20260327.md][related-1]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-2]**
- **[docs/development/issue229/design.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/SESSIE_OVERDRACHT_20260327.md
[related-2]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-3]: docs/development/issue229/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-27 | imp | Initial analysis |

---

## Findings

### 1. EnforcementRunner — Functionele analyse

**Bestand:** `mcp_server/managers/enforcement_runner.py` (194 regels)

**Classes:**
| Klasse | Verantwoordelijkheid |
|--------|---------------------|
| `EnforcementContext` (frozen dataclass) | Bundelt workspace_root, tool_name, params, tool_result. Heeft `get_param()` voor universele param-extractie. |
| `EnforcementRegistry` | Handler-dict wrapper: `register(action_type, handler)`, `has()`, `get()`. |
| `EnforcementRunner` | Laadt rules uit `enforcement.yaml`, filtert op event/timing, dispatcht naar geregistreerde handlers. |

**Geregistreerde action types (default registry):**
1. `check_branch_policy` — controleert branch-type aan base-branch via fnmatch-patronen
2. `commit_state_files` — commit specifieke bestanden via GitManager na tool-uitvoering

**Werkend pad (productie):**
`server.py → run_tool() → enforcement_runner.run(event=tool_name, timing="pre"|"post", context)` filtert enforcement.yaml op `event_source=="tool"` + `tool==event` + `timing` → dispatcht naar handler.

**Huidig enforcement.yaml (alle 3 regels):**
```yaml
- event_source: tool, tool: create_branch, timing: pre  → check_branch_policy
- event_source: tool, tool: transition_phase, timing: post → commit_state_files
- event_source: tool, tool: transition_cycle, timing: post → commit_state_files
```

**Conclusie:** Component werkt correct voor zijn **actuele scope**. Er zijn geen runtime bugs in het werkende pad.

---

### 2. EnforcementRunner — Architectuurvergelijking

#### OVERTREDINGEN

**[OV-ER-1] §1.2 OCP + §13 — Hardcoded `event_source != "tool"` filter blokkeert phase events**

Locatie: `enforcement_runner.py`, methode `run()`:
```python
for rule in self._rules:
    if rule.event_source != "tool":  # hardcoded skip van ALLE niet-tool events
        continue
```
Per §13: _"Behavior that 'triggers at phase X' is configured in a YAML enforcement file, not hardcoded in Python."_ Als enforcement.yaml een `event_source: phase` rule bevat, wordt die **nooit uitgevoerd**. De component is architecturaal gecapped op tool-events. Phase-level enforcement is naar PSE's hardcoded on_exit_* hooks verbannen — precies wat §13 verbiedt.

**[OV-ER-2] §1.5 DIP — Constructor accepteert concrete `PhaseStateEngine`**

```python
def __init__(self, ..., state_engine: PhaseStateEngine, ...):
    self._state_engine = state_engine
```
`PhaseStateEngine` is een concrete klasse (801 regels). Per §1.5 en §6: een read-only consumer (enforcement runner leest alleen `get_current_phase()`) moet `IStateReader` geïnjecteerd krijgen, niet de volledige concrete implementatie.

**[OV-ER-3] §1.5 DIP + §9 YAGNI — Dead DI: `project_manager` nooit gebruikt**

```python
def __init__(self, ..., project_manager: ProjectManager, ...):
    self._project_manager = project_manager  # opgeslagen maar nooit aangeroepen
```
Geen enkele handler-methode roept `self._project_manager` aan. Dit is dode code (§9 YAGNI-overtreding).

**[OV-ER-4] §1.1 SRP — Re-export hub voor schema types**

`enforcement_runner.py` exporteert `EnforcementConfig`, `EnforcementAction`, `EnforcementRule` via `__all__`. Een runner-klasse die ook schema-types re-exporteert heeft twee verantwoordelijkheden.

#### COMPLIANT

| Principe | Status | Bewijs |
|----------|--------|--------|
| §4 Fail-Fast | ✅ | `_validate_registered_actions()` gooit `ConfigError` bij onbekende action_type op startup |
| §13 Config-driven dispatch | ✅ voor tool-events | Registry-pattern, geen if-chain op action_type |
| §5 CQS | ✅ | `EnforcementContext` is frozen; `run()` retourneert `list[str]` |
| §11 DI | ✅ | Alle dependencies via constructor, geen instantiatie in `run()` |
| §12 No import-time side effects | ✅ | Geen module-level config load |

**Volledigheid: PARTIEEL COMPLEET**
- Werkend: tool-event enforcement (2 handlers, 3 yaml-regels)
- Niet werkend: phase-event enforcement — architecturaal geblokkeerd door hardcoded filter

---

### 3. PhaseContractResolver — Functionele analyse

**Bestanden:**
- `mcp_server/managers/phase_contract_resolver.py` (190 regels)
- `mcp_server/config/schemas/phase_contracts_config.py` (CheckSpec, PhaseContractPhase, PhaseContractsConfig)
- `.st3/config/phase_contracts.yaml` (3 workflow-phase-entries)

**Classes:**
| Klasse | Verantwoordelijkheid |
|--------|---------------------|
| `PhaseConfigContext` (frozen dataclass) | Facade: bundelt workphases, phase_contracts, optioneel planning_deliverables. Bevat `_load_planning_deliverables()` static method voor file I/O. |
| `PhaseContractResolver` | Resolveert commit-type en exit-CheckSpecs voor een workflow/fase/cycle. Implementeert A6 merge semantics. |

**Twee publieke methoden:**
1. `resolve_commit_type(workflow_name, phase, sub_phase) → str | None` — voor `GitCommitTool` commit-type validatie
2. `resolve(workflow_name, phase, cycle_number) → list[CheckSpec]` — voor phase exit-gate checks (config + issue-specific merged)

**Wiring in server.py:**
- `resolve_commit_type()` → wired via `build_commit_type_resolver()` → `GitCommitTool` ✅
- `resolve()` → **NERGENS aangeroepen** — niet in PSE.transition(), niet in tools ❌

**Conclusie:** `resolve_commit_type()` is functioneel gereed en correct in gebruik. `resolve()` is dode code relatief aan zijn doel.

---

### 4. PhaseContractResolver — Architectuurvergelijking

#### OVERTREDINGEN

**[OV-PCR-1] §13 + §3 Config-First — `resolve()` is gebouwd maar niet ingebed in phase-transitions**

`resolve()` produceert een `list[CheckSpec]` voor een fase — precies de abstract gate-check die §13 eist. Maar `PSE.transition()` roept hem nooit aan. De hardcoded on_exit_* hooks in PSE doen hetzelfde werk (via WorkphasesConfig en DeliverableChecker), buiten de config-first flow om.

**[OV-PCR-2] §2 DRY + SSOT — Twee configuratiebronnen voor hetzelfde concept**

Phase exit-gates zijn gedefinieerd op twee plekken:
- `phase_contracts.yaml` → `PhaseContractResolver.resolve()` → `CheckSpec` objecten
- `workphases.yaml` → `PSE.on_exit_*()` → `WorkphasesConfig.get_exit_requires()` → dict-parse

Beide beschrijven "wat wordt gecheckt bij verlaten van fase X". Dat is een SSOT-overtreding (§2).

**[OV-PCR-3] §1.1 SRP — `PhaseConfigContext._load_planning_deliverables()` doet file I/O**

Een frozen dataclass (config-facade) laadt bestanden via een static method. File I/O hoort in een dedicated loader, niet in een waarde-object.

**[OV-PCR-4] §3 Config-First — `phase_contracts.yaml` is incompleet**

Voor de `feature`-workflow ontbreken entries voor: `research`, `design`, `tdd`, `validation`, `documentation`, `integration`. Zelfs als `resolve()` werd aangeroepen in PSE, zou het voor 6 van de 8 fases een lege lijst retourneren.

#### COMPLIANT

| Principe | Status | Bewijs |
|----------|--------|--------|
| §4 Fail-Fast | ✅ | `resolve_commit_type()` gooit `ConfigError` bij ontbrekende commit_type_map entry |
| §5 CQS | ✅ | `resolve()` en `resolve_commit_type()` zijn pure queries, geen mutatie |
| §11 DI | ✅ | `PhaseContractResolver(config: PhaseConfigContext)` — alles via constructor |
| §13 A6 merge semantics | ✅ | `_merge_checks()`: required gates immutable, recommended overschrijfbaar |
| §1.2 OCP (intern) | ✅ | Geen if-chain op phase-namen; dispatch via dict-lookup |

**Volledigheid: PARTIEEL COMPLEET**
- Werkend: `resolve_commit_type()` (commit-type pad, GitCommitTool)
- Niet werkend: `resolve()` (gate-check pad) — niet aangeroepen, config incompleet

---

### 5. PhaseStateEngine on_exit_* — Kruisverbanden

**7 hardcoded hooks in `transition()` (PSE L160–250):**
```python
if from_phase == "planning":       self.on_exit_planning_phase(branch, issue_number)
if from_phase == "research":       self.on_exit_research_phase(branch, issue_number)
if from_phase == "design":         self.on_exit_design_phase(branch, issue_number)
if from_phase == "validation":     self.on_exit_validation_phase(branch, issue_number)
if from_phase == "documentation":  self.on_exit_documentation_phase(branch, issue_number)
if from_phase == "implementation": self.on_exit_implementation_phase(branch)
if to_phase == "implementation":   self.on_enter_implementation_phase(branch, issue_number)
```

**[OV-PSE-1] §1.2 OCP — If-keten op fase-namen (exacte voorbeeldovertreding uit §1.2)**

De Quick Reference in ARCHITECTURE_PRINCIPLES.md noemt letterlijk `if phase_name == "implementation"` als verboden patroon. Deze code heeft 7 varianten in één methode. Elke nieuwe fase vereist wijziging van `transition()`.

**[OV-PSE-2] §1.1 SRP — God Class (4-verantwoordelijkheden-anti-pattern uit §1.1)**

§1.1 geeft dit anti-patroon letterlijk als voorbeeld:
```
WorkEngine._save_state()    → state persistence
WorkEngine.transition()     → validation + hook dispatch
WorkEngine.on_exit_phase()  → hook implementation
WorkEngine._reconstruct()   → external-source reconstruction
```
PSE heeft exact deze 4 verantwoordelijkheden.

**[OV-PSE-3] §13 — Hardcoded hooks in Python i.p.v. enforcement config**

"Behavior that 'triggers at phase X' is configured in a YAML enforcement file." De on_exit_* methods zijn precies dit — hardcoded phase-triggered behavior die in enforcement.yaml zou moeten staan.

---

### 6. Wiring-analyse: wat ontbreekt

```
BEDOELDE architectuur (§13 + ARCHITECTURE_PRINCIPLES):
  PSE.transition(from_phase)
    → EnforcementRunner.run(event="phase:exit:{from_phase}", timing="post")
      → enforcement.yaml: event_source: phase, event: exit:planning, action: check_phase_gates
      → PhaseContractResolver.resolve(workflow, phase) → list[CheckSpec] → gate check

WERKELIJKE architectuur:
  PSE.transition(from_phase)
    → if from_phase == "planning": self.on_exit_planning_phase()    [hardcoded]
    → if from_phase == "research": self.on_exit_research_phase()    [hardcoded]
    → ... (5 meer if-takken)
    → EnforcementRunner: NOOIT aangeroepen voor phase events
    → PhaseContractResolver.resolve(): NOOIT aangeroepen
```

**3 ontbrekende verbindingen:**

| # | Gap | Impact |
|---|-----|--------|
| G-1 | `EnforcementRunner.run()` hard-filtert `event_source=="tool"` → phase events nooit dispatcht | EnforcementRunner kan phase hooks nooit ontvangen |
| G-2 | `PSE.transition()` roept EnforcementRunner NIET aan voor phase events | Enforcement pipeline bypassed bij elke phase-transitie |
| G-3 | `PhaseContractResolver.resolve()` nooit aangeroepen in PSE of EnforcementRunner | Gate-check via CheckSpec nooit uitgevoerd |

---

### 7. Volledigheidsmatrix

| Component | Commit-type pad | Gate-check pad | Phase-hook pad | §1.1 SRP | §1.2 OCP | §1.5 DIP | §13 |
|-----------|:--------------:|:--------------:|:--------------:|:--------:|:--------:|:--------:|:---:|
| `PhaseContractResolver` | ✅ wired | ❌ orphan | n.v.t. | ⚠️ PCR-3 | ✅ | ✅ | ❌ PCR-1 |
| `EnforcementRunner` | n.v.t. | n.v.t. | ❌ blocked | ⚠️ ER-4 | ❌ ER-1 | ❌ ER-2,3 | ⚠️ partieel |
| `PSE.transition()` | n.v.t. | ❌ god class | ❌ god class | ❌ PSE-2 | ❌ PSE-1 | ✅ | ❌ PSE-3 |

**Legenda:** ✅ Compliant | ⚠️ Minor afwijking | ❌ Overtreding

---

### 8. Aanbevelingen

#### Prioriteit 1 — OCP + §13 herstellend (hoge impact)

**Ref-A:** `EnforcementRunner.run()` — Verwijder hardcoded `event_source != "tool"` filter. Dispatcher werkt op alle event_source types die in enforcement.yaml staan.

**Ref-B:** `PSE.transition()` — Vervang if-keten door `enforcement_runner.run(event="phase:exit:{from_phase}", ...)`. Vereist: EnforcementRunner geïnjecteerd in PSE constructor.

**Ref-C:** Nieuwe `check_phase_exit_gates` handler in EnforcementRunner roept `PhaseContractResolver.resolve()` aan. enforcement.yaml krijgt phase-level entries per fase.

#### Prioriteit 2 — DIP herstel (middel-prioriteit)

**Ref-D:** `EnforcementRunner` constructor: `state_reader: IStateReader` i.p.v. `state_engine: PhaseStateEngine`.

**Ref-E:** `EnforcementRunner` constructor: verwijder dead DI `project_manager` als geen handler het gebruikt.

#### Prioriteit 3 — SSOT herstel (lang traject)

**Ref-F:** Consolideer `phase_contracts.yaml` + `workphases.yaml` exit_requires naar één config-bron; vul alle fases van feature-workflow in.

#### Scope-aanbeveling

> **Maak een nieuw issue** voor de PSE-refactoring (Ref-A t/m C): dit is substantieel werk — PSE splitsen, enforcement.yaml uitbreiden, wiring aanleggen, tests updaten. Branch #257 heeft al 10 SRP-cycles voltooid; een nieuw issue houdt de scope schoon.

> **Ref-D en Ref-E** zijn kleine chirurgische fixes die eventueel als hotfix-cycles op #257 passen.

---

## Open Questions

1. Moeten `on_exit_*`-hooks volledig verplaatsen naar EnforcementRunner-handlers, of mogen ze als private PSE-methodes blijven zolang PSE zelf de dispatcher is?
2. Welke fases moeten in `phase_contracts.yaml` worden uitgebreid voordat `resolve()` zinnig inzetbaar is?
3. Is `PhaseConfigContext._load_planning_deliverables()` verplaatsbaar naar `ConfigLoader` zonder breaking changes?

## References

- `mcp_server/managers/enforcement_runner.py`
- `mcp_server/managers/phase_contract_resolver.py`
- `mcp_server/managers/phase_state_engine.py` (regels 160–310 en 568–801)
- `.st3/config/enforcement.yaml`
- `.st3/config/phase_contracts.yaml`
- `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md`
- `docs/development/issue257/SESSIE_OVERDRACHT_20260327.md`