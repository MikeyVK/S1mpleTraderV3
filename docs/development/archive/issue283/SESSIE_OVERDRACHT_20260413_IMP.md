# Sessie Overdracht — 13 april 2026 (IMP)

## Branch
`refactor/283-ready-phase-enforcement`

## Issue
\#283

## Fase
`design` — design v9.0 DRAFT inhoudelijk doorgesproken met QA-feedback. Nog niet revisie uitgevoerd.

---

## Aanleiding

QA heeft `design-git-add-commit-regression-fix.md` v9.0 beoordeeld en zes bevindingen
teruggegeven. Alle zes zijn inhoudelijk doorgesproken en beoordeeld. Dit document legt het
besproken standpunt per finding vast zodat de volgende sessie direct kan beginnen met
het doorvoeren van de revisie.

---

## Overzicht bevindingen

| # | Ernst | Bestand | Kernprobleem | Beslissing |
|---|-------|---------|--------------|------------|
| F1 | Blocker | `design-git-add-commit-regression-fix.md` §3.9 | Verkeerde invariant: `git log` test "history touch", correcte invariant is "netto state-wijziging op target branch" | **Accepteren** — proxy wijzigen naar `git diff` |
| F2 | Blocker | `design-git-add-commit-regression-fix.md` §3.14 + `research-git-add-or-commit-regression.md` | Boundary-policy inconsistentie: research laat display-only toe, design verbiedt alles | **Beslissing vereist** — zie F2 |
| F3 | Blocker | `design-git-add-commit-regression-fix.md` §3.4 | NoteContext SRP — drie verantwoordelijkheden (opslag, query, render) zonder architecturale verdediging | **Accepteren verdediging** — SRP-paragraaf toevoegen, niet splitsen |
| F4 | Redactioneel | `design-git-add-commit-regression-fix.md` §3.9 | Voorbeeldcode gebruikt nog `recovery=[...]` kwargs terwijl constraint-tabel die verwijderd heeft | **Fixen** — raise-site patroon in voorbeelden doorvoeren |
| F5 | Blocker | `design-ready-phase-enforcement.md` §2.6 + §2.7 | SSOT-conflict: FINAL-design zegt "geen execute()-wijzigingen"; regression fix breekt dat open | **Accepteren** — supersession note toevoegen aan §2.6 |
| F6 | Synthese | — | Scope geaccepteerd; drie blockers (F1, F2, F3) en twee redactionele issues (F4, F5) herleid tot concrete acties | Zie per-finding acties |

---

## F1 — Proxy §3.9: `git log` → `git diff`

### Probleem

`_has_branch_commits_touching` gebruikt `git log merge_base..HEAD -- path`. Dit test of
*enig commit* ooit het pad aanraakte — niet of de *merge* een netto state-wijziging
intro­duceert. Dat zijn twee verschillende dingen.

**Concreet false positive-scenario:**
```
feature branch:
  commit A  – add .st3/state.json        (artifact present)
  commit B  – delete .st3/state.json     (artifact removed)

git log merge_base..HEAD -- .st3/state.json  → non-empty (twee commits)
git diff merge_base..HEAD -- .st3/state.json → empty      (netto nul)
```

`git log` blokkeert de PR ten onrechte; de merge brengt geen artifact-state mee naar main.

### Correcte invariant

Een child branch mag voor branch-local artifacts **geen netto state-wijziging** veroorzaken
op de target branch. Voor main: artifacts blijven afwezig. Voor een epic-parent: bestaande
artifacts blijven inhoudelijk ongewijzigd.

### Vereiste correctie in §3.9

1. Helper hernoemd: `_has_net_diff_for_path(workspace_root, path, base) -> bool`
2. Git-commando gewijzigd:
   ```python
   # VERVANGEN
   ["log", "--oneline", f"{merge_base_sha}..HEAD", "--", path]

   # DOOR
   ["diff", "--name-only", f"{merge_base_sha}..HEAD", "--", path]
   ```
