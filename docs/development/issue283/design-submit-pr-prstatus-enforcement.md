<!-- docs\development\issue283\design-submit-pr-prstatus-enforcement.md -->
<!-- template=design version=5827e841 created=2026-04-21T10:10Z updated= -->
# submit_pr + PRStatusCache + BranchMutatingTool — Design

**Status:** DRAFT  
**Version:** 1.2
**Last Updated:** 2026-04-21

---

## Purpose

Replace the two-step create_pr flow with an atomic submit_pr tool, add post-PR lockdown via PRStatusCache, and reduce enforcement configuration DRY violations via BranchMutatingTool ABC.

## Scope

**In Scope:**
mcp_server/tools/pr_tools.py (SubmitPRTool), mcp_server/tools/base.py (BranchMutatingTool), mcp_server/state/pr_status_cache.py (new), mcp_server/core/interfaces/__init__.py (IPRStatusReader/Writer/PRStatus), mcp_server/managers/enforcement_runner.py (_handle_check_pr_status, tool_category dispatch), mcp_server/config/schemas/enforcement_config.py (tool_category field), .st3/config/enforcement.yaml (check_pr_status rule + submit_pr phase rule), mcp_server/server.py (composition root), all 18 BranchMutatingTool subclasses updated, terminal-route removed from GitCommitTool

**Out of Scope:**
GitHub branch protection rules, full audit trail for non-agent actors, hot-reload proxy internals

## Prerequisites

Read these first:
1. C1-C10 complete (Model 1 branch-tip neutralization)
2. research-submit-pr-impact-analysis.md v2.0 FINAL
3. BaseTool ABC with enforcement_event class variable (already exists)
4. EnforcementRunner with tool-name dispatch loop (already exists)
---

## 1. Context & Requirements

### 1.1. Problem Statement

The two-step ready-phase flow (git_add_or_commit → create_pr) has a chicken-and-egg problem: neutralize_to_base() restores state.json to the merge-base version, causing create_pr enforcement to read the wrong phase and block PR creation. Additionally, after a PR is submitted, 18 branch-mutating tools have no enforcement to prevent post-PR state corruption. Finally, enforcing check_pr_status on 18 individual tools via 18 separate enforcement.yaml entries is a DRY violation.

### 1.2. Requirements

**Functional:**
- [ ] submit_pr moet atomisch uitvoeren: neutralize artifacts, commit, push, en PR aanmaken in één tool call
- [ ] De readiness-gate (fase == `ready`) wordt afgedwongen via enforcement.yaml, niet intern in de tool
- [ ] Na submit_pr zijn alle branch-mutating tools geblokkeerd totdat merge_pr is aangeroepen
- [ ] `merge_pr` is expliciet geen `BranchMutatingTool`; het is de enige tool die PR status OPEN kan opruimen
- [ ] merge_pr schrijft ABSENT naar PRStatusCache na succesvolle merge
- [ ] Één enforcement.yaml rule dekt alle branch-mutating tools via tool_category
- [ ] PRStatusCache valt terug op GitHub API bij cold start (lege cache na MCP server restart)
- [ ] EnforcementRunner dispatcht op tool_category naast tool name
- [ ] EnforcementRule schema accepteert optioneel tool_category veld
- [ ] create_pr klasse blijft als interne utility; niet geregistreerd als publiek MCP tool

**Non-Functional:**
- [ ] BranchMutatingTool is a zero-method ABC — only sets tool_category class variable
- [ ] PRStatusCache is injected via IPRStatusReader/IPRStatusWriter interfaces (ISP compliance)
- [ ] Fail-fast: unknown tool_category in enforcement.yaml raises ConfigError at startup
- [ ] No global type: ignore disables; targeted ignores only as last resort (per TYPE_CHECKING_PLAYBOOK)

### 1.3. Constraints

