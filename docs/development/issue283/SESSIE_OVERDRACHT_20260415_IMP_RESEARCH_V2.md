# Sessie Overdracht — 15 april 2026 (Research v2.0 — IMP)

**Van:** @imp (implementer sub-rol: researcher)  
**Naar:** @imp (volgende sub-rol: designer)  
**Branch:** `refactor/283-ready-phase-enforcement`  
**Huidige fase:** `ready` (research deliverable afgerond)  
**Commit:** `531f13ea`

---

## Doel van deze overdracht

Dit document legt vast wat het research-fase werk heeft opgeleverd en geeft de designer
de exacte feiten die nodig zijn om een gerichte design-update te schrijven voor Model 1.

---

## Status na research

### Wat afgerond is (C1–C6)

Alle vijf originele defects zijn volledig geïmplementeerd. 2762 tests slagen.
Zie `research-git-add-or-commit-regression.md` §Post-C6 Status voor de complete tabel.

### Huidig probleem (exact)

Ondanks C1–C6 geblokkeerd door `create_pr` gate. Live bewijs op deze branch:

```
git diff --name-only <merge-base>..HEAD -- .st3/state.json .st3/deliverables.json
# output:
.st3/deliverables.json
.st3/state.json

git ls-tree main -- .st3/state.json .st3/deliverables.json
# output: (leeg — niet op main)
```

**Oorzaak:** `skip_paths` + `git restore --staged` is staging-level exclusion, niet
branch-tip neutralisatie. De bestanden staan nog steeds in de branch tree van HEAD
(via eerdere commits). `git diff --name-only merge_base..HEAD` detecteert de netto delta
correct → `create_pr` blokkeert correct.

---

## Geaccepteerd doelmodel (Model 1 — bindend)

Na de ready-phase cleanup commit:

> `git diff --name-only MERGE_BASE(HEAD, BASE)..HEAD -- artifact.path` is leeg
> voor elk pad in `MergeReadinessContext.branch_local_artifacts`.

Dit betekent: de branch-tip changeert de BASE niet op deze paden bij een merge.
De commit history tot aan de ready commit mag de echte werkstate tonen.

---

## Exacte gaps (uit research v2.0)

### Gap 1 — GitCommitTool.execute() voert staging-exclusion uit i.p.v. branch-tip neutralisatie

**Bestand:** `mcp_server/tools/git_tools.py`, `GitCommitTool.execute()` ~regel 352–361

Huidig:
```python
excluded_paths = frozenset(n.file_path for n in ctx.of_type(ExclusionNote))
commit_hash = self.manager.commit_with_scope(
    ...,
    skip_paths=excluded_paths,
)
```

Gewenst bij aanwezigheid van `ExclusionNote` entries (= terminal phase signaal):
1. Resolve BASE branch (3-tier chain: params.base → state.parent_branch → git_config.default_base_branch)
2. Voor elk `ExclusionNote.file_path`:
   - `git ls-tree BASE -- path` leeg → `git rm -- path`
   - `git ls-tree BASE -- path` niet leeg → `git restore --source=BASE --staged --worktree -- path`
3. Commit de resulting tree change (geen `skip_paths` voor deze paden — ze zitten IN de commit)

**Signaal:** aanwezigheid van `ExclusionNote` entries in `NoteContext` = terminal-phase route.
Geen extra phase-detection nodig in `execute()`.

### Gap 2 — GitCommitTool heeft geen base-branch kennis

**Bestand:** `mcp_server/tools/git_tools.py`, `GitCommitInput` (~regel 218)

`GitCommitInput` heeft geen `base` field. `GitCommitTool` heeft geen base-resolutie.

Toevoegen:
- `base: str | None = Field(default=None, ...)` aan `GitCommitInput`
- Resolutieketen in `execute()`:
  1. `params.base` (expliciete override)
  2. `_state_engine.get_state(current_branch).parent_branch` (uit state.json)
  3. `self.manager.git_config.default_base_branch` (uit GitConfig)