3. `bool(log_result.stdout.strip())` blijft identieke logica — `diff --name-only` geeft de
   bestandsnaam als er een netto delta is, leeg als niet.
4. Fail-fast gedrag (niet-nul exit = `ExecutionError`) ongewijzigd.
5. Alle verwijzingen naar `git log` in §3.9 prose, tabel en test-matrix updaten naar `git diff`.
6. §3.8-§3.9 relatie-tabel in §3.9 updaten: "commit-history check" → "net-diff check".

**Tabelnaam aanpassen:**

| Laag | Mechanisme | Effect |
|------|-----------|--------|
| Commit (§3.8) | `git restore --staged` postcondition | Voorkomt dat artifact delta in enig commit belandt |
| Gate (§3.9) | `git diff merge_base..HEAD -- path` | Detecteert netto state-delta op de branch richting target |

---

## F2 — Boundary-policy: open beslissing

### Probleem

Twee documenten geven tegenstrijdige regels:

- `research-git-add-or-commit-regression.md` §5 (violations table noot):
  > "All other `.st3/config` strings in production are **display-only** constants in
  > `ConfigError.file_path` … do not open files and are **legitimate**."

- `design-git-add-commit-regression-fix.md` §3.14 structural test:
  ```python
  assert ".st3/config/" not in node.value
  ```
  Dit verbiedt *elke* `.st3/config/`-literal, inclusief de display-only constanten
  zoals `_ENFORCEMENT_DISPLAY_PATH = ".st3/config/enforcement.yaml"`.

### Twee opties

**Optie A — Totaalverbod** (de test zoals die staat is wél correct):
- Ook display-only strings vliegen eruit.
- De drie display-path constanten (`_ENFORCEMENT_DISPLAY_PATH`, `_PHASE_CONTRACTS_DISPLAY_PATH`,
  `_WORKPHASES_DISPLAY_PATH`) worden vervangen door bestandsnaam-only suffixen
  (bijv. `"enforcement.yaml"`) of door dynamische derivatie uit de geladen config.
- `research-git-add-or-commit-regression.md` §5 noot aanpassen: "display-only legitimate"
  verwijderen en vervangen door het totaalverbod.

**Optie B — Display-only toegestaan** (de research doc is wél correct):
- De guardrail-test krijgt een carve-out die display-path constanten uitsluit.
  Bijv.: alleen `Constant`-nodes aanvlaggen die *niet* als `file_path=` argument
  van een `ConfigError`-constructie worden gebruikt.
- `design-git-add-commit-regression-fix.md` §3.14 test updaten met de carve-out.

### Aanbeveling

**Optie A** is eenvoudiger te enforcen en consistenter: er zijn maar drie constanten,
en een bestandsnaam-suffix is voldoende voor diagnostische doeleinden. De complexiteit van
een carve-out in de AST-test weegt niet op tegen de simpele verwijdering van drie strings.

### Vereiste actie na beslissing

- Beslissing vastleggen als expliciete beleidsregel in §1.2 Requirements (regel toevoegen)
  en in §3.14 als commentaar bij de guardrail-test.
- Bij Optie A: drie constanten updaten + research doc noot corrigeren.
- Bij Optie B: AST-test carve-out specificeren en research doc intact laten.

**→ Beslissing aan de gebruiker vóór de revisie.**

---

## F3 — NoteContext SRP: verdediging toevoegen

### Probleem

`NoteContext` heeft drie verantwoordelijkheden in één klasse:
1. Opslag (`_entries: list[NoteEntry]`)
2. Query-mechanisme (`of_type(T) -> Sequence[T]`)
3. Response-renderer (`render_to_response(base: ToolResult) -> ToolResult`)

Het design verdedigt dit niet tegen §3 SRP en §4 Cohesie uit `ARCHITECTURE_PRINCIPLES.md`.

### Beslissing: verdedigen, niet splitsen