- **FLAG DAY — clean break, geen backward compat:** Er worden géén transitielagen, compatibility shims, of deprecated code-paden achtergelaten. Alle legacy-functionaliteit (`create_pr` als MCP tool, terminal-route in `GitCommitTool`, `exclude_branch_local_artifacts` enforcement rule) wordt in dezelfde PR verwijderd. Elke test die het oude gedrag afdekt wordt herschreven of verwijderd — nooit commented out of conditionally skipped gelaten.
- `enforcement_event` en `tool_category` zijn orthogonaal: een tool kan beide hebben
- `PRStatusCache` is in-memory only; de cache is leidend tijdens een actieve sessie — GitHub API wordt alleen geraadpleegd bij cold start (lege cache)
- `EnforcementRule` heeft `extra='forbid'` (Pydantic): toevoeging van `tool_category` vereist schema-migratie-testupdate
- `MergePRTool` mag `set_pr_status(ABSENT)` alleen aanroepen bij succesvolle merge, niet bij fout
- `BaseTool.__init_subclass__` wraps `execute()` automatisch — geen aanpassing nodig voor `BranchMutatingTool`

## 2. Design Options

### Optie A — Separate tools, NoteContext sharing

Behoud `git_add_or_commit + create_pr` als twee-staps flow, maar introduceer een gedeelde NoteContext via een session-level store zodat de neutralization-state leesbaar is voor `create_pr`.

**Nadelen:** NoteContext is bewust per-call; session-state introduceert gedeelde mutable state (SSOT-schending). `create_pr` wordt impliciet afhankelijk van een vorig tool-call artefact. Fragiel bij partial failure.

### Optie B — HEAD commit message detectie

Na neutralize slaat `git_add_or_commit` een marker op in het commit bericht. `create_pr` detecteert de marker en slaat de fase-check over.

**Nadelen:** Fragiel; commit-bericht parsen is geen betrouwbaar contract. Koppelt enforcement logica aan een tekst-artefact. Niet auditeerbaar.

### Optie C — Atomaire `submit_pr` tool (gekozen)

`submit_pr` voert neutralize, commit, push en PR-aanmaak in één tool-call uit. State.json wordt gelezen vóór neutralize, binnen dezelfde NoteContext. De readiness-gate blijft enforcement-gedreven (enforcement.yaml). Na de tool-call schrijft `PRStatusCache` de OPEN-status, waarna alle branch-mutating tools geblokkeerd zijn totdat `merge_pr` de status wist.

**Voordelen:** Geen race conditions. De scheiding tussen operation logic (tool) en policy gates (enforcement) blijft intact. PRStatusCache met cold-start API fallback maakt de oplossing restart-bestendig. BranchMutatingTool ABC elimineert de DRY-schending in enforcement.yaml.

---

## 3. Chosen Design

**Decision:** Optie C — Atomaire `submit_pr` tool, gecombineerd met `PRStatusCache` (session-leidend, cold-start API fallback) en `BranchMutatingTool` ABC (`tool_category`). Policy gates blijven enforcement-gedreven.

**Rationale:** Optie A en B lossen het kip-ei probleem niet fundamenteel op — ze verschuiven alleen het probleem. Optie C maakt neutralisatie en PR-aanmaak atomisch binnen één NoteContext, terwijl de readiness-gate config-first blijft via enforcement.yaml. De bestaande infrastructure (`BaseTool` ABC, `enforcement_event`, `EnforcementRunner` dispatch) is direct uitbreidbaar met `tool_category`. `PRStatusCache` met cold-start API fallback is restart-bestendig zonder persistente disk-state; de cache is leidend tijdens een actieve sessie.

### 3.1. Key Design Decisions