`_state_engine` is al geïnjecteerd in `GitCommitTool.__init__`.

### Gap 3 — EnforcementRunner hardcodeert `"main"` als base fallback

**Bestand:** `mcp_server/managers/enforcement_runner.py`, `_handle_check_merge_readiness()` ~regel 330

```python
base = str(context.get_param("base") or "main")  # ← "main" hardcoded
```

Fix: `EnforcementRunner.__init__` ontvangt `default_base_branch: str` parameter.
De `"main"` literal wordt vervangen door dit attribuut.

`server.py` injecteert `git_config.default_base_branch` bij constructie van `EnforcementRunner`.

### Gap 4 — Remediation messaging in `_handle_check_merge_readiness` verwijst naar skip_paths

**Bestand:** `mcp_server/managers/enforcement_runner.py`, suggestion notes ~regel 358–368

Huidige tekst impliceert `skip_paths` als fix: "Commit first in the ready phase to auto-exclude them"

Nieuwe tekst moet verwijzen naar Model 1: "Run a ready-phase commit to neutralize excluded
files to base (git rm or git restore --source=BASE)."

---

## Wat NIET verandert

- `_handle_check_merge_readiness` → `_has_net_diff_for_path` → `git diff --name-only merge_base..HEAD`  
  Dit is het juiste check-punt en blijft ongewijzigd.
- `NoteContext` architectuur, `ExclusionNote` signaal, `EnforcementRunner.run()` API → ongewijzigd.
- `GitAdapter.commit(skip_paths=)` postcondition → blijft bestaan als generieke primitive,
  maar wordt niet meer gebruikt in de terminal-phase route.
- `_ENFORCEMENT_DISPLAY_PATH` literal in `enforcement_runner.py` → dit is een display-only
  constant die in het bereik van F2 (boundary policy) valt. Optie A (totaalverbod) of
  Optie B (display-only toegestaan) moet worden besloten vóór de design finalisatie.
  **Aanbeveling: Optie A** (zie SESSIE_OVERDRACHT_20260413_IMP.md §F2).

---

## Aanbevolen implementatievolgorde (voor design/planning)

1. Beslis F2 boundary policy (Optie A of B) — blokkeert design v10.0 finalisatie.
2. Design: schrijf `design-git-add-commit-regression-fix.md` v10.0:
   - §Model 1 ready-commit route (Gap 1)
   - `GitCommitInput.base` veld + 3-tier resolutie (Gap 2)
   - `EnforcementRunner.__init__` default_base_branch injection (Gap 3)
   - Remediation messaging update (Gap 4)
   - F2 boundary policy beslissing
   - F1/F3/F4/F5 fixes uit SESSIE_OVERDRACHT_20260413_IMP.md
   - Supersession note in `design-ready-phase-enforcement.md` §2.6/§2.7 (F5)
3. QA review v10.0.
4. Planning: cycles voor Model 1 implementatie.
5. Implementatie.

**Testcontract voor Model 1 (binding — verplicht in design te specificeren):**
- Setup: branch wijzigt `state.json` + `deliverables.json` in meerdere commits.
- Ready commit: neutraliseert beide paden naar BASE.
- Assert: `git diff --name-only merge_base..HEAD -- path` leeg voor beide paden.
- Assert: `create_pr` gate wordt daarna NIET geblokkeerd.
- Assert: commit history vóór ready commit toont nog steeds de echte werkstate.
- Scenario 2: epic-parent heeft eigen versies → restore naar epic-parent versie.
- Scenario 3: path absent from BASE → verwijderd uit branch tree na ready commit.

---

## Git staat

```
HEAD: 531f13ea  docs(P_READY): research v2.0 — Model 1 branch-tip neutralization gap analysis
Worktree: .st3/state.json is lokaal gewijzigd (niet te committen — branch-local artifact)
```

---

## Niet besproken / buiten scope

- Implementatiecycles (volgt na QA-GO op design v10.0)
- Enige andere issue dan #283
- F2 boundary policy beslissing (aan de gebruiker)