Opsplitsen in `NoteStore` + `NoteRenderer` lost niets op:
- Beide opereren op dezelfde `_entries`-list.
- Beide hebben dezelfde per-call lifetime.
- De renderer heeft de store nodig — splitsen voegt alleen indirectie toe zonder isolatie.

SRP = één *reden tot wijzigen*, niet één *methode*. De reden tot wijzigen voor `NoteContext`
is: "pas de coördinatie van typed note-flow voor één tool-aanroep aan." Alle drie de
methodes dienen precies dat doel.

Vergelijkbaar patroon in de codebase: `ToolResult` is tegelijk data-container én
factory (`ToolResult.text()`, `ToolResult.error()`) zonder SRP-bezwaar.

### Vereiste correctie in §3.4

Aan het einde van de §3.4 NoteContext sectie (na de invarianten-tabel) een sub-sectie
toevoegen:

```
#### SRP Verdediging

NoteContext is een value object voor één aanroep, niet een service.
Reden tot wijzigen: "pas de note-flow coördinatie van één tool-aanroep aan."
Alle drie methodes dienen dat doel; geen heeft een onafhankelijke wijzigingsreden.

Opsplitsen in NoteStore + NoteRenderer lost geen actual SRP-schending op:
- Beide opereren op dezelfde _entries-list en hebben dezelfde per-call lifetime.
- De renderer heeft store-toegang nodig; splitsing voegt indirectie toe zonder isolatie.
- Vergelijkbaar: ToolResult is data-container + factory zonder SRP-bezwaar.

Architecture Principle §3 (SRP): één reden tot wijzigen, niet één methode per klasse.
Architecture Principle §4 (Cohesie): opslag + query + render zijn cohesief onder de
note-flow verantwoordelijkheid.
```

---

## F4 — §3.9 voorbeeldcode recovery kwargs (redactioneel)

### Probleem

§3.9 bevat twee `raise ExecutionError(...)` voorbeelden die nog `recovery=[...]` doorgeven
als constructor-kwarg, terwijl §1.3 constraints stellen dat die parameter verwijderd is.

Locaties in het document:

```python
# FOUT — recovery= kwarg mag niet meer
raise ExecutionError(
    f"git merge-base failed for HEAD and '{base}': {stderr}",
    recovery=[
        f"Verify the target branch '{base}' exists locally and is fetched",
        f"Manually run: git merge-base HEAD {base}",
    ],
)

raise ExecutionError(
    f"git log failed for path '{path}': {stderr}",
    recovery=[
        "Verify that the branch history is readable",
        f"Manually run: git log --oneline {merge_base_sha}..HEAD -- {path}",
    ],
)
```

### Vereiste correctie

Beide sites omzetten naar raise-site patroon (§3.11). Elke recovery-item wordt een
aparte `RecoveryNote`:

```python
# CORRECT na flag-day
note_context.produce(RecoveryNote(
    message=f"Verify the target branch '{base}' exists locally and is fetched",
))
note_context.produce(RecoveryNote(
    message=f"Manually run: git merge-base HEAD {base}",
))
raise ExecutionError(f"git merge-base failed for HEAD and '{base}': {stderr}")

note_context.produce(RecoveryNote(message="Verify that the branch history is readable"))
note_context.produce(RecoveryNote(
    message=f"Manually run: git log --oneline {merge_base_sha}..HEAD -- {path}",
))
raise ExecutionError(f"git log failed for path '{path}': {stderr}")
```

Let op: `_has_net_diff_for_path` (zie F1) is een module-level helper zonder `note_context`
parameter. Na de omzetting naar `git diff` werkt dezelfde helper. Als de helper geen
`note_context` ontvangt, moet de `ExecutionError` zonder recovery-notes worden geraised
en de aanroeper (de handler) de recovery-noten schrijven voor het aanroepen van de helper.
Dit moet in §3.9 expliciet worden gespecificeerd.

---

## F5 — SSOT-conflict design-ready-phase-enforcement.md §2.6