| # | Beslissing | Keuze | Reden |
|---|-----------|-------|-------|
| D1 | Policy gate vs operation logic | **Fase-check in enforcement.yaml; execution logic in tool** | Policy gates (mag deze tool draaien?) horen in enforcement/config. Operation invariants (hoe voer ik dit technisch correct uit?) horen in de tool. Neutralize, commit, push en PR-aanmaak zijn execution logic. De readiness-check is een policy gate. |
| D2 | `CreatePRTool` bewaren? | **Nee, verwijderd in C5** | Delegatie-argument verviel: `SubmitPRTool` roept `github_manager.create_pr()` direct aan (§3.2 execution flow). `CreatePRTool` en `CreatePRInput` zijn dode code zonder hergebruik. Bijbehorende enforcement rule (`create_pr` pre: `check_merge_readiness`) ook verwijderd. |
| D3 | Terminal-route in `GitCommitTool` | **Verwijderen** | Neutralisatie verplaatst naar `submit_pr`; terminal-route is dode code |
| D4 | `git_add_or_commit` in ready-fase | **Blokkeren** | Ready-phase commits zijn exclusief aan `submit_pr` |
| D5 | `exclude_branch_local_artifacts` rule | **Bijgesteld (C4 QA)** | Regel blijft op `git_add_or_commit` (normale commits). Ook toegevoegd aan `submit_pr` pre: enforcement hook produceert `ExclusionNote`s vóórdat `execute()` ze leest; zonder deze regel wordt neutralisatie in productie stilzwijgend overgeslagen. |
| D6 | Post-PR gap enforcement | **In-scope** via `PRStatusCache` | Bounded, helder gedefinieerd; samen met D7 één coherent pakket |
| D7 | Tool-categorie enforcement (DRY) | **`BranchMutatingTool` ABC** + `tool_category` | Één yaml-regel dekt 18 tools; nieuwe tools kiezen simpelweg de juiste ABC. `merge_pr` is expliciet geen `BranchMutatingTool` — zie sectie 3.4. |
| D8 | `EnforcementRule` schema-uitbreiding | **`tool_category` veld toevoegen** | Optioneel veld, validator enforceert `tool` OR `tool_category` bij `event_source == "tool"` |

### 3.2. Component: SubmitPRTool

**Locatie:** `mcp_server/tools/pr_tools.py`

**Input model `SubmitPRInput`:**

| Veld | Type | Verplicht | Beschrijving |
|------|------|-----------|-------------|
| `head` | `str` | ja | Branch naam (feature/X) |
| `base` | `str` | nee (default: main) | Target branch |
| `title` | `str` | ja | PR titel |
| `body` | `str` | nee | PR beschrijving (markdown) |
| `draft` | `bool` | nee (default: False) | Draft PR |

**Execution flow:**

```
SubmitPRTool.execute()
  1. _read_current_phase(branch)         ← leest state.json vóór neutralize (puur informatief: voor CommitNote en logging; geen gate — readiness-gate zit in enforcement.yaml)
  2. _check_net_diff(artifacts, base)    ← conditioneel: heeft branch netto diff in branch-lokale artefacten?
  3. neutralize_to_base(artifacts)       ← alleen als stap 2 positief is (anders skip)
  4. commit_with_scope("ready", ...)     ← chore(P_READY): neutralize...
  5. push(head)                          ← push naar remote
  6. github.create_pr(head, base, ...)   ← PR aanmaken via API
  7. pr_status_writer.set_pr_status(     ← OPEN in PRStatusCache
       branch, PRStatus.OPEN)
```
**Foutafhandeling:** Bij fout in stap 4-7 wordt een `RecoveryNote` geproduceerd. Geen rollback van neutralize (is een content-revert, niet destructief).

**Inheritance:** `SubmitPRTool(BranchMutatingTool)` — geblokkeerd als er al een open PR is op deze branch (check_pr_status enforcement, pre). De readiness-gate (`check_phase_readiness`) is een aparte enforcement rule op `tool: submit_pr, timing: pre`.

### 3.3. Component: PRStatusCache + Interfaces

**Locatie interfaces:** `mcp_server/core/interfaces/__init__.py`

```
PRStatus (Enum)      ← OPEN | ABSENT
IPRStatusReader      ← get_pr_status(branch) → PRStatus
IPRStatusWriter      ← set_pr_status(branch, status) → None
```

**Locatie cache:** `mcp_server/state/pr_status_cache.py`

```
PRStatusCache
  implements: IPRStatusReader, IPRStatusWriter
  _cache: dict[str, PRStatus]
  _fetch_from_api(branch): GitHub API → OPEN | ABSENT

Lifecycle:
  cache miss (cold start)   → _fetch_from_api → sla op in cache
  actieve sessie            → cache is leidend; geen automatische refresh
  merge_pr (success)  → set_pr_status(branch, ABSENT)
  MCP restart         → cache leeg → eerste call triggert API lookup
```

**ISP-injectie:**
- `EnforcementRunner.__init__(pr_status_reader: IPRStatusReader | None = None)`
- `SubmitPRTool.__init__(pr_status_writer: IPRStatusWriter)`
- `MergePRTool.__init__(pr_status_writer: IPRStatusWriter)`

### 3.4. Component: BranchMutatingTool ABC

**Locatie:** `mcp_server/tools/base.py`

```
BaseTool (ABC)
  enforcement_event: str | None = None     (bestaand)
  tool_category: str | None = None         (nieuw)

BranchMutatingTool(BaseTool) (ABC)         (nieuw)
  tool_category = "branch_mutating"
  # Geen abstracte methoden — puur een category-marker
```

**18 subklassen (alle overerven van BranchMutatingTool):**
`GitCommitTool`, `GitPushTool`, `GitPullTool`, `GitMergeTool`, `GitDeleteBranchTool`, `GitRestoreTool`, `SafeEditTool`, `CreateFileTool`, `ScaffoldArtifactTool`, `SavePlanningDeliverablesTool`, `UpdatePlanningDeliverablesTool`, `TransitionPhaseTool`, `ForcePhaseTransitionTool`, `TransitionCycleTool`, `ForceCycleTool`, `InitializeProjectTool`, `CreateBranchTool`, `SubmitPRTool`

**`MergePRTool` is geen `BranchMutatingTool`** — bewuste exemptie. Motivatie: de blokkade-semantiek van `check_pr_status` is "voorkom dat de agent verder werkt aan een branch met open PR". `MergePRTool` werkt de branch niet verder uit — het beëindigt de PR-cyclus. Het is de enige tool die `PRStatus.OPEN` kan opruimen. Als `MergePRTool` ook `BranchMutatingTool` zou zijn, ontstaat een deadlock: de enige uitweg is ook geblokkeerd.

### 3.5. Component: EnforcementRunner + EnforcementRule

**`mcp_server/config/schemas/enforcement_config.py`:**
- Voeg `tool_category: str | None = None` toe aan `EnforcementRule`
- Update `validate_target`: accepteer `tool` OF `tool_category` bij `event_source == "tool"`

**`mcp_server/managers/enforcement_runner.py`:**
- `run()`: dispatch op zowel `rule.tool == event` als `rule.tool_category == tool_category`
- `_handle_check_pr_status()`: nieuwe handler — leest `IPRStatusReader`, blokkeert bij `OPEN`
- `_validate_registered_actions()`: uitbreiden met `KNOWN_CATEGORIES`-check voor fail-fast
- Verwijder: `_handle_exclude_branch_local_artifacts`, `_handle_check_merge_readiness`

**`.st3/config/enforcement.yaml`:**

```yaml
# Verwijderen:
- event_source: tool
  tool: git_add_or_commit
  timing: pre
  actions: [exclude_branch_local_artifacts]

- event_source: tool
  tool: create_pr
  timing: pre
  actions: [check_merge_readiness]

# Toevoegen:
- event_source: tool
  tool_category: branch_mutating
  timing: pre
  actions:
    - type: check_pr_status
```

```yaml
# Toevoegen (submit_pr readiness gate):
- event_source: tool
  tool: submit_pr
  timing: pre
  actions:
    - type: check_phase_readiness
      policy: ready
```

### 3.6. Composition Root (server.py)


```python
pr_cache = PRStatusCache(github_manager=github_manager)

tools = [
    ...
    SubmitPRTool(pr_status_writer=pr_cache),   # vervangt CreatePRTool
    MergePRTool(pr_status_writer=pr_cache),    # uitgebreid
    ...
]

enforcement_runner = EnforcementRunner(
    ...,
    pr_status_reader=pr_cache,
)
```

`CreatePRTool` wordt niet langer opgenomen in de `tools`-lijst.

## Related Documentation
- **[docs/development/issue283/research-submit-pr-impact-analysis.md][related-1]**
- **[docs/development/issue283/SESSIE_OVERDRACHT_20260417_QA_RESEARCH_SUBMIT_PR.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/development/issue283/research-submit-pr-impact-analysis.md
[related-2]: docs/development/issue283/SESSIE_OVERDRACHT_20260417_QA_RESEARCH_SUBMIT_PR.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-21 | Agent | Initial draft — scaffold |
| 1.2 | 2026-04-21 | Agent | QA feedback verwerkt: D1 herformuleerd (policy/operation scheiding), merge_pr exempt expliciet, 14→18 gecorrigeerd, cache-semantiek aangescherpt (γ-model) |