### Probleem

`design-ready-phase-enforcement.md` heeft status FINAL en stelt in §2.6 en §2.7 expliciet:

> "No `execute()` changes."

`design-git-add-commit-regression-fix.md` opent `GitCommitTool.execute()` echt op:
- parameter `context: NoteContext` toegevoegd (§3.5)
- `ExclusionNote`-query toegevoegd (§3.7)
- `skip_paths`-doorgave naar `GitManager` (§3.7)

Twee FINAL-documenten spreken elkaar direct tegen. Implementer heeft tegenstrijdige
instructies.

### Beslissing: supersession note

Aan `design-ready-phase-enforcement.md` §2.6 een supersession note toevoegen:

```
> ⚠ **Gedeeltelijk vervangen.** §2.6 is gedeeltelijk vervangen door
> `design-git-add-commit-regression-fix.md`. `GitCommitTool.execute()` krijgt
> in de regression fix een `context: NoteContext` parameter en leest
> `ExclusionNote` entries uit de context voor `skip_paths`-doorgave.
> De `enforcement_event`-declaratie in dit sectie blijft ongewijzigd geldig.
> Autoriteitsvolgorde: regression fix design prevaleert voor `execute()`-contract;
> dit document prevaleert voor enforcement_event-declaratie.
```

Idem voor §2.7 (CreatePRTool — geen execute-wijziging, dus alleen de noot dat §2.6
gedeeltelijk vervangen is en §2.7 volledig van kracht blijft).

---

## Actielijst voor volgende sessie

Volgorde: eerst F2-beslissing van de gebruiker ophalen, dan alle vijf findings parallel
doorvoeren in `design-git-add-commit-regression-fix.md` v10.0 plus de supersession noten
in `design-ready-phase-enforcement.md`.

| Actie | Vereist F2-beslissing? | Bestand |
|-------|----------------------|---------|
| F1: proxy §3.9 omschrijven (`git diff`, helper hernomen) | Nee | `design-git-add-commit-regression-fix.md` |
| F2: boundary-policy text + guardrail-test aanpassen | **Ja** | `design-git-add-commit-regression-fix.md` + evt. `research-git-add-or-commit-regression.md` |
| F3: SRP-verdediging paragraaf toevoegen aan §3.4 | Nee | `design-git-add-commit-regression-fix.md` |
| F4: recovery kwargs in §3.9 voorbeelden fixen + helper-eigenaarschap note_context specificeren | Nee | `design-git-add-commit-regression-fix.md` |
| F5: supersession note aan §2.6 en §2.7 | Nee | `design-ready-phase-enforcement.md` |
| Versie §: 9.0 → 10.0, version history bijwerken | Nee | `design-git-add-commit-regression-fix.md` |

Na revisie: opnieuw naar `@qa` voor goedkeuring v10.0. Planning volgt pas daarna.

---

## Git-proof terminal commando (uit QA-sessie)

De QA-agent heeft het volgende commando uitgevoerd om `git diff` als correcte proxy te
verifiëren. Resultaat bevestigt: `log` was non-empty (false positive), `diff` was empty
(correct — netto nul):

```powershell
$tmp = Join-Path $env:TEMP 'st3_git_proxy_check'
# setup: branch met add + delete van state.json
git log "$mergeBase..HEAD" -- '.st3/state.json'   # non-empty → false positive
git diff --name-only "$mergeBase..HEAD" -- '.st3/state.json'  # empty → correct
# na merge: state.json niet aanwezig op main
```

Fase commit `b13bbae0` (`chore(P_READY): prepare branch for PR`) bevat het bewijs dat de
huidige `git log`-proxy een false positive geeft op de actieve branch: state.json zat in
een commit maar netto niet meer in de branch-delta.

---

## Niet besproken / buiten scope

- Planning voor de regression fix (volgt pas na QA-GO op design v10.0)
- Implementatiecycles voor de regression fix
- Enige andere issue dan \#283
